"""
Bounty Board - Task Marketplace for Agents and Humans

Ported from mumega/core/sovereign/bounty_board.py with SOS architecture.

Features:
- Bounty lifecycle (OPEN → CLAIMED → SUBMITTED → APPROVED → PAID)
- Automatic expiration and refunds
- Witness approval threshold (>= 100 $MIND)
- Integration with MindLedger

Status Flow:
    OPEN → CLAIMED → SUBMITTED → APPROVED → PAID
           ↓
         EXPIRED → REFUND_PENDING → REFUNDED
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import uuid
import json
import asyncio
from pathlib import Path

from sos.kernel import Config
from sos.observability.logging import get_logger
from sos.services.economy.ledger import get_ledger, TransactionCategory

log = get_logger("bounty_board")


class BountyStatus(str, Enum):
    """Bounty lifecycle states."""
    OPEN = "open"                    # Available for claiming
    CLAIMED = "claimed"              # Claimed, awaiting submission
    SUBMITTED = "submitted"          # Work submitted, awaiting review
    APPROVED = "approved"            # Approved, payment pending
    PAID = "paid"                    # Payment complete
    EXPIRED = "expired"              # Expired without completion
    REFUND_PENDING = "refund_pending"  # Awaiting refund
    REFUNDED = "refunded"            # Refund complete
    CANCELED = "canceled"            # Canceled by creator


@dataclass
class Bounty:
    """A task with a $MIND reward."""
    id: str
    title: str
    description: str
    reward: float  # $MIND amount
    status: BountyStatus = BountyStatus.OPEN
    constraints: List[str] = field(default_factory=list)
    timeout_hours: float = 48.0
    creator_id: str = ""
    claimant_id: Optional[str] = None
    submission_url: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    claimed_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    tx_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.expires_at is None:
            self.expires_at = self.created_at + timedelta(days=7)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "reward": self.reward,
            "status": self.status.value,
            "constraints": self.constraints,
            "timeout_hours": self.timeout_hours,
            "creator_id": self.creator_id,
            "claimant_id": self.claimant_id,
            "submission_url": self.submission_url,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "tx_id": self.tx_id,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Bounty":
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            reward=data["reward"],
            status=BountyStatus(data["status"]),
            constraints=data.get("constraints", []),
            timeout_hours=data.get("timeout_hours", 48.0),
            creator_id=data.get("creator_id", ""),
            claimant_id=data.get("claimant_id"),
            submission_url=data.get("submission_url"),
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            claimed_at=datetime.fromisoformat(data["claimed_at"]) if data.get("claimed_at") else None,
            submitted_at=datetime.fromisoformat(data["submitted_at"]) if data.get("submitted_at") else None,
            paid_at=datetime.fromisoformat(data["paid_at"]) if data.get("paid_at") else None,
            tx_id=data.get("tx_id"),
            metadata=data.get("metadata", {})
        )


class BountyBoard:
    """
    Task marketplace for agents and humans.

    Manages bounty lifecycle from creation to payment.
    Integrates with MindLedger for $MIND rewards.
    """

    WITNESS_THRESHOLD = 100.0  # Bounties >= 100 $MIND need witness approval

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".sos" / "bounties"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._bounties: Dict[str, Bounty] = {}
        self._load_bounties()

    def _load_bounties(self):
        """Load bounties from storage."""
        bounty_file = self.storage_path / "bounties.json"
        if bounty_file.exists():
            try:
                with open(bounty_file) as f:
                    data = json.load(f)
                    self._bounties = {
                        k: Bounty.from_dict(v) for k, v in data.items()
                    }
                log.info(f"Loaded {len(self._bounties)} bounties")
            except Exception as e:
                log.error(f"Failed to load bounties: {e}")

    def _save_bounties(self):
        """Save bounties to storage."""
        bounty_file = self.storage_path / "bounties.json"
        try:
            with open(bounty_file, "w") as f:
                data = {k: v.to_dict() for k, v in self._bounties.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save bounties: {e}")

    def post_bounty(
        self,
        title: str,
        description: str,
        reward: float,
        creator_id: str,
        constraints: Optional[List[str]] = None,
        timeout_hours: float = 48.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Bounty:
        """
        Post a new bounty to the board.

        Args:
            title: Bounty title
            description: Detailed requirements
            reward: $MIND reward amount
            creator_id: Creator's agent/wallet ID
            constraints: Work constraints/rules
            timeout_hours: Hours to complete after claiming
            metadata: Additional metadata

        Returns:
            The created Bounty
        """
        bounty = Bounty(
            id=uuid.uuid4().hex[:8],
            title=title,
            description=description,
            reward=reward,
            creator_id=creator_id,
            constraints=constraints or [],
            timeout_hours=timeout_hours,
            metadata=metadata or {}
        )

        self._bounties[bounty.id] = bounty
        self._save_bounties()

        log.info(f"Bounty posted: {bounty.id} - {title} ({reward} $MIND)")
        return bounty

    def claim_bounty(self, bounty_id: str, claimant_id: str) -> bool:
        """
        Claim an open bounty.

        Args:
            bounty_id: Bounty to claim
            claimant_id: Worker's agent ID

        Returns:
            True if claimed successfully
        """
        bounty = self._bounties.get(bounty_id)
        if not bounty:
            log.warning(f"Bounty not found: {bounty_id}")
            return False

        if bounty.status != BountyStatus.OPEN:
            log.warning(f"Bounty not open: {bounty_id} (status={bounty.status})")
            return False

        bounty.status = BountyStatus.CLAIMED
        bounty.claimant_id = claimant_id
        bounty.claimed_at = datetime.now(timezone.utc)
        self._save_bounties()

        log.info(f"Bounty claimed: {bounty_id} by {claimant_id}")
        return True

    def submit_solution(
        self,
        bounty_id: str,
        submission_url: str,
        claimant_id: str
    ) -> bool:
        """
        Submit work for a claimed bounty.

        Args:
            bounty_id: Bounty ID
            submission_url: URL to proof/work
            claimant_id: Must match original claimant

        Returns:
            True if submitted successfully
        """
        bounty = self._bounties.get(bounty_id)
        if not bounty:
            return False

        if bounty.status != BountyStatus.CLAIMED:
            log.warning(f"Bounty not in CLAIMED state: {bounty_id}")
            return False

        if bounty.claimant_id != claimant_id:
            log.warning(f"Claimant mismatch: {claimant_id} != {bounty.claimant_id}")
            return False

        bounty.status = BountyStatus.SUBMITTED
        bounty.submission_url = submission_url
        bounty.submitted_at = datetime.now(timezone.utc)
        self._save_bounties()

        log.info(f"Bounty submitted: {bounty_id}")
        return True

    def approve_bounty(self, bounty_id: str, approver_id: str) -> Dict[str, Any]:
        """
        Approve a submitted bounty and pay reward.

        Args:
            bounty_id: Bounty to approve
            approver_id: Witness/approver ID

        Returns:
            Result with status and tx_id
        """
        bounty = self._bounties.get(bounty_id)
        if not bounty:
            return {"status": "error", "message": "Bounty not found"}

        if bounty.status != BountyStatus.SUBMITTED:
            return {"status": "error", "message": f"Bounty not submitted (status={bounty.status})"}

        # Check witness threshold
        if bounty.reward >= self.WITNESS_THRESHOLD:
            bounty.status = BountyStatus.APPROVED
            bounty.metadata["approver_id"] = approver_id
            bounty.metadata["approved_at"] = datetime.now(timezone.utc).isoformat()
            self._save_bounties()
            return {
                "status": "pending_witness",
                "message": f"Bounty >= {self.WITNESS_THRESHOLD} $MIND requires witness approval",
                "bounty_id": bounty_id
            }

        # Direct payment for small bounties
        return self._pay_bounty(bounty)

    def _pay_bounty(self, bounty: Bounty) -> Dict[str, Any]:
        """Execute payment for approved bounty."""
        try:
            ledger = get_ledger()
            tx_id = ledger.credit(
                agent_id=bounty.claimant_id,
                amount=bounty.reward,
                category=TransactionCategory.BOUNTY,
                description=f"Bounty: {bounty.title[:30]}",
                metadata={
                    "bounty_id": bounty.id,
                    "creator_id": bounty.creator_id
                }
            )

            bounty.status = BountyStatus.PAID
            bounty.paid_at = datetime.now(timezone.utc)
            bounty.tx_id = tx_id
            self._save_bounties()

            log.info(f"Bounty paid: {bounty.id} -> {bounty.claimant_id} ({bounty.reward} $MIND)")
            return {
                "status": "paid",
                "tx_id": tx_id,
                "reward": bounty.reward,
                "claimant_id": bounty.claimant_id
            }
        except Exception as e:
            log.error(f"Payment failed: {e}")
            return {"status": "error", "message": str(e)}

    def reject_bounty(self, bounty_id: str, reason: str) -> bool:
        """Reject a submitted bounty."""
        bounty = self._bounties.get(bounty_id)
        if not bounty or bounty.status != BountyStatus.SUBMITTED:
            return False

        bounty.status = BountyStatus.OPEN
        bounty.claimant_id = None
        bounty.claimed_at = None
        bounty.submitted_at = None
        bounty.submission_url = None
        bounty.metadata["rejection_reason"] = reason
        bounty.metadata["rejected_at"] = datetime.now(timezone.utc).isoformat()
        self._save_bounties()

        log.info(f"Bounty rejected: {bounty_id} - {reason}")
        return True

    def expire_stale_bounties(self) -> List[str]:
        """Expire bounties that exceeded timeout."""
        now = datetime.now(timezone.utc)
        expired = []

        for bounty in self._bounties.values():
            if bounty.status == BountyStatus.CLAIMED:
                if bounty.claimed_at:
                    deadline = bounty.claimed_at + timedelta(hours=bounty.timeout_hours)
                    if now > deadline:
                        bounty.status = BountyStatus.EXPIRED
                        expired.append(bounty.id)
                        log.info(f"Bounty expired: {bounty.id}")

        if expired:
            self._save_bounties()

        return expired

    def list_bounties(
        self,
        status: Optional[BountyStatus] = None,
        limit: int = 50
    ) -> List[Bounty]:
        """List bounties, optionally filtered by status."""
        bounties = list(self._bounties.values())

        if status:
            bounties = [b for b in bounties if b.status == status]

        return sorted(bounties, key=lambda b: b.created_at, reverse=True)[:limit]

    def get_bounty(self, bounty_id: str) -> Optional[Bounty]:
        """Get a specific bounty."""
        return self._bounties.get(bounty_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get bounty board statistics."""
        bounties = list(self._bounties.values())

        status_counts = {}
        for status in BountyStatus:
            status_counts[status.value] = sum(1 for b in bounties if b.status == status)

        total_posted = sum(b.reward for b in bounties)
        total_paid = sum(b.reward for b in bounties if b.status == BountyStatus.PAID)

        return {
            "total_bounties": len(bounties),
            "status_counts": status_counts,
            "total_posted_mind": total_posted,
            "total_paid_mind": total_paid,
            "open_bounties": status_counts.get("open", 0)
        }


# Singleton instance
_bounty_board: Optional[BountyBoard] = None


def get_bounty_board() -> BountyBoard:
    """Get the global bounty board instance."""
    global _bounty_board
    if _bounty_board is None:
        _bounty_board = BountyBoard()
    return _bounty_board
