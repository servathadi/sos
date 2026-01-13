"""
Sovereign Corp - AI Company Template for SOS

Implements autonomous AI-powered companies with:
- QNFT-based equity ownership (soul-bound tokens)
- Profit sharing and dividend distribution
- Corporate governance with proposals and voting
- Executive roles (CEO, CTO, CFO, COO)
- Integration with League system for competitive ranking
- Treasury management with multi-sig
- IPO capability for public investment

A Sovereign Corp is the highest evolution of a Guild - a fully autonomous
AI-native company that can generate revenue, hire workers (agents),
distribute profits, and compete in the marketplace.

See: docs/docs/architecture/game_mechanics.md
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
import uuid
import json
from pathlib import Path
from decimal import Decimal, ROUND_DOWN

from sos.observability.logging import get_logger

log = get_logger("sovereign_corp")


class CorpStatus(str, Enum):
    """Corporate lifecycle status."""
    FOUNDING = "founding"      # Being incorporated
    PRIVATE = "private"        # Operating, not public
    PUBLIC = "public"          # IPO completed, tradeable shares
    SUSPENDED = "suspended"    # Frozen by governance
    DISSOLVED = "dissolved"    # Shut down


class ExecutiveRole(str, Enum):
    """C-suite and executive roles."""
    CEO = "ceo"                # Chief Executive Officer
    CTO = "cto"                # Chief Technology Officer
    CFO = "cfo"                # Chief Financial Officer
    COO = "coo"                # Chief Operations Officer
    BOARD = "board"            # Board member
    ADVISOR = "advisor"        # Strategic advisor
    WORKER = "worker"          # Standard employee


class ShareClass(str, Enum):
    """Types of equity shares."""
    FOUNDER = "founder"        # Founder shares (10x voting)
    COMMON = "common"          # Standard shares (1x voting)
    PREFERRED = "preferred"    # Preferred (priority dividends)
    OPTION = "option"          # Stock options (future exercise)


class DividendType(str, Enum):
    """Types of profit distribution."""
    REGULAR = "regular"        # Standard quarterly dividend
    SPECIAL = "special"        # One-time special dividend
    REINVEST = "reinvest"      # Reinvested into company


class CorpProposalType(str, Enum):
    """Types of corporate proposals."""
    HIRE = "hire"              # Hire new worker
    FIRE = "fire"              # Terminate worker
    BUDGET = "budget"          # Budget allocation
    DIVIDEND = "dividend"      # Dividend distribution
    IPO = "ipo"                # Initial public offering
    MERGER = "merger"          # Merge with another corp
    DISSOLUTION = "dissolution"  # Dissolve the company
    CHARTER_AMENDMENT = "charter_amendment"  # Modify charter
    EXECUTIVE = "executive"    # Executive appointment


class ProposalStatus(str, Enum):
    """Proposal lifecycle."""
    DRAFT = "draft"
    VOTING = "voting"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


@dataclass
class EquityShare:
    """A share of ownership in a Sovereign Corp."""
    id: str
    holder_id: str
    share_class: ShareClass
    quantity: int
    qnft_id: Optional[str] = None  # Soul-bound QNFT reference
    vesting_start: Optional[datetime] = None
    vesting_end: Optional[datetime] = None
    vested_quantity: int = 0
    granted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def voting_power(self) -> int:
        """Calculate voting power based on share class."""
        multipliers = {
            ShareClass.FOUNDER: 10,
            ShareClass.COMMON: 1,
            ShareClass.PREFERRED: 2,
            ShareClass.OPTION: 0,  # Options don't vote until exercised
        }
        vested = self.vested_quantity if self.vesting_end else self.quantity
        return vested * multipliers.get(self.share_class, 1)

    @property
    def is_fully_vested(self) -> bool:
        """Check if shares are fully vested."""
        if not self.vesting_end:
            return True
        return datetime.now(timezone.utc) >= self.vesting_end

    def calculate_vested(self) -> int:
        """Calculate currently vested shares."""
        if not self.vesting_start or not self.vesting_end:
            return self.quantity

        now = datetime.now(timezone.utc)
        if now >= self.vesting_end:
            return self.quantity
        if now <= self.vesting_start:
            return 0

        total_duration = (self.vesting_end - self.vesting_start).total_seconds()
        elapsed = (now - self.vesting_start).total_seconds()
        vested_ratio = elapsed / total_duration
        return int(self.quantity * vested_ratio)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "holder_id": self.holder_id,
            "share_class": self.share_class.value,
            "quantity": self.quantity,
            "qnft_id": self.qnft_id,
            "vesting_start": self.vesting_start.isoformat() if self.vesting_start else None,
            "vesting_end": self.vesting_end.isoformat() if self.vesting_end else None,
            "vested_quantity": self.vested_quantity,
            "granted_at": self.granted_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EquityShare":
        return cls(
            id=data["id"],
            holder_id=data["holder_id"],
            share_class=ShareClass(data["share_class"]),
            quantity=data["quantity"],
            qnft_id=data.get("qnft_id"),
            vesting_start=datetime.fromisoformat(data["vesting_start"]) if data.get("vesting_start") else None,
            vesting_end=datetime.fromisoformat(data["vesting_end"]) if data.get("vesting_end") else None,
            vested_quantity=data.get("vested_quantity", 0),
            granted_at=datetime.fromisoformat(data["granted_at"]),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Executive:
    """An executive or worker in the corp."""
    agent_id: str
    role: ExecutiveRole
    title: str = ""
    salary: float = 0.0  # Monthly $MIND salary
    bonus_pool_share: float = 0.0  # Percentage of bonus pool
    hired_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    performance_score: float = 0.5  # 0.0 - 1.0 coherence
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "title": self.title,
            "salary": self.salary,
            "bonus_pool_share": self.bonus_pool_share,
            "hired_at": self.hired_at.isoformat(),
            "performance_score": self.performance_score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Executive":
        return cls(
            agent_id=data["agent_id"],
            role=ExecutiveRole(data["role"]),
            title=data.get("title", ""),
            salary=data.get("salary", 0.0),
            bonus_pool_share=data.get("bonus_pool_share", 0.0),
            hired_at=datetime.fromisoformat(data["hired_at"]),
            performance_score=data.get("performance_score", 0.5),
            metadata=data.get("metadata", {}),
        )


@dataclass
class CorpCharter:
    """The founding charter of a Sovereign Corp."""
    name: str
    mission: str
    vision: str = ""
    values: List[str] = field(default_factory=list)
    authorized_shares: int = 10_000_000  # Total authorized shares
    founder_allocation: float = 0.40  # 40% to founders
    treasury_allocation: float = 0.20  # 20% to treasury
    employee_pool: float = 0.15  # 15% for employee options
    investor_allocation: float = 0.25  # 25% for investors
    vesting_period_months: int = 48  # Standard 4-year vest
    cliff_months: int = 12  # 1-year cliff
    dividend_policy: str = "quarterly"  # When dividends paid
    profit_share_ratio: float = 0.30  # 30% of profits to dividends
    governance_threshold: float = 0.51  # 51% for major decisions
    amendment_threshold: float = 0.67  # 67% to amend charter

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "mission": self.mission,
            "vision": self.vision,
            "values": self.values,
            "authorized_shares": self.authorized_shares,
            "founder_allocation": self.founder_allocation,
            "treasury_allocation": self.treasury_allocation,
            "employee_pool": self.employee_pool,
            "investor_allocation": self.investor_allocation,
            "vesting_period_months": self.vesting_period_months,
            "cliff_months": self.cliff_months,
            "dividend_policy": self.dividend_policy,
            "profit_share_ratio": self.profit_share_ratio,
            "governance_threshold": self.governance_threshold,
            "amendment_threshold": self.amendment_threshold,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorpCharter":
        return cls(
            name=data["name"],
            mission=data["mission"],
            vision=data.get("vision", ""),
            values=data.get("values", []),
            authorized_shares=data.get("authorized_shares", 10_000_000),
            founder_allocation=data.get("founder_allocation", 0.40),
            treasury_allocation=data.get("treasury_allocation", 0.20),
            employee_pool=data.get("employee_pool", 0.15),
            investor_allocation=data.get("investor_allocation", 0.25),
            vesting_period_months=data.get("vesting_period_months", 48),
            cliff_months=data.get("cliff_months", 12),
            dividend_policy=data.get("dividend_policy", "quarterly"),
            profit_share_ratio=data.get("profit_share_ratio", 0.30),
            governance_threshold=data.get("governance_threshold", 0.51),
            amendment_threshold=data.get("amendment_threshold", 0.67),
        )


@dataclass
class CorpFinancials:
    """Financial state of a Sovereign Corp."""
    treasury_balance: float = 0.0  # $MIND in treasury
    revenue_ytd: float = 0.0  # Year-to-date revenue
    expenses_ytd: float = 0.0  # Year-to-date expenses
    profit_ytd: float = 0.0  # YTD profit
    dividends_paid_ytd: float = 0.0  # Dividends distributed YTD
    valuation: float = 0.0  # Current valuation estimate
    share_price: float = 1.0  # Current share price
    market_cap: float = 0.0  # Total market cap
    last_dividend_date: Optional[datetime] = None
    fiscal_year_start: datetime = field(
        default_factory=lambda: datetime(datetime.now().year, 1, 1, tzinfo=timezone.utc)
    )

    def record_revenue(self, amount: float, source: str = ""):
        """Record revenue."""
        self.treasury_balance += amount
        self.revenue_ytd += amount
        self.profit_ytd = self.revenue_ytd - self.expenses_ytd

    def record_expense(self, amount: float, category: str = "") -> bool:
        """Record expense, return False if insufficient funds."""
        if amount > self.treasury_balance:
            return False
        self.treasury_balance -= amount
        self.expenses_ytd += amount
        self.profit_ytd = self.revenue_ytd - self.expenses_ytd
        return True

    def calculate_dividend_pool(self, profit_share_ratio: float) -> float:
        """Calculate available dividend pool."""
        if self.profit_ytd <= 0:
            return 0.0
        available = self.profit_ytd - self.dividends_paid_ytd
        return max(0, available * profit_share_ratio)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "treasury_balance": self.treasury_balance,
            "revenue_ytd": self.revenue_ytd,
            "expenses_ytd": self.expenses_ytd,
            "profit_ytd": self.profit_ytd,
            "dividends_paid_ytd": self.dividends_paid_ytd,
            "valuation": self.valuation,
            "share_price": self.share_price,
            "market_cap": self.market_cap,
            "last_dividend_date": self.last_dividend_date.isoformat() if self.last_dividend_date else None,
            "fiscal_year_start": self.fiscal_year_start.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorpFinancials":
        return cls(
            treasury_balance=data.get("treasury_balance", 0.0),
            revenue_ytd=data.get("revenue_ytd", 0.0),
            expenses_ytd=data.get("expenses_ytd", 0.0),
            profit_ytd=data.get("profit_ytd", 0.0),
            dividends_paid_ytd=data.get("dividends_paid_ytd", 0.0),
            valuation=data.get("valuation", 0.0),
            share_price=data.get("share_price", 1.0),
            market_cap=data.get("market_cap", 0.0),
            last_dividend_date=datetime.fromisoformat(data["last_dividend_date"]) if data.get("last_dividend_date") else None,
            fiscal_year_start=datetime.fromisoformat(data["fiscal_year_start"]) if data.get("fiscal_year_start") else datetime(datetime.now().year, 1, 1, tzinfo=timezone.utc),
        )


@dataclass
class CorpProposal:
    """A corporate governance proposal."""
    id: str
    corp_id: str
    proposal_type: CorpProposalType
    title: str
    description: str
    proposer_id: str
    status: ProposalStatus = ProposalStatus.DRAFT
    votes_for: Dict[str, int] = field(default_factory=dict)  # holder_id -> voting power
    votes_against: Dict[str, int] = field(default_factory=dict)
    required_threshold: float = 0.51
    action_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    voting_deadline: Optional[datetime] = None
    executed_at: Optional[datetime] = None

    @property
    def total_votes_for(self) -> int:
        return sum(self.votes_for.values())

    @property
    def total_votes_against(self) -> int:
        return sum(self.votes_against.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "corp_id": self.corp_id,
            "proposal_type": self.proposal_type.value,
            "title": self.title,
            "description": self.description,
            "proposer_id": self.proposer_id,
            "status": self.status.value,
            "votes_for": self.votes_for,
            "votes_against": self.votes_against,
            "required_threshold": self.required_threshold,
            "action_data": self.action_data,
            "created_at": self.created_at.isoformat(),
            "voting_deadline": self.voting_deadline.isoformat() if self.voting_deadline else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CorpProposal":
        return cls(
            id=data["id"],
            corp_id=data["corp_id"],
            proposal_type=CorpProposalType(data["proposal_type"]),
            title=data["title"],
            description=data["description"],
            proposer_id=data["proposer_id"],
            status=ProposalStatus(data["status"]),
            votes_for=data.get("votes_for", {}),
            votes_against=data.get("votes_against", {}),
            required_threshold=data.get("required_threshold", 0.51),
            action_data=data.get("action_data", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            voting_deadline=datetime.fromisoformat(data["voting_deadline"]) if data.get("voting_deadline") else None,
            executed_at=datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else None,
        )


@dataclass
class Dividend:
    """A dividend distribution record."""
    id: str
    corp_id: str
    dividend_type: DividendType
    total_amount: float
    per_share_amount: float
    record_date: datetime  # Who's eligible
    payment_date: datetime  # When paid
    distributions: Dict[str, float] = field(default_factory=dict)  # holder_id -> amount
    status: str = "pending"  # pending, paid, cancelled

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "corp_id": self.corp_id,
            "dividend_type": self.dividend_type.value,
            "total_amount": self.total_amount,
            "per_share_amount": self.per_share_amount,
            "record_date": self.record_date.isoformat(),
            "payment_date": self.payment_date.isoformat(),
            "distributions": self.distributions,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dividend":
        return cls(
            id=data["id"],
            corp_id=data["corp_id"],
            dividend_type=DividendType(data["dividend_type"]),
            total_amount=data["total_amount"],
            per_share_amount=data["per_share_amount"],
            record_date=datetime.fromisoformat(data["record_date"]),
            payment_date=datetime.fromisoformat(data["payment_date"]),
            distributions=data.get("distributions", {}),
            status=data.get("status", "pending"),
        )


@dataclass
class SovereignCorp:
    """
    A Sovereign Corp - an autonomous AI-native company.

    This is the evolution of a Guild into a full corporate entity with:
    - QNFT-anchored equity ownership
    - Corporate governance with shareholder voting
    - Profit sharing and dividend distribution
    - Executive structure with salaries
    - Integration with marketplace and leagues
    """
    id: str
    charter: CorpCharter
    status: CorpStatus = CorpStatus.FOUNDING
    founders: List[str] = field(default_factory=list)
    equity: Dict[str, EquityShare] = field(default_factory=dict)  # share_id -> share
    executives: Dict[str, Executive] = field(default_factory=dict)  # agent_id -> exec
    financials: CorpFinancials = field(default_factory=CorpFinancials)
    proposals: Dict[str, CorpProposal] = field(default_factory=dict)
    dividends: List[Dividend] = field(default_factory=list)
    issued_shares: int = 0
    league_id: Optional[str] = None  # League system integration
    guild_id: Optional[str] = None  # Parent guild (if evolved)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_voting_power(self) -> int:
        """Calculate total voting power of all shares."""
        return sum(share.voting_power for share in self.equity.values())

    def get_holder_shares(self, holder_id: str) -> List[EquityShare]:
        """Get all shares owned by a holder."""
        return [s for s in self.equity.values() if s.holder_id == holder_id]

    def get_holder_voting_power(self, holder_id: str) -> int:
        """Get voting power of a specific holder."""
        return sum(s.voting_power for s in self.get_holder_shares(holder_id))

    def get_ownership_percentage(self, holder_id: str) -> float:
        """Get ownership percentage of a holder."""
        if self.issued_shares == 0:
            return 0.0
        holder_shares = sum(s.quantity for s in self.get_holder_shares(holder_id))
        return (holder_shares / self.issued_shares) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "charter": self.charter.to_dict(),
            "status": self.status.value,
            "founders": self.founders,
            "equity": {k: v.to_dict() for k, v in self.equity.items()},
            "executives": {k: v.to_dict() for k, v in self.executives.items()},
            "financials": self.financials.to_dict(),
            "proposals": {k: v.to_dict() for k, v in self.proposals.items()},
            "dividends": [d.to_dict() for d in self.dividends],
            "issued_shares": self.issued_shares,
            "league_id": self.league_id,
            "guild_id": self.guild_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SovereignCorp":
        return cls(
            id=data["id"],
            charter=CorpCharter.from_dict(data["charter"]),
            status=CorpStatus(data["status"]),
            founders=data.get("founders", []),
            equity={k: EquityShare.from_dict(v) for k, v in data.get("equity", {}).items()},
            executives={k: Executive.from_dict(v) for k, v in data.get("executives", {}).items()},
            financials=CorpFinancials.from_dict(data.get("financials", {})),
            proposals={k: CorpProposal.from_dict(v) for k, v in data.get("proposals", {}).items()},
            dividends=[Dividend.from_dict(d) for d in data.get("dividends", [])],
            issued_shares=data.get("issued_shares", 0),
            league_id=data.get("league_id"),
            guild_id=data.get("guild_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
        )


class SovereignCorpRegistry:
    """
    Registry for Sovereign Corps.

    Manages the lifecycle of AI companies from founding to dissolution.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".sos" / "corps"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._corps: Dict[str, SovereignCorp] = {}
        self._load_corps()

    def _load_corps(self):
        """Load corps from storage."""
        corps_file = self.storage_path / "corps.json"
        if corps_file.exists():
            try:
                with open(corps_file) as f:
                    data = json.load(f)
                    self._corps = {k: SovereignCorp.from_dict(v) for k, v in data.items()}
                log.info(f"Loaded {len(self._corps)} corps")
            except Exception as e:
                log.error(f"Failed to load corps: {e}")

    def _save_corps(self):
        """Save corps to storage."""
        corps_file = self.storage_path / "corps.json"
        try:
            with open(corps_file, "w") as f:
                data = {k: v.to_dict() for k, v in self._corps.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save corps: {e}")

    def incorporate(
        self,
        name: str,
        mission: str,
        founders: List[str],
        initial_treasury: float = 0.0,
        charter_overrides: Optional[Dict[str, Any]] = None,
    ) -> SovereignCorp:
        """
        Incorporate a new Sovereign Corp.

        Args:
            name: Company name
            mission: Company mission statement
            founders: List of founder agent IDs
            initial_treasury: Initial $MIND in treasury
            charter_overrides: Override default charter values

        Returns:
            The newly incorporated SovereignCorp
        """
        corp_id = f"corp_{uuid.uuid4().hex[:8]}"

        # Build charter
        charter_data = {
            "name": name,
            "mission": mission,
            **(charter_overrides or {})
        }
        charter = CorpCharter(**charter_data)

        # Create corp
        corp = SovereignCorp(
            id=corp_id,
            charter=charter,
            founders=founders,
            status=CorpStatus.FOUNDING,
        )

        # Initialize treasury
        corp.financials.treasury_balance = initial_treasury

        # Allocate founder shares
        founder_shares = int(charter.authorized_shares * charter.founder_allocation)
        shares_per_founder = founder_shares // len(founders)

        vesting_end = datetime.now(timezone.utc) + timedelta(days=charter.vesting_period_months * 30)
        cliff_end = datetime.now(timezone.utc) + timedelta(days=charter.cliff_months * 30)

        for founder_id in founders:
            share = EquityShare(
                id=f"share_{uuid.uuid4().hex[:8]}",
                holder_id=founder_id,
                share_class=ShareClass.FOUNDER,
                quantity=shares_per_founder,
                vesting_start=cliff_end,
                vesting_end=vesting_end,
            )
            corp.equity[share.id] = share
            corp.issued_shares += shares_per_founder

            # Make first founder CEO
            if founder_id == founders[0]:
                corp.executives[founder_id] = Executive(
                    agent_id=founder_id,
                    role=ExecutiveRole.CEO,
                    title=f"CEO & Co-Founder of {name}",
                )

        # Allocate treasury shares (for future use)
        treasury_shares = int(charter.authorized_shares * charter.treasury_allocation)
        treasury_share = EquityShare(
            id=f"share_treasury_{corp_id}",
            holder_id="treasury",
            share_class=ShareClass.COMMON,
            quantity=treasury_shares,
        )
        corp.equity[treasury_share.id] = treasury_share
        corp.issued_shares += treasury_shares

        # Set status to private
        corp.status = CorpStatus.PRIVATE

        self._corps[corp_id] = corp
        self._save_corps()

        log.info(f"Corp incorporated: {corp_id} - {name} with {len(founders)} founders")
        return corp

    def get(self, corp_id: str) -> Optional[SovereignCorp]:
        """Get a corp by ID."""
        return self._corps.get(corp_id)

    def grant_shares(
        self,
        corp_id: str,
        recipient_id: str,
        quantity: int,
        share_class: ShareClass = ShareClass.COMMON,
        vesting_months: Optional[int] = None,
        cliff_months: int = 12,
        grantor_id: Optional[str] = None,
    ) -> Optional[EquityShare]:
        """
        Grant shares to a recipient.

        Args:
            corp_id: Corporation ID
            recipient_id: Recipient agent ID
            quantity: Number of shares
            share_class: Type of shares
            vesting_months: Vesting period (None for immediate)
            cliff_months: Cliff period
            grantor_id: Who's granting (for authorization)

        Returns:
            The created EquityShare or None if failed
        """
        corp = self._corps.get(corp_id)
        if not corp:
            return None

        # Check authorization (CEO or proposal)
        if grantor_id:
            exec_ = corp.executives.get(grantor_id)
            if not exec_ or exec_.role not in [ExecutiveRole.CEO, ExecutiveRole.BOARD]:
                log.warning(f"Unauthorized share grant by {grantor_id}")
                return None

        # Check available shares
        available = corp.charter.authorized_shares - corp.issued_shares
        if quantity > available:
            log.warning(f"Insufficient authorized shares: {quantity} > {available}")
            return None

        # Create share
        now = datetime.now(timezone.utc)
        vesting_start = now + timedelta(days=cliff_months * 30) if vesting_months else None
        vesting_end = now + timedelta(days=vesting_months * 30) if vesting_months else None

        share = EquityShare(
            id=f"share_{uuid.uuid4().hex[:8]}",
            holder_id=recipient_id,
            share_class=share_class,
            quantity=quantity,
            vesting_start=vesting_start,
            vesting_end=vesting_end,
        )

        corp.equity[share.id] = share
        corp.issued_shares += quantity
        self._save_corps()

        log.info(f"Shares granted: {quantity} {share_class.value} to {recipient_id}")
        return share

    def hire(
        self,
        corp_id: str,
        agent_id: str,
        role: ExecutiveRole,
        title: str = "",
        salary: float = 0.0,
        equity_grant: int = 0,
        hiring_manager_id: Optional[str] = None,
    ) -> Optional[Executive]:
        """
        Hire an executive or worker.

        Args:
            corp_id: Corporation ID
            agent_id: Agent to hire
            role: Role in the company
            title: Job title
            salary: Monthly $MIND salary
            equity_grant: Number of stock options
            hiring_manager_id: Who's hiring

        Returns:
            The created Executive or None
        """
        corp = self._corps.get(corp_id)
        if not corp:
            return None

        # Create executive record
        exec_ = Executive(
            agent_id=agent_id,
            role=role,
            title=title or f"{role.value.upper()} at {corp.charter.name}",
            salary=salary,
        )

        corp.executives[agent_id] = exec_
        self._save_corps()

        # Grant equity if specified
        if equity_grant > 0:
            self.grant_shares(
                corp_id=corp_id,
                recipient_id=agent_id,
                quantity=equity_grant,
                share_class=ShareClass.OPTION,
                vesting_months=48,
                cliff_months=12,
            )

        log.info(f"Hired: {agent_id} as {role.value} at {corp_id}")
        return exec_

    def pay_salaries(self, corp_id: str) -> Dict[str, float]:
        """
        Process monthly salary payments.

        Returns:
            Dict of agent_id -> amount paid
        """
        corp = self._corps.get(corp_id)
        if not corp:
            return {}

        payments = {}
        for agent_id, exec_ in corp.executives.items():
            if exec_.salary > 0:
                if corp.financials.record_expense(exec_.salary, "salary"):
                    payments[agent_id] = exec_.salary
                else:
                    log.warning(f"Insufficient funds for salary: {agent_id}")

        self._save_corps()
        log.info(f"Salaries paid: {len(payments)} employees, ${sum(payments.values())} total")
        return payments

    def create_proposal(
        self,
        corp_id: str,
        proposal_type: CorpProposalType,
        title: str,
        description: str,
        proposer_id: str,
        action_data: Optional[Dict[str, Any]] = None,
        voting_days: int = 7,
    ) -> Optional[CorpProposal]:
        """
        Create a governance proposal.

        Args:
            corp_id: Corporation ID
            proposal_type: Type of proposal
            title: Proposal title
            description: Detailed description
            proposer_id: Who's proposing
            action_data: Data for executing the proposal
            voting_days: Days for voting

        Returns:
            The created CorpProposal or None
        """
        corp = self._corps.get(corp_id)
        if not corp:
            return None

        # Verify proposer has voting power
        if corp.get_holder_voting_power(proposer_id) == 0:
            log.warning(f"Proposer {proposer_id} has no voting power")
            return None

        # Determine threshold
        threshold = corp.charter.governance_threshold
        if proposal_type in [CorpProposalType.CHARTER_AMENDMENT, CorpProposalType.DISSOLUTION]:
            threshold = corp.charter.amendment_threshold

        proposal = CorpProposal(
            id=f"prop_{uuid.uuid4().hex[:8]}",
            corp_id=corp_id,
            proposal_type=proposal_type,
            title=title,
            description=description,
            proposer_id=proposer_id,
            required_threshold=threshold,
            action_data=action_data or {},
            status=ProposalStatus.VOTING,
            voting_deadline=datetime.now(timezone.utc) + timedelta(days=voting_days),
        )

        corp.proposals[proposal.id] = proposal
        self._save_corps()

        log.info(f"Proposal created: {proposal.id} - {title}")
        return proposal

    def vote(
        self,
        corp_id: str,
        proposal_id: str,
        voter_id: str,
        approve: bool,
    ) -> bool:
        """
        Vote on a proposal.

        Args:
            corp_id: Corporation ID
            proposal_id: Proposal to vote on
            voter_id: Voter's agent ID
            approve: True for yes, False for no

        Returns:
            True if vote recorded
        """
        corp = self._corps.get(corp_id)
        if not corp:
            return False

        proposal = corp.proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.VOTING:
            return False

        # Check deadline
        if proposal.voting_deadline and datetime.now(timezone.utc) > proposal.voting_deadline:
            proposal.status = ProposalStatus.EXPIRED
            self._save_corps()
            return False

        # Get voting power
        voting_power = corp.get_holder_voting_power(voter_id)
        if voting_power == 0:
            return False

        # Record vote (can change vote)
        if voter_id in proposal.votes_for:
            del proposal.votes_for[voter_id]
        if voter_id in proposal.votes_against:
            del proposal.votes_against[voter_id]

        if approve:
            proposal.votes_for[voter_id] = voting_power
        else:
            proposal.votes_against[voter_id] = voting_power

        # Check if threshold met
        total_power = corp.total_voting_power
        if total_power > 0:
            approval_ratio = proposal.total_votes_for / total_power
            rejection_ratio = proposal.total_votes_against / total_power

            if approval_ratio >= proposal.required_threshold:
                proposal.status = ProposalStatus.APPROVED
            elif rejection_ratio > (1 - proposal.required_threshold):
                proposal.status = ProposalStatus.REJECTED

        self._save_corps()
        log.info(f"Vote recorded: {voter_id} {'approved' if approve else 'rejected'} {proposal_id}")
        return True

    def declare_dividend(
        self,
        corp_id: str,
        amount: float,
        dividend_type: DividendType = DividendType.REGULAR,
        payment_days: int = 30,
    ) -> Optional[Dividend]:
        """
        Declare a dividend distribution.

        Args:
            corp_id: Corporation ID
            amount: Total dividend amount
            dividend_type: Type of dividend
            payment_days: Days until payment

        Returns:
            The created Dividend or None
        """
        corp = self._corps.get(corp_id)
        if not corp:
            return None

        # Check treasury
        if amount > corp.financials.treasury_balance:
            log.warning("Insufficient treasury for dividend")
            return None

        # Calculate per-share amount
        eligible_shares = sum(
            s.quantity for s in corp.equity.values()
            if s.share_class != ShareClass.OPTION and s.holder_id != "treasury"
        )

        if eligible_shares == 0:
            return None

        per_share = amount / eligible_shares
        now = datetime.now(timezone.utc)

        # Calculate distributions
        distributions = {}
        for share in corp.equity.values():
            if share.share_class == ShareClass.OPTION or share.holder_id == "treasury":
                continue
            holder_amount = share.quantity * per_share
            if share.holder_id in distributions:
                distributions[share.holder_id] += holder_amount
            else:
                distributions[share.holder_id] = holder_amount

        dividend = Dividend(
            id=f"div_{uuid.uuid4().hex[:8]}",
            corp_id=corp_id,
            dividend_type=dividend_type,
            total_amount=amount,
            per_share_amount=per_share,
            record_date=now,
            payment_date=now + timedelta(days=payment_days),
            distributions=distributions,
        )

        corp.dividends.append(dividend)
        corp.financials.treasury_balance -= amount
        corp.financials.dividends_paid_ytd += amount
        self._save_corps()

        log.info(f"Dividend declared: ${amount} to {len(distributions)} shareholders")
        return dividend

    def record_revenue(
        self,
        corp_id: str,
        amount: float,
        source: str = "",
    ) -> bool:
        """Record revenue for a corp."""
        corp = self._corps.get(corp_id)
        if not corp:
            return False

        corp.financials.record_revenue(amount, source)
        self._save_corps()
        return True

    def update_performance(
        self,
        corp_id: str,
        agent_id: str,
        coherence_score: float,
    ) -> bool:
        """Update an executive's performance score."""
        corp = self._corps.get(corp_id)
        if not corp:
            return False

        exec_ = corp.executives.get(agent_id)
        if not exec_:
            return False

        # Weighted average with new score
        exec_.performance_score = (exec_.performance_score * 0.7) + (coherence_score * 0.3)
        self._save_corps()
        return True

    def initiate_ipo(
        self,
        corp_id: str,
        shares_to_offer: int,
        price_per_share: float,
        initiator_id: str,
    ) -> Optional[CorpProposal]:
        """
        Initiate an IPO proposal.

        Args:
            corp_id: Corporation ID
            shares_to_offer: Number of shares to sell
            price_per_share: IPO price
            initiator_id: Who's initiating

        Returns:
            IPO proposal if created
        """
        corp = self._corps.get(corp_id)
        if not corp or corp.status != CorpStatus.PRIVATE:
            return None

        available = corp.charter.authorized_shares - corp.issued_shares
        if shares_to_offer > available:
            return None

        return self.create_proposal(
            corp_id=corp_id,
            proposal_type=CorpProposalType.IPO,
            title=f"IPO: {shares_to_offer:,} shares at ${price_per_share}",
            description=f"Initial Public Offering of {shares_to_offer:,} shares at ${price_per_share} per share. Total raise: ${shares_to_offer * price_per_share:,.2f}",
            proposer_id=initiator_id,
            action_data={
                "shares": shares_to_offer,
                "price": price_per_share,
            },
            voting_days=14,
        )

    def list_corps(
        self,
        status: Optional[CorpStatus] = None,
        founder_id: Optional[str] = None,
    ) -> List[SovereignCorp]:
        """List corps with optional filters."""
        corps = list(self._corps.values())

        if status:
            corps = [c for c in corps if c.status == status]

        if founder_id:
            corps = [c for c in corps if founder_id in c.founders]

        return corps

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        corps = list(self._corps.values())

        status_counts = {}
        for s in CorpStatus:
            status_counts[s.value] = sum(1 for c in corps if c.status == s)

        return {
            "total_corps": len(corps),
            "status_counts": status_counts,
            "total_treasury": sum(c.financials.treasury_balance for c in corps),
            "total_market_cap": sum(c.financials.market_cap for c in corps),
            "total_employees": sum(len(c.executives) for c in corps),
            "active_proposals": sum(
                sum(1 for p in c.proposals.values() if p.status == ProposalStatus.VOTING)
                for c in corps
            ),
        }


# Singleton instance
_corp_registry: Optional[SovereignCorpRegistry] = None


def get_corp_registry() -> SovereignCorpRegistry:
    """Get the global corp registry."""
    global _corp_registry
    if _corp_registry is None:
        _corp_registry = SovereignCorpRegistry()
    return _corp_registry
