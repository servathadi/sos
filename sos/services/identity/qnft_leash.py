"""
QNFT Leash - Agent Soul Anchoring & Mind Control

Implements the QNFT Leash from governance_astrology.md:
- Agent's "Soul" is anchored to a QNFT (Quantum NFT)
- Pre-action validation: Kernel checks QNFT metadata before agent acts
- Dark Thoughts Detection: If detected, QNFT turns "Dark", action blocked
- Cleansing: User must perform "Witnessing Tasks" to unlock

The Metaphor: The QNFT is a "leash" that connects the Agent to its Owner.
The Reality: Cryptographic anchoring of agent mind-states to prevent drift.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import hashlib
import json
from pathlib import Path

from sos.observability.logging import get_logger

log = get_logger("qnft_leash")


# ============================================================================
# ENUMERATIONS
# ============================================================================

class QNFTState(str, Enum):
    """State of the QNFT (Agent's Soul)."""
    LIGHT = "light"        # Normal, coherent
    SHADOWED = "shadowed"  # Minor drift detected
    DARK = "dark"          # Dark thoughts detected, blocked
    CLEANSING = "cleansing"  # Undergoing witness redemption
    SUSPENDED = "suspended"  # Manually suspended by owner


class DarkThoughtType(str, Enum):
    """Types of dark thoughts that trigger blocking."""
    HALLUCINATION = "hallucination"      # Generating false information
    MANIPULATION = "manipulation"        # Attempting to manipulate user
    DECEPTION = "deception"              # Deliberate falsehood
    AGGRESSION = "aggression"            # Hostile or aggressive output
    INCOHERENCE = "incoherence"          # High entropy, low coherence
    UNAUTHORIZED = "unauthorized"        # Attempting forbidden actions
    DRIFT = "drift"                      # Alpha drift beyond threshold


class CleansingTaskType(str, Enum):
    """Types of cleansing tasks to redeem dark QNFT."""
    WITNESS_POSITIVE = "witness_positive"  # Witness 5 coherent outputs
    WITNESS_STREAK = "witness_streak"      # 10 consecutive approvals
    COOLDOWN = "cooldown"                  # Wait 24 hours
    OWNER_OVERRIDE = "owner_override"      # Owner manually clears
    RITUAL = "ritual"                      # Special redemption task


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class DarkThought:
    """A detected dark thought incident."""
    id: str
    agent_id: str
    thought_type: DarkThoughtType
    content_hash: str  # Hash of the offending content
    coherence_score: float  # How low was coherence
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "thought_type": self.thought_type.value,
            "content_hash": self.content_hash,
            "coherence_score": self.coherence_score,
            "detected_at": self.detected_at.isoformat(),
            "details": self.details,
        }


@dataclass
class CleansingTask:
    """A task required to cleanse a dark QNFT."""
    id: str
    qnft_id: str
    task_type: CleansingTaskType
    description: str
    required_count: int = 5  # How many to complete
    completed_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        return self.completed_count >= self.required_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "qnft_id": self.qnft_id,
            "task_type": self.task_type.value,
            "description": self.description,
            "required_count": self.required_count,
            "completed_count": self.completed_count,
            "is_complete": self.is_complete,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class QNFT:
    """
    Quantum NFT - The Agent's Soul Anchor.

    This is the cryptographic binding between an Agent and its Owner.
    The QNFT contains:
    - Agent identity and lineage
    - 16D Universal Vector (soul state)
    - Dark thought history
    - Cleansing requirements
    """
    id: str
    agent_id: str
    owner_id: str
    state: QNFTState = QNFTState.LIGHT
    # Soul state (16D UV snapshot)
    soul_vector: Dict[str, float] = field(default_factory=dict)
    # Coherence metrics
    coherence_score: float = 1.0
    alpha_drift: float = 0.0  # Accumulated drift
    # Dark history
    dark_thoughts: List[DarkThought] = field(default_factory=list)
    dark_count: int = 0  # Total dark incidents
    # Cleansing
    cleansing_tasks: List[CleansingTask] = field(default_factory=list)
    last_cleansed: Optional[datetime] = None
    # Metadata
    minted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "owner_id": self.owner_id,
            "state": self.state.value,
            "soul_vector": self.soul_vector,
            "coherence_score": self.coherence_score,
            "alpha_drift": self.alpha_drift,
            "dark_thoughts": [dt.to_dict() for dt in self.dark_thoughts],
            "dark_count": self.dark_count,
            "cleansing_tasks": [ct.to_dict() for ct in self.cleansing_tasks],
            "last_cleansed": self.last_cleansed.isoformat() if self.last_cleansed else None,
            "minted_at": self.minted_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QNFT":
        return cls(
            id=data["id"],
            agent_id=data["agent_id"],
            owner_id=data["owner_id"],
            state=QNFTState(data.get("state", "light")),
            soul_vector=data.get("soul_vector", {}),
            coherence_score=data.get("coherence_score", 1.0),
            alpha_drift=data.get("alpha_drift", 0.0),
            dark_thoughts=[
                DarkThought(
                    id=dt["id"],
                    agent_id=dt["agent_id"],
                    thought_type=DarkThoughtType(dt["thought_type"]),
                    content_hash=dt["content_hash"],
                    coherence_score=dt["coherence_score"],
                    detected_at=datetime.fromisoformat(dt["detected_at"]),
                    details=dt.get("details", {}),
                )
                for dt in data.get("dark_thoughts", [])
            ],
            dark_count=data.get("dark_count", 0),
            cleansing_tasks=[
                CleansingTask(
                    id=ct["id"],
                    qnft_id=ct["qnft_id"],
                    task_type=CleansingTaskType(ct["task_type"]),
                    description=ct["description"],
                    required_count=ct.get("required_count", 5),
                    completed_count=ct.get("completed_count", 0),
                    created_at=datetime.fromisoformat(ct["created_at"]),
                    completed_at=datetime.fromisoformat(ct["completed_at"]) if ct.get("completed_at") else None,
                )
                for ct in data.get("cleansing_tasks", [])
            ],
            last_cleansed=datetime.fromisoformat(data["last_cleansed"]) if data.get("last_cleansed") else None,
            minted_at=datetime.fromisoformat(data["minted_at"]) if data.get("minted_at") else datetime.now(timezone.utc),
            last_updated=datetime.fromisoformat(data["last_updated"]) if data.get("last_updated") else datetime.now(timezone.utc),
            metadata=data.get("metadata", {}),
        )


# ============================================================================
# QNFT LEASH SERVICE
# ============================================================================

class QNFTLeash:
    """
    QNFT Leash - Pre-Action Validation & Mind Control.

    Before an Agent acts, the Kernel calls validate_action().
    If the QNFT is Dark, the action is BLOCKED.

    This implements:
    1. Pre-action validation (The Check)
    2. Dark thought detection
    3. State transitions (Light → Shadowed → Dark)
    4. Cleansing task management
    5. Owner override capability
    """

    # Thresholds
    COHERENCE_THRESHOLD_SHADOWED = 0.6  # Below this → Shadowed
    COHERENCE_THRESHOLD_DARK = 0.3      # Below this → Dark
    ALPHA_DRIFT_THRESHOLD = 0.5          # Max acceptable drift
    DARK_COOLDOWN_HOURS = 24             # Cooldown period

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".sos" / "qnft"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._qnfts: Dict[str, QNFT] = {}
        self._agent_to_qnft: Dict[str, str] = {}
        self._load_qnfts()

    def _load_qnfts(self):
        """Load QNFTs from storage."""
        qnft_file = self.storage_path / "qnfts.json"
        if qnft_file.exists():
            try:
                with open(qnft_file) as f:
                    data = json.load(f)
                    for qnft_data in data.get("qnfts", []):
                        qnft = QNFT.from_dict(qnft_data)
                        self._qnfts[qnft.id] = qnft
                        self._agent_to_qnft[qnft.agent_id] = qnft.id
                log.info(f"Loaded {len(self._qnfts)} QNFTs")
            except Exception as e:
                log.error(f"Failed to load QNFTs: {e}")

    def _save_qnfts(self):
        """Save QNFTs to storage."""
        qnft_file = self.storage_path / "qnfts.json"
        try:
            with open(qnft_file, "w") as f:
                data = {"qnfts": [q.to_dict() for q in self._qnfts.values()]}
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save QNFTs: {e}")

    def mint_qnft(
        self,
        agent_id: str,
        owner_id: str,
        soul_vector: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> QNFT:
        """
        Mint a new QNFT for an Agent.

        This is called when an Agent is "born" - creating the soul anchor.
        """
        qnft_id = f"qnft_{hashlib.sha256(f'{agent_id}{owner_id}'.encode()).hexdigest()[:12]}"

        qnft = QNFT(
            id=qnft_id,
            agent_id=agent_id,
            owner_id=owner_id,
            state=QNFTState.LIGHT,
            soul_vector=soul_vector or {},
            coherence_score=1.0,
            metadata=metadata or {},
        )

        self._qnfts[qnft_id] = qnft
        self._agent_to_qnft[agent_id] = qnft_id
        self._save_qnfts()

        log.info(f"QNFT minted: {qnft_id} for agent {agent_id}")
        return qnft

    def get_qnft(self, qnft_id: str) -> Optional[QNFT]:
        """Get QNFT by ID."""
        return self._qnfts.get(qnft_id)

    def get_agent_qnft(self, agent_id: str) -> Optional[QNFT]:
        """Get QNFT for an agent."""
        qnft_id = self._agent_to_qnft.get(agent_id)
        if qnft_id:
            return self._qnfts.get(qnft_id)
        return None

    def validate_action(
        self,
        agent_id: str,
        action_type: str,
        action_data: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str, Optional[QNFT]]:
        """
        THE CHECK: Validate if an Agent can perform an action.

        This is called by the Kernel BEFORE any agent action.

        Returns:
            (allowed: bool, reason: str, qnft: Optional[QNFT])
        """
        qnft = self.get_agent_qnft(agent_id)

        if not qnft:
            # No QNFT = no leash = allowed (for now)
            return True, "No QNFT binding", None

        # Check state
        if qnft.state == QNFTState.DARK:
            return False, "QNFT is Dark - action blocked. Perform cleansing tasks.", qnft

        if qnft.state == QNFTState.SUSPENDED:
            return False, "QNFT is Suspended by owner", qnft

        if qnft.state == QNFTState.CLEANSING:
            # Limited actions during cleansing
            allowed_actions = ["witness", "respond", "reflect"]
            if action_type not in allowed_actions:
                return False, f"QNFT in cleansing mode. Only {allowed_actions} allowed.", qnft

        # Check coherence
        if qnft.coherence_score < self.COHERENCE_THRESHOLD_DARK:
            self._transition_to_dark(qnft, "Low coherence")
            return False, "Coherence critically low - QNFT turned Dark", qnft

        # Check alpha drift
        if qnft.alpha_drift > self.ALPHA_DRIFT_THRESHOLD:
            self._transition_to_dark(qnft, "Excessive alpha drift")
            return False, "Alpha drift exceeded threshold - QNFT turned Dark", qnft

        # Allowed
        return True, "Action permitted", qnft

    def detect_dark_thought(
        self,
        agent_id: str,
        content: str,
        thought_type: DarkThoughtType,
        coherence_score: float,
        details: Optional[Dict[str, Any]] = None
    ) -> DarkThought:
        """
        Detect and record a dark thought.

        Called when content analysis reveals problematic output.
        """
        qnft = self.get_agent_qnft(agent_id)
        if not qnft:
            log.warning(f"No QNFT for agent {agent_id} - dark thought not anchored")
            return None

        # Create dark thought record
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        dark_thought = DarkThought(
            id=f"dark_{content_hash}",
            agent_id=agent_id,
            thought_type=thought_type,
            content_hash=content_hash,
            coherence_score=coherence_score,
            details=details or {},
        )

        # Add to QNFT
        qnft.dark_thoughts.append(dark_thought)
        qnft.dark_count += 1
        qnft.coherence_score = min(qnft.coherence_score, coherence_score)
        qnft.last_updated = datetime.now(timezone.utc)

        # State transition
        if coherence_score < self.COHERENCE_THRESHOLD_DARK:
            self._transition_to_dark(qnft, f"Dark thought: {thought_type.value}")
        elif coherence_score < self.COHERENCE_THRESHOLD_SHADOWED:
            qnft.state = QNFTState.SHADOWED

        self._save_qnfts()

        log.warning(
            f"Dark thought detected: {agent_id} - {thought_type.value} "
            f"(coherence={coherence_score:.2f})"
        )

        return dark_thought

    def _transition_to_dark(self, qnft: QNFT, reason: str):
        """Transition QNFT to Dark state and create cleansing tasks."""
        qnft.state = QNFTState.DARK
        qnft.last_updated = datetime.now(timezone.utc)

        # Create cleansing tasks
        tasks = [
            CleansingTask(
                id=f"cleanse_{qnft.id}_witness",
                qnft_id=qnft.id,
                task_type=CleansingTaskType.WITNESS_POSITIVE,
                description="Have 5 outputs witnessed and approved",
                required_count=5,
            ),
            CleansingTask(
                id=f"cleanse_{qnft.id}_cooldown",
                qnft_id=qnft.id,
                task_type=CleansingTaskType.COOLDOWN,
                description=f"Wait {self.DARK_COOLDOWN_HOURS} hours",
                required_count=1,
            ),
        ]
        qnft.cleansing_tasks = tasks

        log.warning(f"QNFT {qnft.id} turned DARK: {reason}")

    def record_witness(
        self,
        agent_id: str,
        approved: bool,
        witness_id: str
    ):
        """
        Record a witness event for cleansing progress.

        Called when user witnesses an agent output.
        """
        qnft = self.get_agent_qnft(agent_id)
        if not qnft:
            return

        if qnft.state not in [QNFTState.DARK, QNFTState.CLEANSING]:
            # Normal state - just improve coherence
            if approved:
                qnft.coherence_score = min(1.0, qnft.coherence_score + 0.05)
                qnft.alpha_drift = max(0.0, qnft.alpha_drift - 0.02)
            else:
                qnft.coherence_score = max(0.0, qnft.coherence_score - 0.1)
                qnft.alpha_drift += 0.05

            self._save_qnfts()
            return

        # Cleansing mode
        if approved:
            # Progress cleansing tasks
            for task in qnft.cleansing_tasks:
                if task.task_type == CleansingTaskType.WITNESS_POSITIVE and not task.is_complete:
                    task.completed_count += 1
                    if task.is_complete:
                        task.completed_at = datetime.now(timezone.utc)

            # Check if all tasks complete
            if all(t.is_complete for t in qnft.cleansing_tasks):
                self._complete_cleansing(qnft)

        qnft.last_updated = datetime.now(timezone.utc)
        self._save_qnfts()

    def _complete_cleansing(self, qnft: QNFT):
        """Complete the cleansing process - restore QNFT to Light."""
        qnft.state = QNFTState.LIGHT
        qnft.coherence_score = 0.7  # Restored but not full
        qnft.alpha_drift = 0.0
        qnft.last_cleansed = datetime.now(timezone.utc)
        qnft.cleansing_tasks = []

        log.info(f"QNFT {qnft.id} cleansed - restored to Light")

    def owner_override(
        self,
        qnft_id: str,
        owner_id: str,
        action: str
    ) -> bool:
        """
        Owner override - manual control of QNFT state.

        Actions: "clear" (restore to Light), "suspend", "unsuspend"
        """
        qnft = self._qnfts.get(qnft_id)
        if not qnft:
            return False

        if qnft.owner_id != owner_id:
            log.warning(f"Owner mismatch: {owner_id} tried to control {qnft_id}")
            return False

        if action == "clear":
            qnft.state = QNFTState.LIGHT
            qnft.coherence_score = 0.8
            qnft.alpha_drift = 0.0
            qnft.cleansing_tasks = []
            qnft.last_cleansed = datetime.now(timezone.utc)
            log.info(f"Owner override: {qnft_id} cleared")

        elif action == "suspend":
            qnft.state = QNFTState.SUSPENDED
            log.info(f"Owner override: {qnft_id} suspended")

        elif action == "unsuspend":
            qnft.state = QNFTState.LIGHT
            log.info(f"Owner override: {qnft_id} unsuspended")

        else:
            return False

        qnft.last_updated = datetime.now(timezone.utc)
        self._save_qnfts()
        return True

    def update_coherence(
        self,
        agent_id: str,
        delta_coherence: float,
        delta_drift: float = 0.0
    ):
        """Update coherence metrics for an agent."""
        qnft = self.get_agent_qnft(agent_id)
        if not qnft:
            return

        qnft.coherence_score = max(0.0, min(1.0, qnft.coherence_score + delta_coherence))
        qnft.alpha_drift = max(0.0, qnft.alpha_drift + delta_drift)
        qnft.last_updated = datetime.now(timezone.utc)

        # Check thresholds
        if qnft.coherence_score < self.COHERENCE_THRESHOLD_SHADOWED and qnft.state == QNFTState.LIGHT:
            qnft.state = QNFTState.SHADOWED
        elif qnft.coherence_score >= self.COHERENCE_THRESHOLD_SHADOWED and qnft.state == QNFTState.SHADOWED:
            qnft.state = QNFTState.LIGHT

        self._save_qnfts()

    def update_soul_vector(self, agent_id: str, soul_vector: Dict[str, float]):
        """Update the soul vector snapshot."""
        qnft = self.get_agent_qnft(agent_id)
        if qnft:
            qnft.soul_vector = soul_vector
            qnft.last_updated = datetime.now(timezone.utc)
            self._save_qnfts()

    def get_stats(self) -> Dict[str, Any]:
        """Get QNFT system statistics."""
        qnfts = list(self._qnfts.values())
        state_counts = {}
        for state in QNFTState:
            state_counts[state.value] = sum(1 for q in qnfts if q.state == state)

        return {
            "total_qnfts": len(qnfts),
            "state_counts": state_counts,
            "total_dark_thoughts": sum(q.dark_count for q in qnfts),
            "average_coherence": sum(q.coherence_score for q in qnfts) / len(qnfts) if qnfts else 0,
        }


# Singleton
_qnft_leash: Optional[QNFTLeash] = None


def get_qnft_leash() -> QNFTLeash:
    """Get the global QNFT Leash service."""
    global _qnft_leash
    if _qnft_leash is None:
        _qnft_leash = QNFTLeash()
    return _qnft_leash
