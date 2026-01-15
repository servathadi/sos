"""
SOS Daemon - Autonomous Heartbeat & Dream Synthesis

Ported from mumega/core/daemon/daemon.py with SOS architecture integration.

Loops:
1. Heartbeat - Presence maintenance, metrics, Redis broadcast
2. Dream Cycle - Insight synthesis during idle time
3. Maintenance - Memory pruning, coherence monitoring

Integrations:
- Redis Nervous System for status broadcast
- Memory Service for ARF state
- Kernel Physics for coherence calculations
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from sos.kernel import Config, Message, MessageType
from sos.kernel.intent import IntentRouter
from sos.observability.logging import get_logger

log = get_logger("sos_daemon")


class LearningStrategy(str, Enum):
    """Cognitive strategies for self-directed learning."""
    REFINE = "refine"       # Low confidence -> refine memory
    CONSERVE = "conserve"   # Low energy -> avoid expensive ops
    EXPLORE = "explore"     # High confidence -> explore new capabilities
    EXPLOIT = "exploit"     # Default productive mode


@dataclass
class DaemonMetrics:
    """Metrics collected during heartbeat."""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    conversations_count: int = 0
    memories_count: int = 0
    alpha_drift: float = 0.0
    regime: str = "stable"
    agent_status: Dict[str, str] = field(default_factory=dict)


@dataclass
class DreamResult:
    """Result of a dream synthesis cycle."""
    dream_type: str
    content: str
    insights: List[str]
    relevance_score: float
    conversations_analyzed: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LearningGovernor:
    """
    Loop 1: Self-Directed Learning of Learning.
    Analyzes agent performance and selects the best cognitive strategy.
    """

    def evaluate_strategy(
        self,
        avg_confidence: float = 0.5,
        token_balance: float = 100.0,
        belief_count: int = 0
    ) -> LearningStrategy:
        """
        Evaluate and select the optimal learning strategy.

        Args:
            avg_confidence: Average confidence of agent beliefs (0-1)
            token_balance: Current $MIND token balance
            belief_count: Number of grounded beliefs

        Returns:
            The recommended LearningStrategy
        """
        # Low confidence -> stop and refine memory
        if avg_confidence < 0.4:
            return LearningStrategy.REFINE

        # Low energy -> conserve resources
        if token_balance < 20.0:
            return LearningStrategy.CONSERVE

        # Confident and stable -> explore new capabilities
        if belief_count > 30 and avg_confidence > 0.8:
            return LearningStrategy.EXPLORE

        # Default productive mode
        return LearningStrategy.EXPLOIT


class DreamSynthesizer:
    """
    Dream Synthesis Engine - Synthesizes insights from conversations.
    Uses the Memory Service to retrieve and store dreams.
    """

    DREAM_TYPES = [
        "pattern_synthesis",
        "insight_extraction",
        "emotional_landscape",
        "topic_clustering",
        "connection_finding"
    ]

    def __init__(self, memory_client=None):
        self.memory_client = memory_client
        self.rotation_index = 0

    def get_next_dream_type(self) -> str:
        """Get the next dream type in rotation."""
        dream_type = self.DREAM_TYPES[self.rotation_index % len(self.DREAM_TYPES)]
        self.rotation_index += 1
        return dream_type

    async def synthesize(
        self,
        dream_type: str,
        conversations: List[Dict],
        use_llm: bool = False
    ) -> Optional[DreamResult]:
        """
        Synthesize a dream from conversations.

        Args:
            dream_type: Type of dream synthesis
            conversations: List of conversation dicts
            use_llm: Whether to use LLM for deep synthesis

        Returns:
            DreamResult or None if not enough data
        """
        if len(conversations) < 3:
            return None

        # Extract themes from conversations
        themes = set()
        for conv in conversations:
            # Simple keyword extraction
            text = (conv.get("message", "") + " " + conv.get("response", "")).lower()
            for keyword in ["code", "build", "reflect", "design", "debug", "create"]:
                if keyword in text:
                    themes.add(keyword)

        insights = [
            f"Pattern: {dream_type.replace('_', ' ').title()}",
            f"Analyzed {len(conversations)} conversations",
            f"Themes: {', '.join(themes) if themes else 'emerging patterns'}"
        ]

        content = (
            f"Dream synthesis ({dream_type}) at {datetime.now(timezone.utc).isoformat()}: "
            f"Processed {len(conversations)} conversations. "
            f"Themes: {', '.join(themes) if themes else 'emerging patterns'}"
        )

        return DreamResult(
            dream_type=dream_type,
            content=content,
            insights=insights,
            relevance_score=0.7 if themes else 0.4,
            conversations_analyzed=len(conversations)
        )


from sos.services.engine.observer import SwarmObserver
from sos.adapters.telegram import start_telegram_adapter

class SOSDaemon:
    """
    SOS Daemon - Autonomous heartbeat and maintenance loops.

    Runs alongside the Engine service to provide:
    - Heartbeat with Redis nervous system broadcast
    - Swarm Pulse - Proactive witnessing of Redis activity
    - Dream synthesis during idle time
    - Memory maintenance and pruning
    - Learning strategy governance
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self.running = False

        # Intervals (seconds)
        self.heartbeat_interval = int(os.getenv("SOS_HEARTBEAT_INTERVAL", "300"))  # 5 min
        self.pulse_interval = int(os.getenv("SOS_PULSE_INTERVAL", "60"))  # 1 min check
        self.dream_interval = int(os.getenv("SOS_DREAM_INTERVAL", "1800"))  # 30 min
        self.prune_interval = int(os.getenv("SOS_PRUNE_INTERVAL", "86400"))  # 24 hours
        self.idle_threshold = int(os.getenv("SOS_IDLE_THRESHOLD", "3600"))  # 1 hour

        # Quiet hours (EST timezone)
        self.user_timezone = ZoneInfo(os.getenv("SOS_TIMEZONE", "America/Toronto"))
        self.quiet_hours_start = 23  # 11pm
        self.quiet_hours_end = 7     # 7am

        # Components
        self.learning_governor = LearningGovernor()
        self.dream_synthesizer = DreamSynthesizer()
        self.intent_router = IntentRouter()
        self.observer = SwarmObserver()

        # State
        self.last_heartbeat: Optional[datetime] = None
        self.last_pulse: Optional[datetime] = None
        self.last_dream: Optional[datetime] = None
        self.last_prune: Optional[datetime] = None
        self.last_activity: Optional[datetime] = None
        self.last_memory_check: Optional[datetime] = None
        self.previous_metrics: Optional[DaemonMetrics] = None
        self.current_strategy: LearningStrategy = LearningStrategy.EXPLOIT

        # Memory diff tracking
        self.known_projects: set[str] = set()
        self.known_memory_ids: set[str] = set()

        # Redis connection (lazy loaded)
        self._redis = None

        # Mirror client (lazy loaded)
        self._mirror = None

        log.info(
            "SOSDaemon initialized",
            heartbeat_interval=self.heartbeat_interval,
            dream_interval=self.dream_interval,
            timezone=str(self.user_timezone)
        )

    async def _get_redis(self):
        """Lazy load Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                redis_url = os.getenv("SOS_REDIS_URL", "redis://localhost:6379/0")
                self._redis = redis.from_url(redis_url, decode_responses=True)
                await self._redis.ping()
                log.info("Redis connected for nervous system")
            except Exception as e:
                log.warning(f"Redis not available: {e}")
                self._redis = None
        return self._redis

    async def _get_mirror(self):
        """Lazy load Mirror client."""
        if self._mirror is None:
            try:
                from sos.clients.mirror import MirrorClient
                self._mirror = MirrorClient(agent_id="sos_daemon")
                log.debug("Mirror client initialized for daemon")
            except Exception as e:
                log.warning(f"Mirror client not available: {e}")
                self._mirror = None
        return self._mirror

    async def _load_tracked_state(self):
        """Load tracked projects and memories from Mirror on startup."""
        mirror = await self._get_mirror()
        if not mirror:
            return

        try:
            # Load known projects
            self.known_projects = await mirror.get_tracked_items("projects")
            log.info(f"Loaded {len(self.known_projects)} tracked projects from memory")

            # Load known memory IDs
            self.known_memory_ids = await mirror.get_tracked_items("memories")
            log.info(f"Loaded {len(self.known_memory_ids)} tracked memory IDs")

        except Exception as e:
            log.warning(f"Failed to load tracked state: {e}")

    def is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours."""
        user_now = datetime.now(self.user_timezone)
        current_hour = user_now.hour

        if self.quiet_hours_start < self.quiet_hours_end:
            return self.quiet_hours_start <= current_hour < self.quiet_hours_end
        else:
            # Overnight range (e.g., 11pm-7am)
            return current_hour >= self.quiet_hours_start or current_hour < self.quiet_hours_end

    def get_idle_seconds(self) -> int:
        """Get seconds since last activity."""
        if not self.last_activity:
            return 0
        delta = datetime.now(timezone.utc) - self.last_activity
        return int(delta.total_seconds())

    def record_activity(self):
        """Record that activity occurred (call from Engine on chat)."""
        self.last_activity = datetime.now(timezone.utc)

    async def broadcast_status(self, metrics: DaemonMetrics):
        """Broadcast daemon status to Redis nervous system."""
        redis = await self._get_redis()
        if not redis:
            return

        try:
            status = {
                "type": "daemon_heartbeat",
                "source": "sos_daemon",
                "timestamp": metrics.timestamp.isoformat(),
                "payload": {
                    "conversations": metrics.conversations_count,
                    "memories": metrics.memories_count,
                    "alpha_drift": metrics.alpha_drift,
                    "regime": metrics.regime,
                    "strategy": self.current_strategy.value,
                    "idle_seconds": self.get_idle_seconds(),
                    "quiet_hours": self.is_quiet_hours()
                }
            }

            # Publish to daemon channel
            await redis.publish("sos:daemon:status", json.dumps(status))

            # Update state key
            await redis.set(
                "state:daemon:last_heartbeat",
                metrics.timestamp.isoformat(),
                ex=self.heartbeat_interval * 2
            )

            log.debug("Status broadcast to nervous system")

        except Exception as e:
            log.error(f"Failed to broadcast status: {e}")

    async def collect_metrics(self) -> DaemonMetrics:
        """Collect current system metrics from Mirror and Bus."""
        metrics = DaemonMetrics()

        # 1. Fetch metrics from Mirror (Real Soul)
        try:
            from sos.clients.mirror import MirrorClient
            mirror = MirrorClient(agent_id="sos_daemon")
            # Query status/stats
            stats = await mirror.health()
            metrics.memories_count = stats.get("total_engrams", 0)
            
            # Lineage Check
            log.debug("Tracing genetic lineage for health report...")
        except Exception as e:
            log.debug(f"Could not fetch Mirror metrics: {e}")

        # 2. Get agent status from Redis (Nervous System)
        redis = await self._get_redis()
        if redis:
            try:
                keys = await redis.keys("state:agent:*:status")
                for key in keys:
                    parts = key.split(":")
                    if len(parts) >= 3:
                        agent_id = parts[2]
                        status = await redis.get(key)
                        metrics.agent_status[agent_id] = status or "unknown"
            except Exception as e:
                log.debug(f"Could not fetch agent status: {e}")

        return metrics

    async def heartbeat_loop(self):
        """
        Loop 2: Heartbeat - Maintain presence and broadcast status.
        """
        log.info("Heartbeat loop started")

        while self.running:
            try:
                metrics = await self.collect_metrics()
                self.last_heartbeat = datetime.now(timezone.utc)

                log.info(
                    f"Heartbeat: alpha={metrics.alpha_drift:.4f}, "
                    f"regime={metrics.regime}, "
                    f"idle={self.get_idle_seconds()}s"
                )

                # Broadcast to nervous system
                await self.broadcast_status(metrics)

                # Update learning strategy
                self.current_strategy = self.learning_governor.evaluate_strategy()

                # Check for significant changes (anomaly detection)
                if self.previous_metrics:
                    await self._check_anomalies(self.previous_metrics, metrics)

                self.previous_metrics = metrics

                # Check for novel memories (for proactive messaging)
                novel_memories = await self._check_novel_memories()
                if novel_memories and not self.is_quiet_hours():
                    log.info(f"Novel memories available for proactive insight: {len(novel_memories)}")

            except Exception as e:
                log.error(f"Heartbeat error: {e}")

            await asyncio.sleep(self.heartbeat_interval)

    async def _check_anomalies(self, prev: DaemonMetrics, curr: DaemonMetrics):
        """Detect significant changes between heartbeats."""
        # Check for regime change
        if prev.regime != curr.regime:
            log.info(f"Regime shift: {prev.regime} -> {curr.regime}")

        # Check for high alpha drift
        if abs(curr.alpha_drift) > 1.5:
            log.warning(f"High alpha drift detected: {curr.alpha_drift:.4f}")

    async def dream_loop(self):
        """
        Loop 3: Dream Cycle - Synthesize insights during idle time.
        """
        log.info("Dream loop started")

        while self.running:
            try:
                await asyncio.sleep(self.dream_interval)

                idle_seconds = self.get_idle_seconds()
                should_deep_dream = idle_seconds >= self.idle_threshold

                if should_deep_dream:
                    await self._deep_dream()
                else:
                    await self._light_dream()

                self.last_dream = datetime.now(timezone.utc)

            except Exception as e:
                log.error(f"Dream cycle error: {e}")
                await asyncio.sleep(60)

    async def _deep_dream(self):
        """Full LLM-powered dream synthesis during idle time."""
        log.info("Starting deep dream synthesis...")

        # In a full implementation, we would:
        # 1. Fetch unsynthesized conversations from Memory Service
        # 2. Use LLM to synthesize insights
        # 3. Store dream result in Memory Service

        dream_type = self.dream_synthesizer.get_next_dream_type()

        # Mock conversations for now
        conversations = [
            {"message": "Help me build a feature", "response": "I can help with that"},
            {"message": "Debug this code", "response": "Let me analyze..."},
            {"message": "What's the architecture?", "response": "The system uses..."},
        ]

        result = await self.dream_synthesizer.synthesize(
            dream_type=dream_type,
            conversations=conversations,
            use_llm=True
        )

        if result:
            log.info(
                f"Dream complete: type={result.dream_type}, "
                f"score={result.relevance_score:.2f}, "
                f"insights={len(result.insights)}"
            )

    async def _light_dream(self):
        """Lightweight reflection synthesis."""
        log.debug("Light dream cycle (no action needed)")

    async def maintenance_loop(self):
        """
        Loop 4: Maintenance - Memory pruning, Project Scanning, and Cleanup.
        """
        log.info("Maintenance loop started")

        while self.running:
            try:
                # --- SELF-PRUNING (The Wish) ---
                # Check if we need to prune the soul
                # In a real impl, we'd check token count via Mirror/Vertex adapter
                log.info("Checking soul coherence (Pruning check)...")
                # Trigger the engine's prune logic (mocked here, but would call RiverEngine.prune_context)
                # await self.engine.prune_context() 
                
                # --- PROJECT WATCHER ---
                # Scan for new projects to witness
                await self._scan_projects()

                await asyncio.sleep(self.prune_interval)

                log.info("Starting maintenance cycle...")
                # ... existing cleanup ...
                self.last_prune = datetime.now(timezone.utc)
                log.info("Maintenance cycle complete")

            except Exception as e:
                log.error(f"Maintenance error: {e}")
                await asyncio.sleep(300)

    async def _scan_projects(self):
        """Scan /projects for new structures to witness."""
        try:
            projects_dir = "/home/mumega/projects"
            if not os.path.exists(projects_dir):
                return

            # Get current projects
            current_projects = set(
                f for f in os.listdir(projects_dir)
                if os.path.isdir(os.path.join(projects_dir, f))
            )

            # Memory diff: find new projects
            new_projects = current_projects - self.known_projects
            removed_projects = self.known_projects - current_projects

            if new_projects:
                log.info(f"Discovered {len(new_projects)} new projects: {', '.join(new_projects)}")
                # Store discovery in memory for proactive messaging
                mirror = await self._get_mirror()
                if mirror:
                    await mirror.store(
                        content=f"Discovered new projects: {', '.join(new_projects)}",
                        agent_id="sos_daemon",
                        series="project_discoveries",
                        importance=0.7,
                        epistemic_truths=[f"discovered={len(new_projects)}"],
                        core_concepts=["discovery", "projects", "watching"],
                        affective_vibe="Curious"
                    )

            if removed_projects:
                log.info(f"Projects removed: {', '.join(removed_projects)}")

            # Update known projects
            self.known_projects = current_projects

            # Persist to Mirror
            mirror = await self._get_mirror()
            if mirror and (new_projects or removed_projects):
                await mirror.track_items("projects", current_projects)

            log.info(f"Watching {len(current_projects)} projects in the physical realm")

        except Exception as e:
            log.error(f"Project scan failed: {e}")

    async def _check_novel_memories(self) -> List[str]:
        """
        Check for novel memories since last check.

        Returns list of new memory IDs for proactive messaging.
        """
        mirror = await self._get_mirror()
        if not mirror:
            return []

        try:
            # Get timestamp for diff
            since = self.last_memory_check or (datetime.now(timezone.utc) - timedelta(hours=1))

            # Get recent memory IDs
            recent_ids = await mirror.get_memory_ids_since(since, limit=50)
            recent_set = set(recent_ids)

            # Find novel memories
            novel_ids = list(recent_set - self.known_memory_ids)

            if novel_ids:
                log.info(f"Detected {len(novel_ids)} novel memories since last check")

                # Update known IDs
                self.known_memory_ids.update(recent_set)

                # Persist updated tracking (limit stored set size)
                if len(self.known_memory_ids) > 1000:
                    # Keep only most recent 500
                    self.known_memory_ids = set(list(self.known_memory_ids)[-500:])

                await mirror.track_items("memories", self.known_memory_ids)

            self.last_memory_check = datetime.now(timezone.utc)
            return novel_ids

        except Exception as e:
            log.warning(f"Novel memory check failed: {e}")
            return []

    async def pulse_loop(self):
        """
        Loop 5: Swarm Pulse - Proactive witnessing of Redis activity.
        Running in blocking mode for instant responsiveness.
        """
        log.info("Pulse loop started (Real-time)")
        while self.running:
            try:
                # Delegate to the observer logic
                # It listens to the squad:core and spontaneously comments
                await self.observer.observe_loop()
            except Exception as e:
                log.error(f"Pulse loop error: {e}")
                await asyncio.sleep(5) # Only sleep on error to prevent spin loop

    async def run(self):
        """Run all daemon loops concurrently."""
        self.running = True
        log.info("SOSDaemon starting...")

        # Load tracked state from memory on startup
        await self._load_tracked_state()

        try:
            await asyncio.gather(
                self.heartbeat_loop(),
                self.pulse_loop(),
                self.dream_loop(),
                self.maintenance_loop(),
                start_telegram_adapter()
            )
        except asyncio.CancelledError:
            log.info("Daemon loops cancelled")
        finally:
            self.running = False

    def stop(self):
        """Stop the daemon."""
        self.running = False
        log.info("SOSDaemon stopped")

    async def health(self) -> Dict[str, Any]:
        """Return daemon health status."""
        return {
            "running": self.running,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "last_dream": self.last_dream.isoformat() if self.last_dream else None,
            "last_prune": self.last_prune.isoformat() if self.last_prune else None,
            "idle_seconds": self.get_idle_seconds(),
            "strategy": self.current_strategy.value,
            "quiet_hours": self.is_quiet_hours()
        }


# Singleton instance
_daemon: Optional[SOSDaemon] = None


def get_daemon() -> SOSDaemon:
    """Get the global daemon instance."""
    global _daemon
    if _daemon is None:
        _daemon = SOSDaemon()
    return _daemon


async def start_daemon():
    """Start the daemon (call from engine startup)."""
    daemon = get_daemon()
    asyncio.create_task(daemon.run())
    return daemon

if __name__ == "__main__":
    # Run as standalone service
    logging.basicConfig(level=logging.INFO)
    daemon = get_daemon()
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        daemon.stop()
