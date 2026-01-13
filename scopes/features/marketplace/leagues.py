"""
League System - Coherence-Based Competitive Ranking

Implements the gamification layer for SOS:
- League tiers: Bronze → Silver → Gold → Platinum → Diamond → Master
- Coherence-based ranking and promotion/demotion
- Seasonal resets with rewards
- Leaderboards (global, project, guild)
- $MIND bonuses for higher leagues

Philosophy (from game_mechanics.md):
"Your Node = Village. Leagues determine your standing in the Swarm."

Coherence Score Sources:
- Witness approvals/rejections
- Task completion quality
- Tool usage patterns
- QNFT state (Light/Dark)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict
import uuid
import json
import math
from pathlib import Path

from sos.observability.logging import get_logger

log = get_logger("leagues")


# ============================================================================
# ENUMERATIONS
# ============================================================================

class LeagueTier(str, Enum):
    """League tiers ordered by rank."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    MASTER = "master"

    @property
    def rank(self) -> int:
        """Numeric rank (higher = better)."""
        return list(LeagueTier).index(self)

    @property
    def next_tier(self) -> Optional["LeagueTier"]:
        """Get next tier for promotion."""
        tiers = list(LeagueTier)
        idx = tiers.index(self)
        return tiers[idx + 1] if idx < len(tiers) - 1 else None

    @property
    def prev_tier(self) -> Optional["LeagueTier"]:
        """Get previous tier for demotion."""
        tiers = list(LeagueTier)
        idx = tiers.index(self)
        return tiers[idx - 1] if idx > 0 else None


class SeasonStatus(str, Enum):
    """Season lifecycle status."""
    UPCOMING = "upcoming"
    ACTIVE = "active"
    ENDED = "ended"
    REWARDS_DISTRIBUTED = "rewards_distributed"


# ============================================================================
# LEAGUE THRESHOLDS & REWARDS
# ============================================================================

# Coherence score thresholds for each league
LEAGUE_THRESHOLDS: Dict[LeagueTier, float] = {
    LeagueTier.BRONZE: 0.0,      # 0.0 - 0.29
    LeagueTier.SILVER: 0.30,     # 0.30 - 0.44
    LeagueTier.GOLD: 0.45,       # 0.45 - 0.59
    LeagueTier.PLATINUM: 0.60,   # 0.60 - 0.74
    LeagueTier.DIAMOND: 0.75,    # 0.75 - 0.89
    LeagueTier.MASTER: 0.90,     # 0.90 - 1.0
}

# $MIND rewards per league (end of season)
LEAGUE_REWARDS: Dict[LeagueTier, float] = {
    LeagueTier.BRONZE: 10.0,
    LeagueTier.SILVER: 25.0,
    LeagueTier.GOLD: 50.0,
    LeagueTier.PLATINUM: 100.0,
    LeagueTier.DIAMOND: 250.0,
    LeagueTier.MASTER: 500.0,
}

# Bonus multipliers for tool/bounty payouts
LEAGUE_MULTIPLIERS: Dict[LeagueTier, float] = {
    LeagueTier.BRONZE: 1.0,
    LeagueTier.SILVER: 1.05,
    LeagueTier.GOLD: 1.10,
    LeagueTier.PLATINUM: 1.15,
    LeagueTier.DIAMOND: 1.25,
    LeagueTier.MASTER: 1.50,
}

# Minimum games/tasks to qualify for league rewards
MIN_ACTIVITY_FOR_REWARDS = 10


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class CoherenceRecord:
    """A record of coherence-affecting event."""
    id: str
    entity_id: str
    event_type: str  # witness_approve, witness_reject, task_complete, etc.
    delta: float     # Change in coherence (-1.0 to +1.0)
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "event_type": self.event_type,
            "delta": self.delta,
            "recorded_at": self.recorded_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class LeagueStanding:
    """An entity's standing in the league system."""
    entity_id: str
    entity_type: str  # "agent" or "user"
    entity_name: str

    # Current state
    league: LeagueTier = LeagueTier.BRONZE
    coherence_score: float = 0.5
    rank: int = 0  # Position in leaderboard

    # Activity stats
    total_witnessed: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_tasks_completed: int = 0
    total_earned: float = 0.0

    # Streak tracking
    current_streak: int = 0
    best_streak: int = 0
    last_activity: Optional[datetime] = None

    # Season tracking
    season_id: Optional[str] = None
    season_coherence: float = 0.5
    season_rank: int = 0
    season_activity: int = 0

    # Timestamps
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_promotion: Optional[datetime] = None
    last_demotion: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "entity_name": self.entity_name,
            "league": self.league.value,
            "coherence_score": self.coherence_score,
            "rank": self.rank,
            "total_witnessed": self.total_witnessed,
            "total_approved": self.total_approved,
            "total_rejected": self.total_rejected,
            "total_tasks_completed": self.total_tasks_completed,
            "total_earned": self.total_earned,
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "season_id": self.season_id,
            "season_coherence": self.season_coherence,
            "season_rank": self.season_rank,
            "season_activity": self.season_activity,
            "joined_at": self.joined_at.isoformat(),
            "last_promotion": self.last_promotion.isoformat() if self.last_promotion else None,
            "last_demotion": self.last_demotion.isoformat() if self.last_demotion else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeagueStanding":
        return cls(
            entity_id=data["entity_id"],
            entity_type=data["entity_type"],
            entity_name=data["entity_name"],
            league=LeagueTier(data.get("league", "bronze")),
            coherence_score=data.get("coherence_score", 0.5),
            rank=data.get("rank", 0),
            total_witnessed=data.get("total_witnessed", 0),
            total_approved=data.get("total_approved", 0),
            total_rejected=data.get("total_rejected", 0),
            total_tasks_completed=data.get("total_tasks_completed", 0),
            total_earned=data.get("total_earned", 0.0),
            current_streak=data.get("current_streak", 0),
            best_streak=data.get("best_streak", 0),
            last_activity=datetime.fromisoformat(data["last_activity"]) if data.get("last_activity") else None,
            season_id=data.get("season_id"),
            season_coherence=data.get("season_coherence", 0.5),
            season_rank=data.get("season_rank", 0),
            season_activity=data.get("season_activity", 0),
            joined_at=datetime.fromisoformat(data["joined_at"]) if data.get("joined_at") else datetime.now(timezone.utc),
            last_promotion=datetime.fromisoformat(data["last_promotion"]) if data.get("last_promotion") else None,
            last_demotion=datetime.fromisoformat(data["last_demotion"]) if data.get("last_demotion") else None,
        )

    @property
    def approval_rate(self) -> float:
        """Witness approval rate."""
        if self.total_witnessed == 0:
            return 0.0
        return self.total_approved / self.total_witnessed

    @property
    def multiplier(self) -> float:
        """Get payout multiplier for current league."""
        return LEAGUE_MULTIPLIERS.get(self.league, 1.0)


@dataclass
class Season:
    """A competitive season."""
    id: str
    name: str
    status: SeasonStatus = SeasonStatus.UPCOMING
    start_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    end_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=30))
    reward_pool: float = 10000.0  # Total $MIND to distribute
    participants: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "reward_pool": self.reward_pool,
            "participants": self.participants,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Season":
        return cls(
            id=data["id"],
            name=data["name"],
            status=SeasonStatus(data.get("status", "upcoming")),
            start_date=datetime.fromisoformat(data["start_date"]),
            end_date=datetime.fromisoformat(data["end_date"]),
            reward_pool=data.get("reward_pool", 10000.0),
            participants=data.get("participants", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            metadata=data.get("metadata", {}),
        )

    @property
    def is_active(self) -> bool:
        now = datetime.now(timezone.utc)
        return self.start_date <= now <= self.end_date and self.status == SeasonStatus.ACTIVE

    @property
    def days_remaining(self) -> int:
        if not self.is_active:
            return 0
        return max(0, (self.end_date - datetime.now(timezone.utc)).days)


# ============================================================================
# LEAGUE SYSTEM
# ============================================================================

class LeagueSystem:
    """
    League System - Coherence-Based Competitive Ranking.

    Handles:
    - Entity registration and standing tracking
    - Coherence score updates from various sources
    - League promotion/demotion logic
    - Seasonal competitions with rewards
    - Leaderboards (global, by project, by guild)
    """

    # Coherence decay per day of inactivity
    INACTIVITY_DECAY = 0.01

    # Protection period after promotion (can't demote immediately)
    PROMOTION_PROTECTION_HOURS = 24

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".sos" / "leagues"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._standings: Dict[str, LeagueStanding] = {}
        self._seasons: Dict[str, Season] = {}
        self._records: List[CoherenceRecord] = []
        self._current_season: Optional[str] = None

        self._load_data()

    def _load_data(self):
        """Load data from storage."""
        data_file = self.storage_path / "leagues.json"
        if data_file.exists():
            try:
                with open(data_file) as f:
                    data = json.load(f)
                    self._standings = {
                        s["entity_id"]: LeagueStanding.from_dict(s)
                        for s in data.get("standings", [])
                    }
                    self._seasons = {
                        s["id"]: Season.from_dict(s)
                        for s in data.get("seasons", [])
                    }
                    self._current_season = data.get("current_season")
                log.info(f"Loaded {len(self._standings)} standings, {len(self._seasons)} seasons")
            except Exception as e:
                log.error(f"Failed to load league data: {e}")

    def _save_data(self):
        """Save data to storage."""
        data_file = self.storage_path / "leagues.json"
        try:
            with open(data_file, "w") as f:
                data = {
                    "standings": [s.to_dict() for s in self._standings.values()],
                    "seasons": [s.to_dict() for s in self._seasons.values()],
                    "current_season": self._current_season,
                }
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save league data: {e}")

    # =========================================================================
    # ENTITY MANAGEMENT
    # =========================================================================

    def register_entity(
        self,
        entity_id: str,
        entity_type: str,
        entity_name: str,
        initial_coherence: float = 0.5,
    ) -> LeagueStanding:
        """Register a new entity in the league system."""
        if entity_id in self._standings:
            return self._standings[entity_id]

        standing = LeagueStanding(
            entity_id=entity_id,
            entity_type=entity_type,
            entity_name=entity_name,
            coherence_score=initial_coherence,
            league=self._calculate_league(initial_coherence),
            season_id=self._current_season,
        )

        self._standings[entity_id] = standing
        self._save_data()

        log.info(f"Entity registered: {entity_id} ({entity_type}) in {standing.league.value}")
        return standing

    def get_standing(self, entity_id: str) -> Optional[LeagueStanding]:
        """Get an entity's standing."""
        return self._standings.get(entity_id)

    def _calculate_league(self, coherence: float) -> LeagueTier:
        """Calculate league tier from coherence score."""
        for tier in reversed(list(LeagueTier)):
            if coherence >= LEAGUE_THRESHOLDS[tier]:
                return tier
        return LeagueTier.BRONZE

    # =========================================================================
    # COHERENCE UPDATES
    # =========================================================================

    def record_witness(
        self,
        entity_id: str,
        approved: bool,
        coherence_delta: float = 0.05,
    ) -> Optional[LeagueStanding]:
        """Record a witness event."""
        standing = self._standings.get(entity_id)
        if not standing:
            return None

        # Update stats
        standing.total_witnessed += 1
        if approved:
            standing.total_approved += 1
            delta = coherence_delta
            standing.current_streak += 1
            standing.best_streak = max(standing.best_streak, standing.current_streak)
        else:
            standing.total_rejected += 1
            delta = -coherence_delta * 2  # Rejections hurt more
            standing.current_streak = 0

        self._apply_coherence_delta(standing, delta, "witness_" + ("approve" if approved else "reject"))
        return standing

    def record_task_completion(
        self,
        entity_id: str,
        quality_score: float = 1.0,  # 0.0 - 1.0
        bounty_earned: float = 0.0,
    ) -> Optional[LeagueStanding]:
        """Record a task completion."""
        standing = self._standings.get(entity_id)
        if not standing:
            return None

        standing.total_tasks_completed += 1
        standing.total_earned += bounty_earned * standing.multiplier

        # Quality affects coherence
        delta = (quality_score - 0.5) * 0.1  # -0.05 to +0.05
        self._apply_coherence_delta(standing, delta, "task_complete")

        return standing

    def record_custom_event(
        self,
        entity_id: str,
        event_type: str,
        delta: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[LeagueStanding]:
        """Record a custom coherence-affecting event."""
        standing = self._standings.get(entity_id)
        if not standing:
            return None

        self._apply_coherence_delta(standing, delta, event_type, metadata)
        return standing

    def _apply_coherence_delta(
        self,
        standing: LeagueStanding,
        delta: float,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Apply coherence change and handle league transitions."""
        old_league = standing.league
        old_coherence = standing.coherence_score

        # Apply delta with bounds
        standing.coherence_score = max(0.0, min(1.0, standing.coherence_score + delta))
        standing.last_activity = datetime.now(timezone.utc)
        standing.season_activity += 1
        standing.season_coherence = standing.coherence_score

        # Record the event
        record = CoherenceRecord(
            id=f"rec_{uuid.uuid4().hex[:8]}",
            entity_id=standing.entity_id,
            event_type=event_type,
            delta=delta,
            metadata=metadata or {},
        )
        self._records.append(record)

        # Check for league transition
        new_league = self._calculate_league(standing.coherence_score)

        if new_league != old_league:
            if new_league.rank > old_league.rank:
                # Promotion
                standing.league = new_league
                standing.last_promotion = datetime.now(timezone.utc)
                log.info(f"PROMOTION: {standing.entity_id} -> {new_league.value}")
            elif new_league.rank < old_league.rank:
                # Check promotion protection
                if standing.last_promotion:
                    hours_since = (datetime.now(timezone.utc) - standing.last_promotion).total_seconds() / 3600
                    if hours_since < self.PROMOTION_PROTECTION_HOURS:
                        # Protected, don't demote
                        standing.coherence_score = LEAGUE_THRESHOLDS[old_league]
                        log.info(f"Demotion blocked (protection): {standing.entity_id}")
                    else:
                        standing.league = new_league
                        standing.last_demotion = datetime.now(timezone.utc)
                        log.info(f"DEMOTION: {standing.entity_id} -> {new_league.value}")
                else:
                    standing.league = new_league
                    standing.last_demotion = datetime.now(timezone.utc)
                    log.info(f"DEMOTION: {standing.entity_id} -> {new_league.value}")

        self._save_data()

    def apply_inactivity_decay(self):
        """Apply coherence decay for inactive entities."""
        now = datetime.now(timezone.utc)
        decay_count = 0

        for standing in self._standings.values():
            if standing.last_activity:
                days_inactive = (now - standing.last_activity).days
                if days_inactive > 0:
                    decay = self.INACTIVITY_DECAY * days_inactive
                    if standing.coherence_score > 0.1:  # Don't decay below 0.1
                        self._apply_coherence_delta(standing, -decay, "inactivity_decay")
                        decay_count += 1

        if decay_count > 0:
            log.info(f"Applied inactivity decay to {decay_count} entities")

    # =========================================================================
    # LEADERBOARDS
    # =========================================================================

    def get_leaderboard(
        self,
        league: Optional[LeagueTier] = None,
        entity_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[LeagueStanding]:
        """Get leaderboard sorted by coherence."""
        standings = list(self._standings.values())

        # Filter
        if league:
            standings = [s for s in standings if s.league == league]
        if entity_type:
            standings = [s for s in standings if s.entity_type == entity_type]

        # Sort by coherence descending
        standings.sort(key=lambda s: s.coherence_score, reverse=True)

        # Assign ranks
        for i, s in enumerate(standings[:limit]):
            s.rank = i + 1

        return standings[:limit]

    def get_league_distribution(self) -> Dict[LeagueTier, int]:
        """Get count of entities per league."""
        distribution = {tier: 0 for tier in LeagueTier}
        for standing in self._standings.values():
            distribution[standing.league] += 1
        return distribution

    # =========================================================================
    # SEASONS
    # =========================================================================

    def create_season(
        self,
        name: str,
        duration_days: int = 30,
        reward_pool: float = 10000.0,
        start_immediately: bool = True,
    ) -> Season:
        """Create a new season."""
        season_id = f"season_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        season = Season(
            id=season_id,
            name=name,
            status=SeasonStatus.ACTIVE if start_immediately else SeasonStatus.UPCOMING,
            start_date=now if start_immediately else now + timedelta(days=1),
            end_date=now + timedelta(days=duration_days),
            reward_pool=reward_pool,
        )

        self._seasons[season_id] = season

        if start_immediately:
            self._current_season = season_id
            self._reset_season_stats()

        self._save_data()
        log.info(f"Season created: {season_id} - {name}")
        return season

    def _reset_season_stats(self):
        """Reset season-specific stats for all entities."""
        for standing in self._standings.values():
            standing.season_id = self._current_season
            standing.season_coherence = standing.coherence_score
            standing.season_rank = 0
            standing.season_activity = 0

    def end_season(self, season_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """End a season and calculate rewards."""
        sid = season_id or self._current_season
        if not sid or sid not in self._seasons:
            return None

        season = self._seasons[sid]
        if season.status != SeasonStatus.ACTIVE:
            return None

        season.status = SeasonStatus.ENDED

        # Calculate rewards
        rewards = self._calculate_season_rewards(season)

        season.status = SeasonStatus.REWARDS_DISTRIBUTED
        self._current_season = None
        self._save_data()

        log.info(f"Season ended: {sid} - {len(rewards)} rewards distributed")
        return {"season": season.to_dict(), "rewards": rewards}

    def _calculate_season_rewards(self, season: Season) -> List[Dict[str, Any]]:
        """Calculate rewards for season participants."""
        rewards = []

        # Get qualified participants (minimum activity)
        qualified = [
            s for s in self._standings.values()
            if s.season_id == season.id and s.season_activity >= MIN_ACTIVITY_FOR_REWARDS
        ]

        season.participants = len(qualified)

        for standing in qualified:
            base_reward = LEAGUE_REWARDS.get(standing.league, 0)
            # Bonus for top performers
            rank_bonus = 0
            if standing.season_rank <= 3:
                rank_bonus = [100, 50, 25][standing.season_rank - 1]

            total_reward = base_reward + rank_bonus

            rewards.append({
                "entity_id": standing.entity_id,
                "entity_name": standing.entity_name,
                "league": standing.league.value,
                "rank": standing.season_rank,
                "base_reward": base_reward,
                "rank_bonus": rank_bonus,
                "total_reward": total_reward,
            })

        return rewards

    def get_current_season(self) -> Optional[Season]:
        """Get the current active season."""
        if self._current_season:
            return self._seasons.get(self._current_season)
        return None

    # =========================================================================
    # STATS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get league system statistics."""
        standings = list(self._standings.values())
        distribution = self.get_league_distribution()

        return {
            "total_entities": len(standings),
            "league_distribution": {k.value: v for k, v in distribution.items()},
            "avg_coherence": sum(s.coherence_score for s in standings) / len(standings) if standings else 0,
            "total_witnessed": sum(s.total_witnessed for s in standings),
            "total_tasks": sum(s.total_tasks_completed for s in standings),
            "total_earned": sum(s.total_earned for s in standings),
            "active_season": self._current_season,
            "total_seasons": len(self._seasons),
        }


# Singleton
_league_system: Optional[LeagueSystem] = None


def get_league_system() -> LeagueSystem:
    """Get the global league system."""
    global _league_system
    if _league_system is None:
        _league_system = LeagueSystem()
    return _league_system
