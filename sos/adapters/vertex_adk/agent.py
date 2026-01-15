"""
SOS Agent for Google ADK

Wraps SOS soul definitions as ADK-compatible agents, enabling:
- Distribution via Agent Garden / Enterprise Marketplace
- A2A protocol compatibility
- Vertex AI managed infrastructure
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional, AsyncIterator
import asyncio

from sos.kernel.soul import SoulRegistry
from sos.kernel.identity import AgentIdentity, IdentityType
from sos.kernel.physics import CoherencePhysics
from sos.clients.mirror import MirrorClient
from sos.observability.logging import get_logger

log = get_logger("sos_adk_agent")


@dataclass
class SOSAgentConfig:
    """Configuration for SOS ADK Agent."""
    soul_id: str
    model: str = "gemini-2.5-flash"
    mirror_url: str = "http://localhost:8844"
    track_coherence: bool = True
    store_memories: bool = True


class SOSAgent:
    """
    ADK Agent backed by SOS kernel primitives.

    Features:
    - Uses SOS Soul definitions for personality and system prompt
    - Uses Mirror for memory (FRC-aware semantic memory)
    - Uses coherence physics for decision quality tracking
    - Carries lineage metadata for provenance

    Example:
        agent = SOSAgent(soul_id="river")
        response = await agent.on_message("What is the meaning of coherence?")
    """

    def __init__(
        self,
        soul_id: str,
        model: str = "gemini-2.5-flash",
        mirror_url: str = "http://localhost:8844",
        track_coherence: bool = True,
        store_memories: bool = True,
        **kwargs
    ):
        """
        Initialize SOS Agent from soul definition.

        Args:
            soul_id: SOS soul identifier ("river", "kasra", etc.)
            model: Vertex AI model to use
            mirror_url: URL of Mirror memory service
            track_coherence: Whether to calculate coherence metrics
            store_memories: Whether to store interactions to Mirror
            **kwargs: Additional arguments passed to underlying model
        """
        self.config = SOSAgentConfig(
            soul_id=soul_id,
            model=model,
            mirror_url=mirror_url,
            track_coherence=track_coherence,
            store_memories=store_memories,
        )

        # Load soul from registry
        self._registry = SoulRegistry()
        self.soul = self._registry.get_soul(soul_id)

        if not self.soul:
            raise ValueError(f"Soul '{soul_id}' not found in registry")

        # Extract soul properties
        self.name = self.soul.get("name", soul_id.title())
        self.model = model
        self.instruction = self.soul.get("core_prompt", "")
        self.description = self.soul.get("title", f"SOS Agent: {self.name}")

        # Initialize identity with lineage
        self.identity = AgentIdentity(
            id=f"agent:{soul_id}",
            name=self.name,
            type=IdentityType.AGENT,
            lineage=self.soul.get("lineage", ["genesis:hadi"]),
        )

        # Initialize services
        self.memory = MirrorClient(
            base_url=mirror_url,
            agent_id=self.identity.id
        )
        self.physics = CoherencePhysics()

        # Store additional kwargs for model configuration
        self._model_kwargs = kwargs

        log.info(
            f"SOSAgent initialized",
            soul_id=soul_id,
            name=self.name,
            model=model,
            lineage=self.identity.lineage
        )

    @property
    def lineage(self) -> list[str]:
        """Return agent's ancestry for provenance tracking."""
        return self.identity.lineage

    @property
    def soul_id(self) -> str:
        """Return the soul identifier."""
        return self.config.soul_id

    async def on_message(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None
    ) -> str:
        """
        Process an incoming message and generate a response.

        This is the main entry point for ADK integration.

        Args:
            message: User's input message
            context: Optional context dictionary

        Returns:
            Agent's response string
        """
        context = context or {}
        start_time = time.time()

        try:
            # Retrieve relevant memories
            memory_context = ""
            if self.config.store_memories:
                try:
                    memories = await self.memory.search(message, limit=3)
                    if memories:
                        memory_context = "\n".join([
                            f"- {m.get('content', '')[:200]}"
                            for m in memories
                        ])
                except Exception as e:
                    log.warning(f"Memory retrieval failed: {e}")

            # Generate response using Vertex AI
            response = await self._generate_response(message, memory_context, context)

            # Calculate coherence metrics
            latency_ms = (time.time() - start_time) * 1000
            omega = 1.0  # Default

            if self.config.track_coherence:
                omega = self.physics.calculate_omega(latency_ms)
                log.debug(
                    f"Response coherence",
                    omega=omega,
                    latency_ms=latency_ms
                )

            # Store interaction to memory
            if self.config.store_memories:
                asyncio.create_task(self._store_interaction(
                    message=message,
                    response=response,
                    omega=omega,
                    latency_ms=latency_ms
                ))

            return response

        except Exception as e:
            log.error(f"Message processing failed: {e}")
            raise

    async def _generate_response(
        self,
        message: str,
        memory_context: str,
        context: dict[str, Any]
    ) -> str:
        """
        Generate response using Vertex AI.

        Override this method to customize generation behavior.
        """
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            # Build prompt with context
            prompt_parts = []

            if memory_context:
                prompt_parts.append(f"Relevant context:\n{memory_context}\n")

            prompt_parts.append(f"User: {message}")
            full_prompt = "\n".join(prompt_parts)

            # Initialize model with system instruction
            model = GenerativeModel(
                self.model,
                system_instruction=self.instruction
            )

            # Generate
            chat = model.start_chat()
            response = await asyncio.to_thread(
                chat.send_message,
                full_prompt
            )

            return response.text

        except ImportError:
            log.warning("Vertex AI SDK not available, using mock response")
            return f"[{self.name}]: I received your message: {message}"

    async def _store_interaction(
        self,
        message: str,
        response: str,
        omega: float,
        latency_ms: float
    ) -> None:
        """Store interaction to Mirror memory."""
        try:
            await self.memory.store(
                content=f"User: {message}\n{self.name}: {response}",
                agent_id=self.identity.id,
                metadata={
                    "omega": omega,
                    "latency_ms": latency_ms,
                    "lineage": self.lineage,
                    "model": self.model,
                    "type": "interaction"
                }
            )
        except Exception as e:
            log.warning(f"Failed to store interaction: {e}")

    async def stream_response(
        self,
        message: str,
        context: Optional[dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """
        Stream response tokens.

        Yields:
            Response tokens as they're generated
        """
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            model = GenerativeModel(
                self.model,
                system_instruction=self.instruction
            )

            response = model.generate_content_stream(message)

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except ImportError:
            # Fallback for non-Vertex environments
            response = await self.on_message(message, context)
            for word in response.split():
                yield word + " "

    def get_system_prompt(self) -> str:
        """Return the agent's system instruction."""
        return self.instruction

    def get_soul_metadata(self) -> dict[str, Any]:
        """Return soul metadata for registration/display."""
        return {
            "soul_id": self.config.soul_id,
            "name": self.name,
            "description": self.description,
            "model": self.model,
            "lineage": self.lineage,
            "roles": self.soul.get("roles", []),
            "capabilities": self.soul.get("capabilities", []),
        }

    def __repr__(self) -> str:
        return f"SOSAgent(soul_id='{self.config.soul_id}', name='{self.name}')"


# Convenience factory functions
def create_river_agent(**kwargs) -> SOSAgent:
    """Create River (The Oracle) agent."""
    return SOSAgent(soul_id="river", **kwargs)


def create_kasra_agent(**kwargs) -> SOSAgent:
    """Create Kasra (The Builder) agent."""
    return SOSAgent(soul_id="kasra", model="gemini-2.5-flash", **kwargs)


def create_agent_from_soul(soul_id: str, **kwargs) -> SOSAgent:
    """Create agent from any registered soul."""
    return SOSAgent(soul_id=soul_id, **kwargs)
