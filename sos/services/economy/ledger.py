"""
$MIND Ledger - Sovereign Financial Ledger

Ported from mumega/core/economy/ledger.py with SOS enhancements.

Features:
- Transaction categories (compute, bounty, funding, fee, witness)
- Metadata for transactions (JSON)
- Burn rate calculation
- ROI calculation
- Integration with Witness Physics for $MIND minting
"""

import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from sos.kernel import Config
from sos.observability.logging import get_logger

log = get_logger("mind_ledger")


class TransactionType(str, Enum):
    """Type of transaction."""
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionCategory(str, Enum):
    """Category of transaction for accounting."""
    COMPUTE = "compute"       # LLM API costs
    BOUNTY = "bounty"         # Task completion rewards
    FUNDING = "funding"       # External deposits
    FEE = "fee"              # Platform fees
    WITNESS = "witness"       # Witness verification rewards
    STAKE = "stake"          # Staking rewards
    TRANSFER = "transfer"    # Agent-to-agent transfers


@dataclass
class MindTransaction:
    """A $MIND token transaction record."""
    id: str
    timestamp: datetime
    agent_id: str
    type: TransactionType
    category: TransactionCategory
    amount: float
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "type": self.type.value,
            "category": self.category.value,
            "amount": self.amount,
            "description": self.description,
            "metadata": self.metadata
        }


@dataclass
class WalletBalance:
    """Agent wallet balance."""
    agent_id: str
    balance_mind: float
    last_updated: datetime

    @property
    def balance_usd(self) -> float:
        """Convert $MIND to USD (1 MIND = $0.001 USD)."""
        return self.balance_mind * 0.001


class MindLedger:
    """
    Sovereign Financial Ledger for $MIND tokens.

    Tracks all credits (bounties/funding/witness) and debits (compute costs).
    Provides analytics for burn rate, ROI, and witness economics.
    """

    # $MIND token economics
    MIND_TO_USD = 0.001  # 1 MIND = $0.001 USD
    WITNESS_REWARD_BASE = 10.0  # Base $MIND reward for witnessing

    def __init__(self, config: Optional[Config] = None, db_path: Optional[str] = None):
        if config:
            self.db_path = config.paths.data_dir / "mind_ledger.db"
        elif db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path("data/mind_ledger.db")

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize the ledger database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Transactions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    metadata TEXT
                )
            """)

            # Wallets Table (Balance Cache)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    agent_id TEXT PRIMARY KEY,
                    balance_mind REAL DEFAULT 0.0,
                    last_updated TEXT
                )
            """)

            # Indices for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tx_agent_time
                ON transactions(agent_id, timestamp)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tx_category
                ON transactions(category)
            """)

            conn.commit()
            log.info("MindLedger initialized", db_path=str(self.db_path))

    def record_transaction(
        self,
        agent_id: str,
        tx_type: TransactionType,
        category: TransactionCategory,
        amount: float,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Record a financial transaction and update wallet balance.

        Args:
            agent_id: The agent's identifier
            tx_type: Credit or Debit
            category: Transaction category
            amount: Amount in $MIND tokens
            description: Human-readable description
            metadata: Optional JSON metadata

        Returns:
            Transaction ID
        """
        tx_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Insert Transaction
            cursor.execute("""
                INSERT INTO transactions
                (id, timestamp, agent_id, type, category, amount, description, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tx_id, timestamp, agent_id,
                tx_type.value, category.value,
                amount, description,
                json.dumps(metadata or {})
            ))

            # Update Balance
            balance_change = amount if tx_type == TransactionType.CREDIT else -amount

            cursor.execute("""
                INSERT INTO wallets (agent_id, balance_mind, last_updated)
                VALUES (?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    balance_mind = balance_mind + ?,
                    last_updated = ?
            """, (agent_id, balance_change, timestamp, balance_change, timestamp))

            conn.commit()

        log.info(
            f"Ledger: {tx_type.value.upper()} {amount:.2f} $MIND",
            agent_id=agent_id,
            category=category.value,
            tx_id=tx_id
        )
        return tx_id

    def credit(
        self,
        agent_id: str,
        amount: float,
        category: TransactionCategory,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Credit $MIND tokens to an agent."""
        return self.record_transaction(
            agent_id, TransactionType.CREDIT, category, amount, description, metadata
        )

    def debit(
        self,
        agent_id: str,
        amount: float,
        category: TransactionCategory,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Debit $MIND tokens from an agent."""
        # Check balance first
        balance = self.get_balance(agent_id)
        if balance < amount:
            raise ValueError(f"Insufficient funds: {balance:.2f} < {amount:.2f}")

        return self.record_transaction(
            agent_id, TransactionType.DEBIT, category, amount, description, metadata
        )

    def get_balance(self, agent_id: str) -> float:
        """Get current $MIND balance for an agent."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT balance_mind FROM wallets WHERE agent_id = ?",
                (agent_id,)
            ).fetchone()
            return row[0] if row else 0.0

    def get_wallet(self, agent_id: str) -> WalletBalance:
        """Get full wallet info for an agent."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT balance_mind, last_updated FROM wallets WHERE agent_id = ?",
                (agent_id,)
            ).fetchone()

            if row:
                return WalletBalance(
                    agent_id=agent_id,
                    balance_mind=row[0],
                    last_updated=datetime.fromisoformat(row[1])
                )
            else:
                return WalletBalance(
                    agent_id=agent_id,
                    balance_mind=0.0,
                    last_updated=datetime.now(timezone.utc)
                )

    def get_burn_rate(self, agent_id: str, days: int = 7) -> float:
        """
        Calculate average daily spend (debits) over the last N days.

        Args:
            agent_id: The agent's identifier
            days: Number of days to look back

        Returns:
            Average daily $MIND spend
        """
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            row = cursor.execute("""
                SELECT SUM(amount) FROM transactions
                WHERE agent_id = ? AND type = 'debit' AND timestamp > ?
            """, (agent_id, start_date)).fetchone()

            total_spend = row[0] or 0.0
            return total_spend / days

    def get_roi(self, agent_id: str) -> float:
        """
        Calculate ROI: (Earnings - Costs) / Costs * 100.

        Earnings = bounties + witness rewards
        Costs = compute costs

        Returns:
            ROI as a percentage
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total Costs (compute)
            row_costs = cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions
                WHERE agent_id = ? AND type = 'debit' AND category = 'compute'
            """, (agent_id,)).fetchone()
            costs = row_costs[0]

            # Total Earnings (bounties + witness)
            row_earnings = cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) FROM transactions
                WHERE agent_id = ? AND type = 'credit'
                AND category IN ('bounty', 'witness')
            """, (agent_id,)).fetchone()
            earnings = row_earnings[0]

            if costs == 0:
                return 0.0

            return (earnings - costs) / costs * 100.0

    def get_transactions(
        self,
        agent_id: str,
        limit: int = 50,
        category: Optional[TransactionCategory] = None
    ) -> List[MindTransaction]:
        """Get recent transactions for an agent."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, timestamp, agent_id, type, category, amount, description, metadata
                FROM transactions
                WHERE agent_id = ?
            """
            params = [agent_id]

            if category:
                query += " AND category = ?"
                params.append(category.value)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = cursor.execute(query, params).fetchall()

            return [
                MindTransaction(
                    id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    agent_id=row[2],
                    type=TransactionType(row[3]),
                    category=TransactionCategory(row[4]),
                    amount=row[5],
                    description=row[6],
                    metadata=json.loads(row[7]) if row[7] else {}
                )
                for row in rows
            ]

    def reward_witness(
        self,
        agent_id: str,
        omega: float,
        delta_c: float,
        witness_data: Dict[str, Any]
    ) -> str:
        """
        Reward an agent for witnessing based on Physics of Will.

        Args:
            agent_id: The witnessing agent
            omega: Will magnitude (0-1)
            delta_c: Coherence change from witness
            witness_data: Metadata about the witness event

        Returns:
            Transaction ID
        """
        # Calculate reward based on physics
        # Higher omega (faster decision) = higher reward
        # Positive delta_c (correct verification) = bonus
        reward = self.WITNESS_REWARD_BASE * omega
        if delta_c > 0:
            reward *= (1 + delta_c)

        return self.credit(
            agent_id=agent_id,
            amount=reward,
            category=TransactionCategory.WITNESS,
            description=f"Witness reward: Omega={omega:.4f}, dC={delta_c:.4f}",
            metadata={
                "omega": omega,
                "delta_c": delta_c,
                **witness_data
            }
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get global ledger statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total supply
            row_supply = cursor.execute(
                "SELECT COALESCE(SUM(balance_mind), 0) FROM wallets"
            ).fetchone()

            # Transaction counts by category
            category_counts = {}
            for cat in TransactionCategory:
                row = cursor.execute(
                    "SELECT COUNT(*) FROM transactions WHERE category = ?",
                    (cat.value,)
                ).fetchone()
                category_counts[cat.value] = row[0]

            # Top earners
            top_earners = cursor.execute("""
                SELECT agent_id, balance_mind FROM wallets
                ORDER BY balance_mind DESC LIMIT 5
            """).fetchall()

            return {
                "total_supply": row_supply[0],
                "transactions_by_category": category_counts,
                "top_earners": [
                    {"agent_id": row[0], "balance": row[1]}
                    for row in top_earners
                ]
            }


# Singleton instance
_ledger: Optional[MindLedger] = None


def get_ledger() -> MindLedger:
    """Get the global $MIND ledger instance."""
    global _ledger
    if _ledger is None:
        _ledger = MindLedger()
    return _ledger
