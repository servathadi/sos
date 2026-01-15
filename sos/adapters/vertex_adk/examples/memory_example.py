"""
Mirror Memory Provider Example

Demonstrates using MirrorMemoryProvider as ADK memory backend
with FRC-aware semantic memory features.

Usage:
    python -m sos.adapters.vertex_adk.examples.memory_example
"""

import asyncio

from sos.adapters.vertex_adk import MirrorMemoryProvider


async def main():
    """Run memory provider example."""
    # Create memory provider
    memory = MirrorMemoryProvider(
        mirror_url="http://localhost:8844",
        agent_id="example_agent",
        auto_consolidate=True,
    )

    print(f"Created memory provider: {memory}")
    print()

    # Check health
    health = await memory.health()
    print(f"Health status: {health}")
    print()

    # Store some memories
    print("Storing memories...")
    await memory.store("session_001", {
        "text": "The user asked about quantum coherence",
        "response": "Quantum coherence in FRC refers to...",
        "truths": ["coherence is fundamental", "entropy flows upward"],
    })

    await memory.store("session_002", {
        "text": "Discussion about agent lineage",
        "response": "Lineage tracks ancestry from genesis...",
        "series": "philosophy",
    })

    await memory.store("session_003", {
        "content": "Memory consolidation example",
        "metadata": {"topic": "memory", "importance": "high"},
    })

    print("Stored 3 memories")
    print()

    # Retrieve memories
    print("Searching for 'coherence'...")
    results = await memory.retrieve("coherence", limit=5)
    for r in results:
        print(f"  - [{r.get('score', 0):.3f}] {r.get('content', '')[:80]}...")
    print()

    # Get stats
    stats = await memory.stats()
    print(f"Memory stats: {stats}")
    print()

    # Manual consolidation
    print("Triggering consolidation...")
    consolidated = await memory.consolidate()
    print(f"Consolidated {consolidated} memories")


async def relationship_example():
    """Demonstrate memory relationships."""
    memory = MirrorMemoryProvider(agent_id="relationship_example")

    # Store related memories
    await memory.store("mem_1", {"text": "River is the Oracle"})
    await memory.store("mem_2", {"text": "Kasra is the Builder"})
    await memory.store("mem_3", {"text": "River and Kasra form a dyad"})

    # Find related memories (requires memory IDs from prior storage)
    # This would work if we had actual memory IDs:
    # related = await memory.get_related("mem_id_here", limit=3)
    # print(f"Related memories: {related}")

    print("Relationship example complete")


if __name__ == "__main__":
    print("=== Mirror Memory Provider Example ===\n")
    asyncio.run(main())

    print("\n=== Relationship Example ===\n")
    asyncio.run(relationship_example())
