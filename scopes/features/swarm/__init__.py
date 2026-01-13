"""
Swarm Scope - Fleet Management, Task Orchestration, and Hive Workers

This scope handles the distributed task system for SOS.

Components:
- Daemon: Heartbeat, Dreams, Maintenance loops
- SwarmDispatcher: Task sharding and dispatch
- SovereignTaskManager: Auto-spawn tasks from chat
- WorkerRegistry: Persistent workers with reputation
- AsyncHiveBridge: Lightweight parallel inference

Worker Patterns:
1. AsyncHiveBridge - Transient swarms for parallel inference
2. WorkerRegistry - Persistent workers with reputation tiers

Worker Lifecycle:
    REGISTER → CLAIM → EXECUTE → REPORT

Reputation Tiers:
    NOVICE → APPRENTICE → JOURNEYMAN → EXPERT → MASTER

Map-Reduce Pattern:
    inputs → map_template → parallel workers → reduce_prompt → synthesized output

See scopes/features/README.md for philosophy.
"""

# Re-export for convenience
from sos.services.engine.daemon import (
    SOSDaemon,
    LearningGovernor,
    DreamSynthesizer,
    LearningStrategy,
    get_daemon,
    start_daemon,
)
from sos.services.engine.swarm import SwarmDispatcher, get_swarm
from sos.services.engine.task_manager import SovereignTaskManager

from scopes.features.swarm.workers import (
    WorkerRegistry,
    WorkerProfile,
    WorkerTier,
    WorkerStatus,
    AsyncHiveBridge,
    HiveJob,
    HiveResult,
    get_worker_registry,
    get_hive_bridge,
)

__all__ = [
    # Daemon
    "SOSDaemon",
    "LearningGovernor",
    "DreamSynthesizer",
    "LearningStrategy",
    "get_daemon",
    "start_daemon",
    # Swarm
    "SwarmDispatcher",
    "get_swarm",
    "SovereignTaskManager",
    # Workers
    "WorkerRegistry",
    "WorkerProfile",
    "WorkerTier",
    "WorkerStatus",
    "AsyncHiveBridge",
    "HiveJob",
    "HiveResult",
    "get_worker_registry",
    "get_hive_bridge",
]
