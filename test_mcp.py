import asyncio
import os
import sys

sys.path.append(os.getcwd())

from sos.services.tools.core import ToolsCore

async def test_mcp():
    print(">>> Initializing Tools Core (with MCP Bridge)...")
    core = ToolsCore()
    
    print("\n>>> Listing Tools:")
    tools = await core.list_tools()
    for t in tools:
        print(f" - {t['name']}")
        
    print("\n✅ MCP Discovery Complete")

if __name__ == "__main__":
    asyncio.run(test_mcp())

