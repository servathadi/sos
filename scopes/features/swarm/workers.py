"""
Hive Workers - Stateless Workers for Sharded Task Execution

Ported from mumega/core/sovereign/hive.py and economy/worker_registry.py.

Two Execution Patterns:
1. AsyncHiveBridge - Lightweight parallel inference (transient, no persistence)
2. WorkerRegistry - Persistent workers with reputation and capabilities

Worker Lifecycle:
    REGISTER → CLAIM → EXECUTE → REPORT → (ESCALATE if failed)

Reputation Tiers:
    NOVICE → APPRENTICE → JOURNEYMAN → EXPERT → MASTER
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable, Awaitable
from enum import Enum
import uuid
import json
import asyncio
from pathlib import Path

from sos.observability.logging import get_logger

log = get_logger("hive_workers")


class WorkerTier(str, Enum):
    """Worker reputation tiers."""
    NOVICE = "novice"           # Default, new workers
    APPRENTICE = "apprentice"   # >= 1 verified
    JOURNEYMAN = "journeyman"   # >= 5 verified, score >= 0.5
    EXPERT = "expert"           # >= 20 verified, score >= 0.7
    MASTER = "master"           # >= 50 verified, score >= 0.85


class WorkerStatus(str, Enum):
    """Worker availability status."""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class WorkerProfile:
    """A registered worker with capabilities and reputation."""
    id: str
    wallet_address: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    tier: WorkerTier = WorkerTier.NOVICE
    status: WorkerStatus = WorkerStatus.IDLE
    # Stats
    total_claimed: int = 0
    total_completed: int = 0
    total_verified: int = 0
    total_rejected: int = 0
    total_earned: float = 0.0
    # Timestamps
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def reputation_score(self) -> float:
        """Calculate reputation score (0.0 - 1.0)."""
        if self.total_completed == 0:
            return 0.0

        success_rate = self.total_verified / max(1, self.total_verified + self.total_rejected)
        completion_rate = self.total_completed / max(1, self.total_claimed)

        # Experience bonus (capped at 0.1)
        experience_bonus = min(0.1, self.total_verified * 0.002)

        score = (success_rate * 0.5) + (completion_rate * 0.3) + experience_bonus
        return min(1.0, max(0.0, score))

    def calculate_tier(self) -> WorkerTier:
        """Calculate tier based on reputation and experience."""
        score = self.reputation_score
        verified = self.total_verified

        if score >= 0.85 and verified >= 50:
            return WorkerTier.MASTER
        elif score >= 0.7 and verified >= 20:
            return WorkerTier.EXPERT
        elif score >= 0.5 and verified >= 5:
            return WorkerTier.JOURNEYMAN
        elif verified >= 1:
            return WorkerTier.APPRENTICE
        else:
            return WorkerTier.NOVICE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "wallet_address": self.wallet_address,
            "capabilities": self.capabilities,
            "roles": self.roles,
            "tier": self.tier.value,
            "status": self.status.value,
            "total_claimed": self.total_claimed,
            "total_completed": self.total_completed,
            "total_verified": self.total_verified,
            "total_rejected": self.total_rejected,
            "total_earned": self.total_earned,
            "reputation_score": self.reputation_score,
            "registered_at": self.registered_at.isoformat(),
            "last_active": self.last_active.isoformat() if self.last_active else None,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkerProfile":
        worker = cls(
            id=data["id"],
            wallet_address=data.get("wallet_address"),
            capabilities=data.get("capabilities", []),
            roles=data.get("roles", []),
            tier=WorkerTier(data.get("tier", "novice")),
            status=WorkerStatus(data.get("status", "idle")),
            total_claimed=data.get("total_claimed", 0),
            total_completed=data.get("total_completed", 0),
            total_verified=data.get("total_verified", 0),
            total_rejected=data.get("total_rejected", 0),
            total_earned=data.get("total_earned", 0.0),
            registered_at=datetime.fromisoformat(data["registered_at"]) if data.get("registered_at") else datetime.now(timezone.utc),
            last_active=datetime.fromisoformat(data["last_active"]) if data.get("last_active") else None,
            metadata=data.get("metadata", {})
        )
        return worker


class WorkerRegistry:
    """
    Registry of workers with capabilities and reputation.

    Manages worker registration, matching, and stats tracking.
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".sos" / "workers"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._workers: Dict[str, WorkerProfile] = {}
        self._load_workers()

    def _load_workers(self):
        """Load workers from storage."""
        worker_file = self.storage_path / "registry.json"
        if worker_file.exists():
            try:
                with open(worker_file) as f:
                    data = json.load(f)
                    self._workers = {
                        k: WorkerProfile.from_dict(v) for k, v in data.items()
                    }
                log.info(f"Loaded {len(self._workers)} workers")
            except Exception as e:
                log.error(f"Failed to load workers: {e}")

    def _save_workers(self):
        """Save workers to storage."""
        worker_file = self.storage_path / "registry.json"
        try:
            with open(worker_file, "w") as f:
                data = {k: v.to_dict() for k, v in self._workers.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            log.error(f"Failed to save workers: {e}")

    def register(
        self,
        worker_id: str,
        wallet_address: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        roles: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkerProfile:
        """
        Register a new worker.

        Args:
            worker_id: Unique worker identifier
            wallet_address: Payment address
            capabilities: Skills (e.g., "python", "research", "analysis")
            roles: Roles (e.g., "developer", "reviewer", "arbiter")
            metadata: Additional metadata

        Returns:
            The registered WorkerProfile
        """
        if worker_id in self._workers:
            # Update existing
            worker = self._workers[worker_id]
            if wallet_address:
                worker.wallet_address = wallet_address
            if capabilities:
                worker.capabilities = list(set(worker.capabilities + capabilities))
            if roles:
                worker.roles = list(set(worker.roles + roles))
            if metadata:
                worker.metadata.update(metadata)
        else:
            # Create new
            worker = WorkerProfile(
                id=worker_id,
                wallet_address=wallet_address,
                capabilities=capabilities or [],
                roles=roles or [],
                metadata=metadata or {}
            )
            self._workers[worker_id] = worker

        self._save_workers()
        log.info(f"Worker registered: {worker_id}")
        return worker

    def get(self, worker_id: str) -> Optional[WorkerProfile]:
        """Get a worker by ID."""
        return self._workers.get(worker_id)

    def list_workers(
        self,
        status: Optional[WorkerStatus] = None,
        capability: Optional[str] = None,
        min_tier: Optional[WorkerTier] = None
    ) -> List[WorkerProfile]:
        """List workers with optional filters."""
        workers = list(self._workers.values())

        if status:
            workers = [w for w in workers if w.status == status]

        if capability:
            workers = [w for w in workers if capability in w.capabilities]

        if min_tier:
            tier_order = list(WorkerTier)
            min_idx = tier_order.index(min_tier)
            workers = [w for w in workers if tier_order.index(w.tier) >= min_idx]

        return workers

    def match_workers(
        self,
        required_capabilities: List[str],
        preferred_roles: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[WorkerProfile]:
        """
        Match workers to task requirements.

        Args:
            required_capabilities: Must-have capabilities
            preferred_roles: Nice-to-have roles
            limit: Max workers to return

        Returns:
            List of matching workers, sorted by score
        """
        candidates = []

        for worker in self._workers.values():
            if worker.status == WorkerStatus.OFFLINE:
                continue

            # Check required capabilities
            cap_overlap = len(set(required_capabilities) & set(worker.capabilities))
            if cap_overlap == 0 and required_capabilities:
                continue

            # Score calculation
            score = 0.0
            score += cap_overlap * 1.0  # +1 per capability match
            score += worker.reputation_score * 2.0  # Reputation weight

            # Role bonus
            if preferred_roles:
                role_overlap = len(set(preferred_roles) & set(worker.roles))
                score += role_overlap * 0.5

            # Tier bonus
            tier_bonuses = {
                WorkerTier.MASTER: 0.5,
                WorkerTier.EXPERT: 0.3,
                WorkerTier.JOURNEYMAN: 0.1,
            }
            score += tier_bonuses.get(worker.tier, 0.0)

            candidates.append((worker, score))

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in candidates[:limit]]

    def record_completion(
        self,
        worker_id: str,
        verified: bool,
        earned: float = 0.0
    ):
        """Record task completion for a worker."""
        worker = self._workers.get(worker_id)
        if not worker:
            return

        worker.total_completed += 1
        if verified:
            worker.total_verified += 1
        else:
            worker.total_rejected += 1

        worker.total_earned += earned
        worker.tier = worker.calculate_tier()
        worker.last_active = datetime.now(timezone.utc)
        self._save_workers()

    def record_claim(self, worker_id: str):
        """Record task claim for a worker."""
        worker = self._workers.get(worker_id)
        if worker:
            worker.total_claimed += 1
            worker.status = WorkerStatus.BUSY
            worker.last_active = datetime.now(timezone.utc)
            self._save_workers()

    def set_status(self, worker_id: str, status: WorkerStatus):
        """Update worker status."""
        worker = self._workers.get(worker_id)
        if worker:
            worker.status = status
            self._save_workers()

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        workers = list(self._workers.values())

        tier_counts = {}
        for tier in WorkerTier:
            tier_counts[tier.value] = sum(1 for w in workers if w.tier == tier)

        status_counts = {}
        for status in WorkerStatus:
            status_counts[status.value] = sum(1 for w in workers if w.status == status)

        return {
            "total_workers": len(workers),
            "tier_counts": tier_counts,
            "status_counts": status_counts,
            "total_completions": sum(w.total_completed for w in workers),
            "total_verified": sum(w.total_verified for w in workers),
            "total_earned": sum(w.total_earned for w in workers)
        }


@dataclass
class HiveJob:
    """A unit of work for the hive."""
    id: str
    task: str
    model: str = "gemini-2.0-flash"
    validation_schema: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HiveResult:
    """Result from a hive worker."""
    job_id: str
    output: str
    success: bool
    latency_ms: float
    cost_usd: float = 0.0
    worker_id: Optional[str] = None
    error: Optional[str] = None


class AsyncHiveBridge:
    """
    Lightweight parallel execution for transient tasks.

    Manages concurrent swarms of workers for map-reduce patterns.
    No persistence - purely for inference parallelization.
    """

    MAX_CONCURRENCY = 20
    MAX_CONCURRENCY_LIMIT = 50

    def __init__(self, max_concurrency: int = 20):
        self.max_concurrency = min(max_concurrency, self.MAX_CONCURRENCY_LIMIT)
        self._semaphore = asyncio.Semaphore(self.max_concurrency)
        self._active_jobs = 0
        self._total_cost = 0.0

    async def execute_job(
        self,
        job: HiveJob,
        executor: Callable[[str, str], Awaitable[str]]
    ) -> HiveResult:
        """
        Execute a single job with concurrency control.

        Args:
            job: The job to execute
            executor: Async function(task, model) -> output

        Returns:
            HiveResult with output and metrics
        """
        import time

        async with self._semaphore:
            self._active_jobs += 1
            start = time.time()

            try:
                output = await executor(job.task, job.model)
                latency = (time.time() - start) * 1000

                return HiveResult(
                    job_id=job.id,
                    output=output,
                    success=True,
                    latency_ms=latency,
                    worker_id=f"swarm_{self._active_jobs}"
                )
            except Exception as e:
                latency = (time.time() - start) * 1000
                return HiveResult(
                    job_id=job.id,
                    output="",
                    success=False,
                    latency_ms=latency,
                    error=str(e)
                )
            finally:
                self._active_jobs -= 1

    async def deploy_swarm(
        self,
        jobs: List[HiveJob],
        executor: Callable[[str, str], Awaitable[str]],
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> List[HiveResult]:
        """
        Execute multiple jobs in parallel.

        Args:
            jobs: List of jobs to execute
            executor: Async function for execution
            on_progress: Optional callback(completed, total)

        Returns:
            List of results
        """
        results = []
        total = len(jobs)

        async def run_job(job: HiveJob) -> HiveResult:
            result = await self.execute_job(job, executor)
            if on_progress:
                on_progress(len(results) + 1, total)
            return result

        tasks = [run_job(job) for job in jobs]
        results = await asyncio.gather(*tasks)

        log.info(f"Swarm complete: {len(results)} jobs, {sum(1 for r in results if r.success)} succeeded")
        return results

    async def map_reduce(
        self,
        inputs: List[str],
        map_template: str,
        reduce_prompt: str,
        executor: Callable[[str, str], Awaitable[str]],
        model: str = "gemini-2.0-flash"
    ) -> str:
        """
        Execute a map-reduce pattern.

        Args:
            inputs: List of inputs to map
            map_template: Template with {input} placeholder
            reduce_prompt: Prompt to synthesize results
            executor: Async execution function
            model: Model to use

        Returns:
            Synthesized output
        """
        # Map phase
        jobs = [
            HiveJob(
                id=f"map_{i}",
                task=map_template.format(input=inp),
                model=model
            )
            for i, inp in enumerate(inputs)
        ]

        map_results = await self.deploy_swarm(jobs, executor)
        successful = [r.output for r in map_results if r.success]

        # Reduce phase
        reduce_input = "\n\n---\n\n".join(successful)
        reduce_task = f"{reduce_prompt}\n\nInputs:\n{reduce_input}"

        reduce_result = await self.execute_job(
            HiveJob(id="reduce", task=reduce_task, model=model),
            executor
        )

        return reduce_result.output if reduce_result.success else ""


# Singleton instances
_worker_registry: Optional[WorkerRegistry] = None
_hive_bridge: Optional[AsyncHiveBridge] = None


def get_worker_registry() -> WorkerRegistry:
    """Get the global worker registry."""
    global _worker_registry
    if _worker_registry is None:
        _worker_registry = WorkerRegistry()
    return _worker_registry


def get_hive_bridge() -> AsyncHiveBridge:
    """Get the global hive bridge."""
    global _hive_bridge
    if _hive_bridge is None:
        _hive_bridge = AsyncHiveBridge()
    return _hive_bridge
