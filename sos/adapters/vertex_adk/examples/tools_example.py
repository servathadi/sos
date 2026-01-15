"""
SOS Tool Bridge Example

Demonstrates bridging SOS tools to ADK-compatible format.

Usage:
    python -m sos.adapters.vertex_adk.examples.tools_example
"""

import asyncio

from sos.adapters.vertex_adk import (
    SOSToolBridge,
    sos_tools_as_adk,
)
from sos.adapters.vertex_adk.tools import (
    get_safe_tools_bridge,
    get_code_tools_bridge,
    get_full_tools_bridge,
    SAFE_TOOLS,
    CODE_TOOLS,
    WALLET_TOOLS,
)


async def main():
    """Run tool bridge example."""
    # Create bridge with all tools
    bridge = sos_tools_as_adk(tools_url="http://localhost:8004")

    print("=== Full Tool Bridge ===")
    print(f"Created bridge: {bridge}")
    print()

    # List available tools
    print("Listing tools from SOS registry...")
    tools = await bridge.list_tools()
    print(f"Found {len(tools)} tools:")
    for t in tools[:10]:  # Show first 10
        print(f"  - {t.get('name')}: {t.get('description', '')[:60]}...")
    print()

    # Get as ADK-compatible tools
    print("Converting to ADK format...")
    adk_tools = await bridge.get_tools()
    print(f"Converted {len(adk_tools)} tools to ADK format")
    print()

    # Execute a tool
    print("Executing web_search tool...")
    try:
        result = await bridge.execute("web_search", query="SOS Sovereign Operating System")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Execution failed (tools service may not be running): {e}")
    print()

    # Get Vertex AI schemas
    schemas = bridge.get_tool_schemas()
    print(f"Generated {len(schemas)} Vertex AI tool schemas")


async def allowlist_example():
    """Demonstrate tool allowlisting."""
    print("\n=== Tool Allowlist Example ===\n")

    print(f"SAFE_TOOLS: {SAFE_TOOLS}")
    print(f"CODE_TOOLS: {CODE_TOOLS}")
    print(f"WALLET_TOOLS: {WALLET_TOOLS}")
    print()

    # Create bridges with different allowlists
    safe_bridge = get_safe_tools_bridge()
    code_bridge = get_code_tools_bridge()
    full_bridge = get_full_tools_bridge()

    print(f"Safe bridge allowlist: {safe_bridge.allowed_tools}")
    print(f"Code bridge allowlist: {code_bridge.allowed_tools}")
    print(f"Full bridge allowlist: {full_bridge.allowed_tools} (None = all)")
    print()

    # Custom allowlist
    custom_bridge = SOSToolBridge(
        tools_url="http://localhost:8004",
        allowed_tools=["web_search", "calculator", "get_current_time"]
    )
    print(f"Custom bridge allowlist: {custom_bridge.allowed_tools}")


async def vertex_integration_example():
    """Show how tools integrate with Vertex AI."""
    print("\n=== Vertex AI Integration Example ===\n")

    bridge = sos_tools_as_adk()
    await bridge.list_tools()  # Populate cache

    schemas = bridge.get_tool_schemas()

    print("Example tool schema for Vertex AI function calling:")
    if schemas:
        import json
        print(json.dumps(schemas[0], indent=2))
    else:
        print("No tools available (tools service may not be running)")

    print()
    print("To use with Vertex AI GenerativeModel:")
    print("""
    from vertexai.generative_models import GenerativeModel, Tool, FunctionDeclaration

    # Get schemas from bridge
    bridge = sos_tools_as_adk()
    await bridge.list_tools()
    schemas = bridge.get_tool_schemas()

    # Convert to Vertex function declarations
    functions = [
        FunctionDeclaration(
            name=s['name'],
            description=s['description'],
            parameters=s['parameters']
        )
        for s in schemas
    ]

    # Create tool for model
    vertex_tool = Tool(function_declarations=functions)

    # Use with model
    model = GenerativeModel(
        "gemini-2.5-flash",
        tools=[vertex_tool]
    )
    """)


if __name__ == "__main__":
    print("=== SOS Tool Bridge Example ===\n")
    asyncio.run(main())
    asyncio.run(allowlist_example())
    asyncio.run(vertex_integration_example())
