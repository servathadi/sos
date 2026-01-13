"""
Marketplace Integrations - Wiring Components Together

This module connects the Phase 7 components:
- LeagueSystem ↔ SovereignCorpRegistry
- LeagueSystem ↔ SovereignPM
- Corps ↔ Tool Registry
- PM ↔ Corps ↔ Leagues (full triangle)

Events flow:
- Corp incorporates → Registers in League
- Corp earns revenue → Coherence boost
- Executive completes task → Coherence boost
- Proposal passes → Coherence boost
- Dividend declared → Coherence boost
- PM task completed → Corp coherence + League update
- PM bounty paid → Corp revenue + League multiplier applied
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone

from sos.observability.logging import get_logger

from scopes.features.marketplace.leagues import (
    LeagueSystem,
    LeagueTier,
    LeagueStanding,
    LEAGUE_MULTIPLIERS,
    LEAGUE_REWARDS,
    get_league_system,
)
from scopes.features.marketplace.sovereign_corp import (
    SovereignCorp,
    SovereignCorpRegistry,
    CorpStatus,
    ExecutiveRole,
    get_corp_registry,
)
from scopes.features.marketplace.tools.sovereign_pm import (
    SovereignPM,
    Task,
    TaskStatus,
    TaskPriority,
    Project,
    Bounty,
    BountyCurrency,
    TaskFilter,
    get_sovereign_pm,
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


# ============================================================================
# PM ↔ CORPS ↔ LEAGUES INTEGRATION
# ============================================================================

class PMCorpLeagueIntegration:
    """
    Integration layer connecting SovereignPM, Corps, and Leagues.

    Handles:
    - Linking projects to corps
    - Task completion → Corp coherence updates
    - Bounty payments with league multipliers
    - Corp revenue tracking from bounties
    - Worker performance tracking
    """

    # Coherence deltas for PM events
    PM_COHERENCE_DELTAS = {
        "task_completed_low": 0.005,      # Low priority task
        "task_completed_medium": 0.01,    # Medium priority
        "task_completed_high": 0.02,      # High priority
        "task_completed_urgent": 0.03,    # Urgent/P0
        "bounty_paid": 0.01,              # Bounty successfully paid
        "task_overdue": -0.01,            # Task missed deadline
        "project_completed": 0.05,        # All tasks in project done
    }

    def __init__(
        self,
        pm: Optional[SovereignPM] = None,
        corps: Optional[SovereignCorpRegistry] = None,
        leagues: Optional[LeagueSystem] = None,
    ):
        self.pm = pm or get_sovereign_pm()
        self.corps = corps or get_corp_registry()
        self.leagues = leagues or get_league_system()

        # Project → Corp mapping
        self._project_corp_map: Dict[str, str] = {}

    def link_project_to_corp(
        self,
        project_id: str,
        corp_id: str,
    ) -> bool:
        """
        Link a PM project to a corp.

        All tasks in this project will affect corp coherence.
        """
        project = self.pm.get_project(project_id)
        corp = self.corps.get(corp_id)

        if not project or not corp:
            return False

        self._project_corp_map[project_id] = corp_id

        # Update project metadata
        project.metadata["corp_id"] = corp_id
        project.owner_id = corp_id

        log.info(f"Project {project_id} linked to corp {corp_id}")
        return True

    def create_corp_project(
        self,
        corp_id: str,
        name: str,
        description: str = "",
    ) -> Optional[Project]:
        """
        Create a project owned by a corp.
        """
        corp = self.corps.get(corp_id)
        if not corp:
            return None

        project = self.pm.create_project(
            name=name,
            description=description,
            owner_id=corp_id,
        )

        if project:
            self._project_corp_map[project.id] = corp_id
            project.metadata["corp_id"] = corp_id

        log.info(f"Created project {project.id} for corp {corp_id}")
        return project

    def get_corp_for_task(self, task: Task) -> Optional[str]:
        """Get the corp ID associated with a task's project."""
        if not task.project_id:
            return None
        return self._project_corp_map.get(task.project_id)

    def on_task_completed(
        self,
        task: Task,
        quality_score: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Handle task completion event.

        Updates:
        - Corp coherence based on priority
        - Assignee's league standing
        - Corp's league standing

        Returns:
            Dict with update results
        """
        result = {
            "task_id": task.id,
            "corp_updated": False,
            "assignee_updated": False,
            "coherence_delta": 0.0,
        }

        corp_id = self.get_corp_for_task(task)

        # Determine coherence delta based on priority
        priority_deltas = {
            TaskPriority.NONE: self.PM_COHERENCE_DELTAS["task_completed_low"],
            TaskPriority.LOW: self.PM_COHERENCE_DELTAS["task_completed_low"],
            TaskPriority.MEDIUM: self.PM_COHERENCE_DELTAS["task_completed_medium"],
            TaskPriority.HIGH: self.PM_COHERENCE_DELTAS["task_completed_high"],
            TaskPriority.URGENT: self.PM_COHERENCE_DELTAS["task_completed_urgent"],
        }
        base_delta = priority_deltas.get(task.priority, 0.01)
        delta = base_delta * quality_score

        result["coherence_delta"] = delta

        # Update corp coherence
        if corp_id:
            standing = self.leagues.record_custom_event(
                entity_id=corp_id,
                event_type="pm_task_completed",
                delta=delta,
                metadata={
                    "task_id": task.id,
                    "priority": task.priority.value,
                    "quality": quality_score,
                },
            )
            if standing:
                result["corp_updated"] = True
                result["corp_coherence"] = standing.coherence_score
                result["corp_league"] = standing.league.value
                log.info(f"Corp {corp_id} task completed: coherence +{delta:.3f}")

        # Update assignee coherence (if registered in leagues)
        if task.assignee_id:
            assignee_standing = self.leagues.record_task_completion(
                entity_id=task.assignee_id,
                quality_score=quality_score,
                bounty_earned=task.bounty.final_amount if task.bounty else 0.0,
            )
            if assignee_standing:
                result["assignee_updated"] = True
                result["assignee_coherence"] = assignee_standing.coherence_score

        return result

    def on_bounty_paid(
        self,
        task: Task,
        tx_id: str,
    ) -> Dict[str, Any]:
        """
        Handle bounty payment event.

        Updates:
        - Corp revenue (bounty amount)
        - Corp coherence
        - Applies league multiplier

        Returns:
            Dict with payment results
        """
        result = {
            "task_id": task.id,
            "paid": False,
            "amount": 0.0,
            "multiplier": 1.0,
            "final_amount": 0.0,
        }

        if not task.bounty:
            return result

        corp_id = self.get_corp_for_task(task)
        bounty = task.bounty

        # Get league multiplier for corp
        multiplier = 1.0
        if corp_id:
            standing = self.leagues.get_standing(corp_id)
            if standing:
                multiplier = LEAGUE_MULTIPLIERS.get(standing.league, 1.0)

        # Apply multiplier to bounty
        original_amount = bounty.amount
        final_amount = original_amount * multiplier * bounty.coherence_multiplier

        result["amount"] = original_amount
        result["multiplier"] = multiplier
        result["final_amount"] = final_amount
        result["paid"] = True

        # Record as corp revenue
        if corp_id:
            self.corps.record_revenue(corp_id, final_amount, f"Bounty: {task.title}")

            # Update corp coherence
            self.leagues.record_custom_event(
                entity_id=corp_id,
                event_type="bounty_paid",
                delta=self.PM_COHERENCE_DELTAS["bounty_paid"],
                metadata={
                    "task_id": task.id,
                    "amount": final_amount,
                    "tx_id": tx_id,
                },
            )

            log.info(f"Corp {corp_id} bounty paid: ${final_amount:.2f} ({multiplier:.2f}x)")

        return result

    def on_task_overdue(self, task: Task) -> Optional[LeagueStanding]:
        """Handle task overdue event (negative coherence)."""
        corp_id = self.get_corp_for_task(task)
        if not corp_id:
            return None

        return self.leagues.record_custom_event(
            entity_id=corp_id,
            event_type="task_overdue",
            delta=self.PM_COHERENCE_DELTAS["task_overdue"],
            metadata={"task_id": task.id, "due_date": task.due_date.isoformat() if task.due_date else None},
        )

    def on_project_completed(self, project_id: str) -> Optional[LeagueStanding]:
        """Handle project completion (all tasks done)."""
        corp_id = self._project_corp_map.get(project_id)
        if not corp_id:
            return None

        return self.leagues.record_custom_event(
            entity_id=corp_id,
            event_type="project_completed",
            delta=self.PM_COHERENCE_DELTAS["project_completed"],
            metadata={"project_id": project_id},
        )

    def get_corp_projects(self, corp_id: str) -> List[Project]:
        """Get all projects owned by a corp."""
        return [
            self.pm.get_project(pid)
            for pid, cid in self._project_corp_map.items()
            if cid == corp_id and self.pm.get_project(pid)
        ]

    def get_corp_tasks(
        self,
        corp_id: str,
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
        """Get all tasks for a corp's projects."""
        tasks = []
        for project_id, cid in self._project_corp_map.items():
            if cid == corp_id:
                task_filter = TaskFilter(project_id=project_id)
                if status:
                    task_filter.status = [status]
                project_tasks = self.pm.list_tasks(filter=task_filter)
                tasks.extend(project_tasks)
        return tasks

    def get_corp_stats(self, corp_id: str) -> Dict[str, Any]:
        """Get PM stats for a corp."""
        tasks = self.get_corp_tasks(corp_id)

        total_bounties = sum(t.bounty.amount for t in tasks if t.bounty)
        paid_bounties = sum(t.bounty.final_amount for t in tasks if t.bounty and t.bounty.paid)

        return {
            "total_projects": len(self.get_corp_projects(corp_id)),
            "total_tasks": len(tasks),
            "completed_tasks": len([t for t in tasks if t.status == TaskStatus.DONE]),
            "in_progress_tasks": len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
            "blocked_tasks": len([t for t in tasks if t.status == TaskStatus.BLOCKED]),
            "total_bounties": total_bounties,
            "paid_bounties": paid_bounties,
            "pending_bounties": total_bounties - paid_bounties,
        }

    def complete_task_with_integration(
        self,
        task_id: str,
        quality_score: float = 1.0,
    ) -> Tuple[Optional[Task], Dict[str, Any]]:
        """
        Complete a task with full integration updates.

        Returns:
            (completed_task, integration_results)
        """
        task = self.pm.complete_task(task_id, quality_score)
        if not task:
            return None, {}

        results = self.on_task_completed(task, quality_score)
        return task, results


# Singleton instance
_pm_integration: Optional[PMCorpLeagueIntegration] = None


def get_pm_corp_league_integration() -> PMCorpLeagueIntegration:
    """Get the global PM-Corp-League integration."""
    global _pm_integration
    if _pm_integration is None:
        _pm_integration = PMCorpLeagueIntegration()
    return _pm_integration
