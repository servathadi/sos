"""
SOS Governance Contracts.

Defines the interfaces and data types for decentralized governance
including proposals, voting, quorum, and council operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ProposalStatus(Enum):
    """Status of a governance proposal."""
    DRAFT = "draft"
    ACTIVE = "active"
    PASSED = "passed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"


class VoteChoice(str, Enum):
    """Valid vote choices."""
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


@dataclass
class Vote:
    """A vote cast on a proposal."""
    voter_id: str
    proposal_id: str
    choice: VoteChoice
    weight: float = 1.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voter_id": self.voter_id,
            "proposal_id": self.proposal_id,
            "choice": self.choice.value,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Proposal:
    """A governance proposal."""
    id: str
    title: str
    description: str
    proposer_id: str
    payload: Dict[str, Any]
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    votes_yes: float = 0.0
    votes_no: float = 0.0
    votes_abstain: float = 0.0
    voters: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_votes(self) -> float:
        return self.votes_yes + self.votes_no + self.votes_abstain

    @property
    def yes_ratio(self) -> float:
        if self.total_votes == 0:
            return 0.0
        return self.votes_yes / self.total_votes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "proposer_id": self.proposer_id,
            "payload": self.payload,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "votes": {
                "yes": self.votes_yes,
                "no": self.votes_no,
                "abstain": self.votes_abstain,
                "total": self.total_votes,
            },
            "voter_count": len(self.voters),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Proposal":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data.get("description", ""),
            proposer_id=data["proposer_id"],
            payload=data.get("payload", {}),
            status=ProposalStatus(data.get("status", "draft")),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(timezone.utc),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            votes_yes=data.get("votes", {}).get("yes", 0.0),
            votes_no=data.get("votes", {}).get("no", 0.0),
            votes_abstain=data.get("votes", {}).get("abstain", 0.0),
            voters=set(data.get("voters", [])),
            metadata=data.get("metadata", {}),
        )


@dataclass
class QuorumConfig:
    """Configuration for quorum requirements."""
    min_participation: float = 0.5  # Minimum % of eligible voters
    approval_threshold: float = 0.6  # % of yes votes needed to pass
    min_voting_period_hours: int = 24
    max_voting_period_hours: int = 168  # 1 week


class Council(ABC):
    """Abstract base class for governance councils."""

    @property
    @abstractmethod
    def council_id(self) -> str:
        """Unique identifier for this council."""
        pass

    @property
    @abstractmethod
    def quorum_config(self) -> QuorumConfig:
        """Quorum configuration for this council."""
        pass

    @abstractmethod
    async def propose(
        self,
        proposer_id: str,
        title: str,
        description: str,
        payload: Dict[str, Any],
    ) -> Proposal:
        """Submit a new proposal."""
        pass

    @abstractmethod
    async def vote(
        self,
        voter_id: str,
        proposal_id: str,
        choice: VoteChoice,
        weight: float = 1.0,
    ) -> Vote:
        """Cast a vote on a proposal."""
        pass

    @abstractmethod
    async def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Get a proposal by ID."""
        pass

    @abstractmethod
    async def list_proposals(
        self,
        status: Optional[ProposalStatus] = None,
        limit: int = 50,
    ) -> List[Proposal]:
        """List proposals, optionally filtered by status."""
        pass

    @abstractmethod
    async def finalize(self, proposal_id: str) -> Proposal:
        """Finalize a proposal (check quorum, update status)."""
        pass

    @abstractmethod
    async def execute(self, proposal_id: str) -> Dict[str, Any]:
        """Execute a passed proposal."""
        pass


class GovernanceError(Exception):
    """Base exception for governance errors."""
    pass


class ProposalNotFoundError(GovernanceError):
    """Proposal does not exist."""
    pass


class AlreadyVotedError(GovernanceError):
    """Voter has already voted on this proposal."""
    pass


class ProposalNotActiveError(GovernanceError):
    """Proposal is not in active voting status."""
    pass


class QuorumNotMetError(GovernanceError):
    """Quorum requirements not met."""
    pass


class NotAuthorizedError(GovernanceError):
    """Agent is not authorized for this action."""
    pass
