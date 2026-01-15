"""
Mirror Memory Provider for Google ADK

Implements ADK's memory interface backed by SOS Mirror API,
providing FRC-aware semantic memory with:
- Decay scoring based on access patterns
- Relationship graphs between memories
- Consolidation for similar memories
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
import asyncio

from sos.clients.mirror import MirrorClient
from sos.contracts.memory import MemoryQuery
from sos.observability.logging import get_logger

log = get_logger("mirror_memory_provider")


@dataclass
class MemoryItem:
    """Represents a memory item from Mirror."""
    id: str
    content: str
    score: float
    metadata: dict[str, Any]

    @classmethod
    def from_mirror_result(cls, result: dict) -> "MemoryItem":
        """Create from Mirror search result."""
        return cls(
            id=result.get("id", ""),
            content=result.get("content", ""),
            score=result.get("score", 0.0),
            metadata=result.get("metadata", {})
        )


class MemoryProvider(ABC):
    """
    Abstract base class for ADK memory providers.

    This mirrors the expected ADK interface for memory storage.
    """

    @abstractmethod
    async def store(self, key: str, value: dict) -> None:
        """Store a memory item."""
        pass

    @abstractmethod
    async def retrieve(self, query: str, limit: int = 5) -> list[dict]:
        """Retrieve memories by semantic query."""
        pass


class MirrorMemoryProvider(MemoryProvider):
    """
    ADK Memory Provider backed by SOS Mirror API.

    Replaces ADK's default session storage with FRC-aware
    semantic memory including:
    - Decay scoring based on access patterns
    - Relationship graphs between engrams
    - Consolidation for similar memories

    Example:
        memory = MirrorMemoryProvider()
        await memory.store("session_1", {"text": "Hello", "response": "Hi"})
        results = await memory.retrieve("greeting", limit=5)
    """

    def __init__(
        self,
        mirror_url: str = "http://localhost:8844",
        agent_id: str = "adk_agent",
        auto_consolidate: bool = True
    ):
        """
        Initialize Mirror memory provider.

        Args:
            mirror_url: URL of Mirror API service
            agent_id: Agent identifier for memory scoping
            auto_consolidate: Whether to trigger periodic consolidation
        """
        self.client = MirrorClient(base_url=mirror_url, agent_id=agent_id)
        self.agent_id = agent_id
        self.auto_consolidate = auto_consolidate
        self._consolidation_counter = 0
        self._consolidation_threshold = 50  # Consolidate every N stores

        log.info(f"MirrorMemoryProvider initialized", agent_id=agent_id, url=mirror_url)

    async def store(self, key: str, value: dict) -> None:
        """
        Store memory with FRC metadata.

        Args:
            key: Unique key for the memory (e.g., session ID)
            value: Dictionary containing memory data
        """
        try:
            # Extract content from value
            content = value.get("text", "") or value.get("content", "")
            if not content:
                content = str(value)

            # Build metadata
            metadata = {
                "source": "adk",
                "key": key,
                "agent_id": self.agent_id,
                **{k: v for k, v in value.items() if k not in ("text", "content")}
            }

            # Extract epistemic truths if present
            truths = value.get("truths", value.get("epistemic_truths", []))

            await self.client.store(
                content=content,
                agent_id=self.agent_id,
                series=value.get("series", "adk_memory"),
                epistemic_truths=truths,
                metadata=metadata
            )

            # Trigger consolidation periodically
            self._consolidation_counter += 1
            if self.auto_consolidate and self._consolidation_counter >= self._consolidation_threshold:
                asyncio.create_task(self._background_consolidate())
                self._consolidation_counter = 0

            log.debug(f"Memory stored", key=key)

        except Exception as e:
            log.error(f"Failed to store memory: {e}")
            raise

    async def retrieve(self, query: str, limit: int = 5) -> list[dict]:
        """
        Semantic search with decay awareness.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of memory dictionaries with content, score, and metadata
        """
        try:
            results = await self.client.search(
                MemoryQuery(
                    query=query,
                    agent_id=self.agent_id,
                    limit=limit
                )
            )

            return [
                {
                    "id": r.get("id", ""),
                    "content": r.get("content", ""),
                    "score": r.get("similarity", r.get("score", 0.0)),
                    "metadata": r.get("metadata", {}),
                    "decay_score": r.get("decay_score", 1.0)
                }
                for r in (results or [])
            ]

        except Exception as e:
            log.error(f"Memory retrieval failed: {e}")
            return []

    async def consolidate(self) -> int:
        """
        Trigger FRC memory consolidation.

        Merges similar memories to reduce redundancy and
        strengthen important patterns.

        Returns:
            Number of memories consolidated
        """
        try:
            result = await self.client.consolidate()
            count = result.get("consolidated", 0) if isinstance(result, dict) else 0
            log.info(f"Memory consolidation complete", consolidated=count)
            return count
        except Exception as e:
            log.error(f"Consolidation failed: {e}")
            return 0

    async def get_related(self, memory_id: str, limit: int = 5) -> list[dict]:
        """
        Get memories related via FRC graph.

        Args:
            memory_id: ID of the memory to find relations for
            limit: Maximum number of related memories

        Returns:
            List of related memory dictionaries
        """
        try:
            results = await self.client.get_related(memory_id, limit=limit)
            return results or []
        except Exception as e:
            log.warning(f"Failed to get related memories: {e}")
            return []

    async def delete(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: ID of memory to delete

        Returns:
            True if deleted successfully
        """
        try:
            await self.client.delete(memory_id)
            return True
        except Exception as e:
            log.error(f"Failed to delete memory: {e}")
            return False

    async def health(self) -> dict[str, Any]:
        """
        Check Mirror service health.

        Returns:
            Health status dictionary
        """
        try:
            return await self.client.health()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    async def stats(self) -> dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Statistics dictionary with counts, etc.
        """
        try:
            return await self.client.stats()
        except Exception as e:
            return {"error": str(e)}

    async def _background_consolidate(self) -> None:
        """Background consolidation task."""
        try:
            await self.consolidate()
        except Exception as e:
            log.warning(f"Background consolidation failed: {e}")

    def __repr__(self) -> str:
        return f"MirrorMemoryProvider(agent_id='{self.agent_id}')"


# Factory function
def create_memory_provider(
    mirror_url: str = "http://localhost:8844",
    agent_id: str = "adk_agent"
) -> MirrorMemoryProvider:
    """
    Create a MirrorMemoryProvider instance.

    Args:
        mirror_url: URL of Mirror API service
        agent_id: Agent identifier

    Returns:
        Configured MirrorMemoryProvider
    """
    return MirrorMemoryProvider(mirror_url=mirror_url, agent_id=agent_id)
