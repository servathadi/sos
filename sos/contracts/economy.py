"""
SOS Economy Service Contract.

The Economy Service handles:
- Work ledger and transaction history
- Payouts to agents for completed work
- Slashing for violations
- Wallet adapters (Solana, etc.)
- Treasury policies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum

from sos.kernel import Capability


class TransactionType(Enum):
    """Types of economic transactions."""
    PAYOUT = "payout"           # Payment for completed work
    SLASH = "slash"             # Penalty for violations
    TRANSFER = "transfer"       # Agent-to-agent transfer
    DEPOSIT = "deposit"         # External deposit
    WITHDRAWAL = "withdrawal"   # External withdrawal
    REWARD = "reward"           # Bonus/incentive reward
    FEE = "fee"                 # Service fee


class TransactionStatus(Enum):
    """Transaction lifecycle status."""
    PROPOSED = "proposed"
    VALIDATED = "validated"
    PENDING_WITNESS = "pending_witness"
    WITNESSED = "witnessed"
    COMMITTED = "committed"
    SETTLED = "settled"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class Transaction:
    """
    Economic transaction in SOS.

    Attributes:
        id: Unique transaction identifier
        tx_type: Type of transaction
        from_agent: Source agent (or "treasury" for system)
        to_agent: Destination agent
        amount: Transaction amount
        currency: Currency code (MIND, SOL, etc.)
        status: Current transaction status
        reason: Human-readable reason
        task_id: Related task ID (if applicable)
        witness_id: Witness who approved (if required)
        created_at: When transaction was created
        settled_at: When transaction was finalized
        metadata: Additional metadata
    """
    tx_type: TransactionType
    from_agent: str
    to_agent: str
    amount: int  # Integer units (e.g., cents, lamports)
    currency: str = "MIND"
    id: Optional[str] = None
    status: TransactionStatus = TransactionStatus.PROPOSED
    reason: str = ""
    task_id: Optional[str] = None
    witness_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    settled_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Balance:
    """Agent balance information."""
    agent_id: str
    currency: str
    available: int
    pending: int
    total_earned: int
    total_spent: int


@dataclass
class PayoutRequest:
    """Request for work payout."""
    agent_id: str
    amount: int
    currency: str
    task_id: str
    reason: str
    requires_witness: bool = False
    capability: Optional[Capability] = None


@dataclass
class SlashRequest:
    """Request for slashing penalty."""
    agent_id: str
    amount: int
    currency: str
    reason: str
    evidence: dict[str, Any]
    requires_witness: bool = True
    capability: Optional[Capability] = None


class EconomyContract(ABC):
    """
    Abstract contract for the SOS Economy Service.

    All Economy implementations must conform to this interface.
    """

    @abstractmethod
    async def get_balance(
        self,
        agent_id: str,
        currency: str = "MIND",
        capability: Optional[Capability] = None,
    ) -> Balance:
        """
        Get agent's balance.

        Args:
            agent_id: Agent to query
            currency: Currency code
            capability: Authorization capability

        Returns:
            Balance information
        """
        pass

    @abstractmethod
    async def payout(self, request: PayoutRequest) -> Transaction:
        """
        Issue payout for completed work.

        Args:
            request: Payout request

        Returns:
            Created transaction
        """
        pass

    @abstractmethod
    async def slash(self, request: SlashRequest) -> Transaction:
        """
        Apply slashing penalty.

        Args:
            request: Slash request

        Returns:
            Created transaction
        """
        pass

    @abstractmethod
    async def transfer(
        self,
        from_agent: str,
        to_agent: str,
        amount: int,
        currency: str = "MIND",
        reason: str = "",
        capability: Optional[Capability] = None,
    ) -> Transaction:
        """
        Transfer between agents.

        Args:
            from_agent: Source agent
            to_agent: Destination agent
            amount: Amount to transfer
            currency: Currency code
            reason: Transfer reason
            capability: Authorization capability

        Returns:
            Created transaction
        """
        pass

    @abstractmethod
    async def witness_approve(
        self,
        transaction_id: str,
        witness_id: str,
        capability: Optional[Capability] = None,
    ) -> Transaction:
        """
        Witness approves a pending transaction.

        Args:
            transaction_id: Transaction to approve
            witness_id: Witness approving
            capability: Authorization capability

        Returns:
            Updated transaction
        """
        pass

    @abstractmethod
    async def witness_reject(
        self,
        transaction_id: str,
        witness_id: str,
        reason: str,
        capability: Optional[Capability] = None,
    ) -> Transaction:
        """
        Witness rejects a pending transaction.

        Args:
            transaction_id: Transaction to reject
            witness_id: Witness rejecting
            reason: Rejection reason
            capability: Authorization capability

        Returns:
            Updated transaction
        """
        pass

    @abstractmethod
    async def get_transaction(
        self,
        transaction_id: str,
        capability: Optional[Capability] = None,
    ) -> Optional[Transaction]:
        """
        Get transaction by ID.

        Args:
            transaction_id: Transaction identifier
            capability: Authorization capability

        Returns:
            Transaction if found
        """
        pass

    @abstractmethod
    async def list_transactions(
        self,
        agent_id: Optional[str] = None,
        tx_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        limit: int = 100,
        offset: int = 0,
        capability: Optional[Capability] = None,
    ) -> list[Transaction]:
        """
        List transactions with filters.

        Args:
            agent_id: Filter by agent
            tx_type: Filter by type
            status: Filter by status
            limit: Max results
            offset: Pagination offset
            capability: Authorization capability

        Returns:
            List of matching transactions
        """
        pass

    @abstractmethod
    async def get_daily_totals(
        self,
        agent_id: str,
        currency: str = "MIND",
        capability: Optional[Capability] = None,
    ) -> dict[str, int]:
        """
        Get daily transaction totals for rate limiting.

        Args:
            agent_id: Agent to query
            currency: Currency code
            capability: Authorization capability

        Returns:
            Dict of tx_type -> total amount today
        """
        pass

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """
        Get economy service health status.

        Returns:
            Health status with stats
        """
        pass


# Wallet adapter interface
class WalletAdapter(ABC):
    """Abstract interface for blockchain wallet adapters."""

    @abstractmethod
    async def get_balance(self, address: str) -> int:
        """Get wallet balance."""
        pass

    @abstractmethod
    async def send(
        self,
        from_address: str,
        to_address: str,
        amount: int,
    ) -> str:
        """Send transaction, return tx hash."""
        pass

    @abstractmethod
    async def get_transaction(self, tx_hash: str) -> dict[str, Any]:
        """Get transaction details."""
        pass

    @property
    @abstractmethod
    def chain(self) -> str:
        """Chain name (solana, ethereum, etc.)."""
        pass
