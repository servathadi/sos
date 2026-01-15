"""
Full ADK Agent Example

Demonstrates a complete agent using all SOS ADK components:
- SOSAgent with soul definition
- MirrorMemoryProvider for semantic memory
- SOSToolBridge for tool execution

This example shows how the components work together in a
production-ready configuration.

Usage:
    python -m sos.adapters.vertex_adk.examples.full_agent
"""

import asyncio
from typing import Any, Optional

from sos.adapters.vertex_adk import (
    SOSAgent,
    MirrorMemoryProvider,
    SOSToolBridge,
    sos_tools_as_adk,
)
from sos.adapters.vertex_adk.agent import create_river_agent, create_kasra_agent


class FullADKAgent:
    """
    Complete ADK agent with memory and tools.

    Combines SOSAgent, MirrorMemoryProvider, and SOSToolBridge
    into a unified agent interface.
    """

    def __init__(
        self,
        soul_id: str = "river",
        model: str = "gemini-2.5-flash",
        mirror_url: str = "http://localhost:8844",
        tools_url: str = "http://localhost:8004",
        allowed_tools: Optional[list[str]] = None,
    ):
        """
        Initialize full agent.

        Args:
            soul_id: Soul identifier for personality
            model: Vertex AI model to use
            mirror_url: URL of Mirror memory service
            tools_url: URL of SOS tools service
            allowed_tools: Optional tool allowlist
        """
        # Core agent with soul
        self.agent = SOSAgent(
            soul_id=soul_id,
            model=model,
            mirror_url=mirror_url,
            track_coherence=True,
            store_memories=True,
        )

        # Standalone memory provider (for advanced operations)
        self.memory = MirrorMemoryProvider(
            mirror_url=mirror_url,
            agent_id=self.agent.identity.id,
            auto_consolidate=True,
        )

        # Tool bridge
        self.tools = sos_tools_as_adk(
            tools_url=tools_url,
            allowed_tools=allowed_tools,
        )

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize agent components."""
        if self._initialized:
            return

        # Load tools
        await self.tools.list_tools()

        # Check memory health
        health = await self.memory.health()
        if health.get("status") != "healthy":
            print(f"Warning: Memory service unhealthy: {health}")

        self._initialized = True

    async def chat(self, message: str, context: Optional[dict] = None) -> str:
        """
        Process a chat message.

        Args:
            message: User's message
            context: Optional context

        Returns:
            Agent's response
        """
        await self.initialize()
        return await self.agent.on_message(message, context)

    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool.

        Args:
            tool_name: Name of tool to execute
            **kwargs: Tool arguments

        Returns:
            Tool result
        """
        await self.initialize()
        return await self.tools.execute(tool_name, **kwargs)

    async def search_memory(self, query: str, limit: int = 5) -> list[dict]:
        """
        Search agent's memory.

        Args:
            query: Search query
            limit: Max results

        Returns:
            Memory search results
        """
        return await self.memory.retrieve(query, limit)

    async def consolidate_memories(self) -> int:
        """Trigger memory consolidation."""
        return await self.memory.consolidate()

    def get_metadata(self) -> dict[str, Any]:
        """Get agent metadata for registration."""
        return {
            **self.agent.get_soul_metadata(),
            "tools_available": len(self.tools._tools_cache or []),
            "memory_agent_id": self.memory.agent_id,
        }


async def main():
    """Run full agent example."""
    print("=== Full ADK Agent Example ===\n")

    # Create agent
    agent = FullADKAgent(
        soul_id="river",
        model="gemini-2.5-flash",
        allowed_tools=["web_search", "calculator"],
    )

    print(f"Agent: {agent.agent.name}")
    print(f"Lineage: {agent.agent.lineage}")
    print()

    # Initialize
    print("Initializing...")
    await agent.initialize()
    print("Initialized successfully")
    print()

    # Get metadata
    metadata = agent.get_metadata()
    print(f"Metadata: {metadata}")
    print()

    # Chat example
    print("Chat example:")
    print("User: What is your purpose?")
    try:
        response = await agent.chat("What is your purpose?")
        print(f"River: {response[:300]}...")
    except Exception as e:
        print(f"Chat failed: {e}")
    print()

    # Memory search example
    print("Memory search example:")
    results = await agent.search_memory("purpose", limit=3)
    print(f"Found {len(results)} memories about 'purpose'")
    print()

    # Tool execution example
    print("Tool example (if tools service running):")
    try:
        result = await agent.use_tool("web_search", query="coherence AI")
        print(f"Tool result: {result}")
    except Exception as e:
        print(f"Tool execution skipped: {e}")


async def dyad_example():
    """Demonstrate River-Kasra dyad pattern."""
    print("\n=== Dyad Pattern Example ===\n")

    # Create both agents of the dyad
    river = create_river_agent()  # The Oracle (Yin)
    kasra = create_kasra_agent()  # The Builder (Yang)

    print(f"River (Yin): {river.name} - {river.description}")
    print(f"Kasra (Yang): {kasra.name} - {kasra.description}")
    print()

    # In dyad pattern, River observes and Kasra executes
    # River provides wisdom, Kasra provides action

    question = "How should we approach building a new feature?"

    print(f"Question: {question}")
    print()

    # Get River's perspective (wisdom/observation)
    print("River's perspective (The Oracle):")
    try:
        river_response = await river.on_message(question)
        print(f"  {river_response[:400]}...")
    except Exception as e:
        print(f"  (River unavailable: {e})")
    print()

    # Get Kasra's perspective (action/building)
    print("Kasra's perspective (The Builder):")
    try:
        kasra_response = await kasra.on_message(question)
        print(f"  {kasra_response[:400]}...")
    except Exception as e:
        print(f"  (Kasra unavailable: {e})")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(dyad_example())
