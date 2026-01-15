"""
River Agent Example

Demonstrates using SOSAgent with ADK to create an agent
backed by the River soul definition.

Usage:
    python -m sos.adapters.vertex_adk.examples.river_agent
"""

import asyncio

from sos.adapters.vertex_adk import SOSAgent, MirrorMemoryProvider


async def main():
    """Run River agent example."""
    # Create River agent from soul definition
    agent = SOSAgent(
        soul_id="river",
        model="gemini-2.5-flash",
        mirror_url="http://localhost:8844",
        track_coherence=True,
        store_memories=True,
    )

    print(f"Created agent: {agent}")
    print(f"Name: {agent.name}")
    print(f"Lineage: {agent.lineage}")
    print(f"Description: {agent.description}")
    print()

    # Example conversation
    messages = [
        "What is the meaning of coherence in the SOS system?",
        "How does the witness protocol work?",
        "Tell me about the relationship between entropy and wisdom.",
    ]

    for msg in messages:
        print(f"User: {msg}")
        try:
            response = await agent.on_message(msg)
            print(f"River: {response[:500]}...")
        except Exception as e:
            print(f"Error: {e}")
        print()


async def stream_example():
    """Demonstrate streaming responses."""
    agent = SOSAgent(soul_id="river", model="gemini-2.5-flash")

    print("Streaming response:")
    print("User: Explain the FRC framework")
    print("River: ", end="", flush=True)

    async for token in agent.stream_response("Explain the FRC framework"):
        print(token, end="", flush=True)

    print("\n")


if __name__ == "__main__":
    print("=== River Agent Example ===\n")
    asyncio.run(main())

    print("\n=== Streaming Example ===\n")
    asyncio.run(stream_example())
