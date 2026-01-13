"""
Guild & Company Registry - Institutional Identities for SOS

Implements multi-sig treasury and institutional governance.

Features:
- Guild creation with founding members
- Multi-sig treasury (M-of-N approval)
- Membership management (join, leave, roles)
- Revenue sharing and profit distribution
- Governance proposals and voting

Guild Types:
- COMPANY: Commercial entity with profit distribution
- DAO: Decentralized governance with proposal voting
- SQUAD: Task-focused team with shared bounties
- SYNDICATE: Investment group with pooled treasury
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import uuid
import json
from pathlib import Path

from sos.observability.logging import get_logger
from sos.services.economy.ledger import get_ledger, TransactionCategory

log = get_logger("guild_registry")


class GuildType(str, Enum):
    """Type of institutional entity."""
    COMPANY = "company"       # Commercial with profit sharing
    DAO = "dao"              # Decentralized governance
    SQUAD = "squad"          # Task-focused team
    SYNDICATE = "syndicate"  # Investment pool


class MemberRole(str, Enum):
    """Role within a guild."""
    FOUNDER = "founder"      # Original creator, full control
    ADMIN = "admin"          # Can manage members, treasury ops
    MEMBER = "member"        # Standard member, can vote
    CONTRIBUTOR = "contributor"  # Limited, task-only access


class ProposalStatus(str, Enum):
    """Status of a governance proposal."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


@dataclass
class GuildMember:
    """A member of a guild."""
    agent_id: str
    role: MemberRole
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revenue_share: float = 0.0  # Percentage of revenue (0.0-100.0)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "joined_at": self.joined_at.isoformat(),
            "revenue_share": self.revenue_share,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GuildMember":
        return cls(
            agent_id=data["agent_id"],
            role=MemberRole(data["role"]),
            joined_at=datetime.fromisoformat(data["joined_at"]),
            revenue_share=data.get("revenue_share", 0.0),
            metadata=data.get("metadata", {})
        )


@dataclass
class TreasuryConfig:
    """Multi-sig treasury configuration."""
    required_signatures: int = 2  # M signatures required
    total_signers: int = 3        # N total signers
    signers: List[str] = field(default_factory=list)  # Agent IDs
    daily_limit: float = 1000.0   # Max daily spend without proposal
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "required_signatures": self.required_signatures,
            "total_signers": self.total_signers,
            "signers": self.signers,
            "daily_limit": self.daily_limit,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TreasuryConfig":
        return cls(
            required_signatures=data.get("required_signatures", 2),
            total_signers=data.get("total_signers", 3),
            signers=data.get("signers", []),
            daily_limit=data.get("daily_limit", 1000.0),
            metadata=data.get("metadata", {})
        )


@dataclass
class Proposal:
    """A governance proposal."""
    id: str
    guild_id: str
    title: str
    description: str
    proposal_type: str  # "treasury", "membership", "governance"
    proposer_id: str
    status: ProposalStatus = ProposalStatus.PENDING
    votes_for: Set[str] = field(default_factory=set)
    votes_against: Set[str] = field(default_factory=set)
    required_votes: int = 2
    action_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "guild_id": self.guild_id,
            "title": self.title,
            "description": self.description,
            "proposal_type": self.proposal_type,
            "proposer_id": self.proposer_id,
            "status": self.status.value,
            "votes_for": list(self.votes_for),
            "votes_against": list(self.votes_against),
            "required_votes": self.required_votes,
            "action_data": self.action_data,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proposal":
        return cls(
            id=data["id"],
            guild_id=data["guild_id"],
            title=data["title"],
            description=data["description"],
            proposal_type=data["proposal_type"],
            proposer_id=data["proposer_id"],
            status=ProposalStatus(data["status"]),
            votes_for=set(data.get("votes_for", [])),
            votes_against=set(data.get("votes_against", [])),
            required_votes=data.get("required_votes", 2),
            action_data=data.get("action_data", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            executed_at=datetime.fromisoformat(data["executed_at"]) if data.get("executed_at") else None
        )


@dataclass
class Guild:
    """An institutional entity in SOS."""
    id: str
    name: str
    guild_type: GuildType
    description: str = ""
    members: Dict[str, GuildMember] = field(default_factory=dict)
    treasury: TreasuryConfig = field(default_factory=TreasuryConfig)
    treasury_balance: float = 0.0
    proposals: Dict[str, Proposal] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "guild_type": self.guild_type.value,
            "description": self.description,
            "members": {k: v.to_dict() for k, v in self.members.items()},
            "treasury": self.treasury.to_dict(),
            "treasury_balance": self.treasury_balance,
            "proposals": {k: v.to_dict() for k, v in self.proposals.items()},
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Guild":
        return cls(
            id=data["id"],
            name=data["name"],
            guild_type=GuildType(data["guild_type"]),
            description=data.get("description", ""),
            members={k: GuildMember.from_dict(v) for k, v in data.get("members", {}).items()},
            treasury=TreasuryConfig.from_dict(data.get("treasury", {})),
            treasury_balance=data.get("treasury_balance", 0.0),
            proposals={k: Proposal.from_dict(v) for k, v in data.get("proposals", {}).items()},
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {})
        )


class GuildRegistry:
    """
    Registry of guilds and companies.

    Manages institutional identities, multi-sig treasury, and governance.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".sos" / "guilds"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._guilds: Dict[str, Guild] = {}
        self._load_guilds()

    def _load_guilds(self):
        """Load guilds from storage."""
        guild_file = self.storage_path / "guilds.json"
        if guild_file.exists():
            try:
                with open(guild_file) as f:
                    data = json.load(f)
                    self._guilds = {k: Guild.from_dict(v) for k, v in data.items()}
                log.info(f"Loaded {len(self._guilds)} guilds")
            except Exception as e:
                log.error(f"Failed to load guilds: {e}")

    def _save_guilds(self):
        """Save guilds to storage."""
        guild_file = self.storage_path / "guilds.json"
        try:
            with open(guild_file, "w") as f:
                data = {k: v.to_dict() for k, v in self._guilds.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save guilds: {e}")

    def create_guild(
        self,
        name: str,
        guild_type: GuildType,
        founder_id: str,
        description: str = "",
        initial_signers: Optional[List[str]] = None,
        required_signatures: int = 2,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Guild:
        """
        Create a new guild.

        Args:
            name: Guild name
            guild_type: Type of guild
            founder_id: Founding agent ID
            description: Guild description
            initial_signers: Treasury signers (defaults to founder)
            required_signatures: M-of-N for treasury
            metadata: Additional metadata

        Returns:
            The created Guild
        """
        guild_id = f"guild_{uuid.uuid4().hex[:8]}"

        signers = initial_signers or [founder_id]
        treasury = TreasuryConfig(
            required_signatures=min(required_signatures, len(signers)),
            total_signers=len(signers),
            signers=signers
        )

        founder = GuildMember(
            agent_id=founder_id,
            role=MemberRole.FOUNDER,
            revenue_share=100.0  # Founder starts with 100%
        )

        guild = Guild(
            id=guild_id,
            name=name,
            guild_type=guild_type,
            description=description,
            members={founder_id: founder},
            treasury=treasury,
            metadata=metadata or {}
        )

        self._guilds[guild_id] = guild
        self._save_guilds()

        log.info(f"Guild created: {guild_id} - {name} ({guild_type.value})")
        return guild

    def get(self, guild_id: str) -> Optional[Guild]:
        """Get a guild by ID."""
        return self._guilds.get(guild_id)

    def add_member(
        self,
        guild_id: str,
        agent_id: str,
        role: MemberRole = MemberRole.MEMBER,
        revenue_share: float = 0.0,
        added_by: Optional[str] = None
    ) -> bool:
        """Add a member to a guild."""
        guild = self._guilds.get(guild_id)
        if not guild:
            return False

        # Check permission (admin or founder can add)
        if added_by:
            adder = guild.members.get(added_by)
            if not adder or adder.role not in [MemberRole.FOUNDER, MemberRole.ADMIN]:
                log.warning(f"Permission denied: {added_by} cannot add members")
                return False

        member = GuildMember(
            agent_id=agent_id,
            role=role,
            revenue_share=revenue_share
        )

        guild.members[agent_id] = member
        self._save_guilds()

        log.info(f"Member added: {agent_id} to {guild_id} as {role.value}")
        return True

    def remove_member(
        self,
        guild_id: str,
        agent_id: str,
        removed_by: str
    ) -> bool:
        """Remove a member from a guild."""
        guild = self._guilds.get(guild_id)
        if not guild or agent_id not in guild.members:
            return False

        # Check permission
        remover = guild.members.get(removed_by)
        target = guild.members.get(agent_id)

        if not remover:
            return False

        # Can't remove founder
        if target.role == MemberRole.FOUNDER:
            return False

        # Only founder/admin can remove
        if remover.role not in [MemberRole.FOUNDER, MemberRole.ADMIN]:
            return False

        del guild.members[agent_id]
        self._save_guilds()

        log.info(f"Member removed: {agent_id} from {guild_id}")
        return True

    def deposit_treasury(
        self,
        guild_id: str,
        amount: float,
        depositor_id: str
    ) -> bool:
        """Deposit $MIND to guild treasury."""
        guild = self._guilds.get(guild_id)
        if not guild:
            return False

        guild.treasury_balance += amount
        self._save_guilds()

        log.info(f"Treasury deposit: {amount} $MIND to {guild_id} from {depositor_id}")
        return True

    def create_proposal(
        self,
        guild_id: str,
        title: str,
        description: str,
        proposal_type: str,
        proposer_id: str,
        action_data: Optional[Dict[str, Any]] = None
    ) -> Optional[Proposal]:
        """Create a governance proposal."""
        guild = self._guilds.get(guild_id)
        if not guild or proposer_id not in guild.members:
            return None

        proposal = Proposal(
            id=f"prop_{uuid.uuid4().hex[:8]}",
            guild_id=guild_id,
            title=title,
            description=description,
            proposal_type=proposal_type,
            proposer_id=proposer_id,
            required_votes=guild.treasury.required_signatures,
            action_data=action_data or {}
        )

        guild.proposals[proposal.id] = proposal
        self._save_guilds()

        log.info(f"Proposal created: {proposal.id} in {guild_id}")
        return proposal

    def vote_proposal(
        self,
        guild_id: str,
        proposal_id: str,
        voter_id: str,
        approve: bool
    ) -> bool:
        """Vote on a proposal."""
        guild = self._guilds.get(guild_id)
        if not guild:
            return False

        proposal = guild.proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.PENDING:
            return False

        if voter_id not in guild.members:
            return False

        # Only signers can vote on treasury proposals
        if proposal.proposal_type == "treasury":
            if voter_id not in guild.treasury.signers:
                return False

        if approve:
            proposal.votes_for.add(voter_id)
            proposal.votes_against.discard(voter_id)
        else:
            proposal.votes_against.add(voter_id)
            proposal.votes_for.discard(voter_id)

        # Check if passed
        if len(proposal.votes_for) >= proposal.required_votes:
            proposal.status = ProposalStatus.APPROVED

        # Check if rejected
        total_voters = len(guild.members) if proposal.proposal_type != "treasury" else len(guild.treasury.signers)
        if len(proposal.votes_against) > total_voters - proposal.required_votes:
            proposal.status = ProposalStatus.REJECTED

        self._save_guilds()

        log.info(f"Vote recorded: {voter_id} {'approved' if approve else 'rejected'} {proposal_id}")
        return True

    def list_guilds(
        self,
        guild_type: Optional[GuildType] = None,
        member_id: Optional[str] = None
    ) -> List[Guild]:
        """List guilds with optional filters."""
        guilds = list(self._guilds.values())

        if guild_type:
            guilds = [g for g in guilds if g.guild_type == guild_type]

        if member_id:
            guilds = [g for g in guilds if member_id in g.members]

        return guilds

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        guilds = list(self._guilds.values())

        type_counts = {}
        for gt in GuildType:
            type_counts[gt.value] = sum(1 for g in guilds if g.guild_type == gt)

        return {
            "total_guilds": len(guilds),
            "type_counts": type_counts,
            "total_members": sum(len(g.members) for g in guilds),
            "total_treasury": sum(g.treasury_balance for g in guilds),
            "active_proposals": sum(
                sum(1 for p in g.proposals.values() if p.status == ProposalStatus.PENDING)
                for g in guilds
            )
        }


# Singleton instance
_guild_registry: Optional[GuildRegistry] = None


def get_guild_registry() -> GuildRegistry:
    """Get the global guild registry."""
    global _guild_registry
    if _guild_registry is None:
        _guild_registry = GuildRegistry()
    return _guild_registry
