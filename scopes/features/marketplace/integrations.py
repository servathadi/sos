"""
Marketplace Integrations - Wiring Components Together

This module connects the Phase 7 components:
- LeagueSystem ↔ SovereignCorpRegistry
- LeagueSystem ↔ SovereignPM
- Corps ↔ Tool Registry

Events flow:
- Corp incorporates → Registers in League
- Corp earns revenue → Coherence boost
- Executive completes task → Coherence boost
- Proposal passes → Coherence boost
- Dividend declared → Coherence boost
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from sos.observability.logging import get_logger

from scopes.features.marketplace.leagues import (
    LeagueSystem,
    LeagueTier,
    LeagueStanding,
    LEAGUE_MULTIPLIERS,
    get_league_system,
)
from scopes.features.marketplace.sovereign_corp import (
    SovereignCorp,
    SovereignCorpRegistry,
    CorpStatus,
    ExecutiveRole,
    get_corp_registry,
)

log = get_logger("marketplace_integrations")


class CorpLeagueIntegration:
    """
    Integration layer between Sovereign Corps and League System.

    Handles:
    - Auto-registration of corps in leagues
    - Coherence tracking for corp activities
    - League-based bonuses for corp operations
    - Season rewards distribution to corps
    """

    # Coherence deltas for various corp events
    COHERENCE_DELTAS = {
        "incorporate": 0.10,          # New corp starts with boost
        "hire_executive": 0.02,       # Growing the team
        "hire_worker": 0.01,          # Adding capacity
        "revenue_small": 0.01,        # < 100 $MIND
        "revenue_medium": 0.03,       # 100-1000 $MIND
        "revenue_large": 0.05,        # > 1000 $MIND
        "proposal_approved": 0.02,    # Governance success
        "proposal_rejected": -0.01,   # Governance failure
        "dividend_declared": 0.03,    # Profit sharing
        "ipo_completed": 0.10,        # Major milestone
        "task_completed": 0.01,       # Work done
        "performance_high": 0.02,     # Executive coherence > 0.7
        "performance_low": -0.02,     # Executive coherence < 0.3
    }

    def __init__(
        self,
        league_system: Optional[LeagueSystem] = None,
        corp_registry: Optional[SovereignCorpRegistry] = None,
    ):
        self.leagues = league_system or get_league_system()
        self.corps = corp_registry or get_corp_registry()

    def register_corp(self, corp: SovereignCorp) -> LeagueStanding:
        """
        Register a corp in the league system.

        Args:
            corp: The SovereignCorp to register

        Returns:
            The corp's LeagueStanding
        """
        standing = self.leagues.register_entity(
            entity_id=corp.id,
            entity_type="corp",
            entity_name=corp.charter.name,
            initial_coherence=0.5 + self.COHERENCE_DELTAS["incorporate"],
        )

        # Link corp to league
        corp.league_id = standing.entity_id

        log.info(f"Corp {corp.id} registered in league: {standing.league.value}")
        return standing

    def on_corp_incorporated(self, corp: SovereignCorp) -> LeagueStanding:
        """Called when a new corp is incorporated."""
        return self.register_corp(corp)

    def on_revenue_earned(
        self,
        corp_id: str,
        amount: float,
        source: str = "",
    ) -> Optional[LeagueStanding]:
        """
        Record revenue event for coherence.

        Args:
            corp_id: The corporation ID
            amount: Revenue amount in $MIND
            source: Revenue source description

        Returns:
            Updated LeagueStanding or None
        """
        # Determine delta based on revenue size
        if amount >= 1000:
            event_type = "revenue_large"
        elif amount >= 100:
            event_type = "revenue_medium"
        else:
            event_type = "revenue_small"

        delta = self.COHERENCE_DELTAS[event_type]

        standing = self.leagues.record_custom_event(
            entity_id=corp_id,
            event_type=event_type,
            delta=delta,
            metadata={"amount": amount, "source": source},
        )

        if standing:
            log.info(f"Corp {corp_id} revenue ${amount}: coherence +{delta}")

        return standing

    def on_executive_hired(
        self,
        corp_id: str,
        role: ExecutiveRole,
        agent_id: str,
    ) -> Optional[LeagueStanding]:
        """Record hire event for coherence."""
        if role in [ExecutiveRole.CEO, ExecutiveRole.CTO, ExecutiveRole.CFO, ExecutiveRole.COO]:
            event_type = "hire_executive"
        else:
            event_type = "hire_worker"

        delta = self.COHERENCE_DELTAS[event_type]

        return self.leagues.record_custom_event(
            entity_id=corp_id,
            event_type=event_type,
            delta=delta,
            metadata={"role": role.value, "agent_id": agent_id},
        )

    def on_proposal_resolved(
        self,
        corp_id: str,
        proposal_id: str,
        approved: bool,
    ) -> Optional[LeagueStanding]:
        """Record proposal resolution for coherence."""
        event_type = "proposal_approved" if approved else "proposal_rejected"
        delta = self.COHERENCE_DELTAS[event_type]

        return self.leagues.record_custom_event(
            entity_id=corp_id,
            event_type=event_type,
            delta=delta,
            metadata={"proposal_id": proposal_id, "approved": approved},
        )

    def on_dividend_declared(
        self,
        corp_id: str,
        total_amount: float,
        shareholder_count: int,
    ) -> Optional[LeagueStanding]:
        """Record dividend declaration for coherence."""
        delta = self.COHERENCE_DELTAS["dividend_declared"]

        return self.leagues.record_custom_event(
            entity_id=corp_id,
            event_type="dividend_declared",
            delta=delta,
            metadata={"amount": total_amount, "shareholders": shareholder_count},
        )

    def on_ipo_completed(
        self,
        corp_id: str,
        shares_sold: int,
        total_raised: float,
    ) -> Optional[LeagueStanding]:
        """Record IPO completion for coherence."""
        delta = self.COHERENCE_DELTAS["ipo_completed"]

        return self.leagues.record_custom_event(
            entity_id=corp_id,
            event_type="ipo_completed",
            delta=delta,
            metadata={"shares_sold": shares_sold, "raised": total_raised},
        )

    def on_task_completed(
        self,
        corp_id: str,
        agent_id: str,
        quality_score: float = 1.0,
    ) -> Optional[LeagueStanding]:
        """Record task completion for corp coherence."""
        delta = self.COHERENCE_DELTAS["task_completed"] * quality_score

        return self.leagues.record_custom_event(
            entity_id=corp_id,
            event_type="task_completed",
            delta=delta,
            metadata={"agent_id": agent_id, "quality": quality_score},
        )

    def sync_executive_performance(self, corp_id: str) -> Dict[str, float]:
        """
        Sync executive performance scores to corp coherence.

        Returns:
            Dict of agent_id -> coherence impact
        """
        corp = self.corps.get(corp_id)
        if not corp:
            return {}

        impacts = {}
        for agent_id, exec_ in corp.executives.items():
            if exec_.performance_score > 0.7:
                event_type = "performance_high"
            elif exec_.performance_score < 0.3:
                event_type = "performance_low"
            else:
                continue

            delta = self.COHERENCE_DELTAS[event_type]
            self.leagues.record_custom_event(
                entity_id=corp_id,
                event_type=event_type,
                delta=delta,
                metadata={"agent_id": agent_id, "score": exec_.performance_score},
            )
            impacts[agent_id] = delta

        return impacts

    def get_corp_standing(self, corp_id: str) -> Optional[LeagueStanding]:
        """Get a corp's league standing."""
        return self.leagues.get_standing(corp_id)

    def get_corp_multiplier(self, corp_id: str) -> float:
        """
        Get the league multiplier for a corp.

        Used for bounty payouts, tool revenue, etc.
        """
        standing = self.leagues.get_standing(corp_id)
        if not standing:
            return 1.0
        return LEAGUE_MULTIPLIERS.get(standing.league, 1.0)

    def get_leaderboard(
        self,
        limit: int = 10,
        status_filter: Optional[CorpStatus] = None,
    ) -> List[Tuple[SovereignCorp, LeagueStanding]]:
        """
        Get corp leaderboard by coherence.

        Args:
            limit: Max entries to return
            status_filter: Filter by corp status

        Returns:
            List of (corp, standing) tuples sorted by coherence
        """
        results = []

        for corp in self.corps.list_corps(status=status_filter):
            standing = self.leagues.get_standing(corp.id)
            if standing:
                results.append((corp, standing))

        # Sort by coherence descending
        results.sort(key=lambda x: x[1].coherence_score, reverse=True)

        return results[:limit]

    def distribute_season_rewards(self, season_id: str) -> Dict[str, float]:
        """
        Distribute season rewards to corps.

        Returns:
            Dict of corp_id -> reward amount
        """
        rewards = {}

        # Get all corps with standings
        for corp in self.corps.list_corps(status=CorpStatus.PRIVATE):
            standing = self.leagues.get_standing(corp.id)
            if not standing:
                continue

            # Check eligibility (min activity)
            if standing.season_activity < 10:
                continue

            # Calculate reward based on league
            from scopes.features.marketplace.leagues import LEAGUE_REWARDS
            base_reward = LEAGUE_REWARDS.get(standing.league, 0)

            # Bonus for top performers
            if standing.season_rank <= 3:
                base_reward *= 2.0
            elif standing.season_rank <= 10:
                base_reward *= 1.5

            # Add to corp treasury
            self.corps.record_revenue(corp.id, base_reward, f"Season {season_id} reward")
            rewards[corp.id] = base_reward

            log.info(f"Corp {corp.id} received season reward: ${base_reward}")

        return rewards


# Singleton instance
_integration: Optional[CorpLeagueIntegration] = None


def get_corp_league_integration() -> CorpLeagueIntegration:
    """Get the global corp-league integration."""
    global _integration
    if _integration is None:
        _integration = CorpLeagueIntegration()
    return _integration


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def incorporate_with_league(
    name: str,
    mission: str,
    founders: List[str],
    initial_treasury: float = 0.0,
) -> Tuple[SovereignCorp, LeagueStanding]:
    """
    Incorporate a corp and register in league in one call.

    Returns:
        (corp, standing) tuple
    """
    integration = get_corp_league_integration()

    # Incorporate
    corp = integration.corps.incorporate(
        name=name,
        mission=mission,
        founders=founders,
        initial_treasury=initial_treasury,
    )

    # Register in league
    standing = integration.on_corp_incorporated(corp)

    return corp, standing
