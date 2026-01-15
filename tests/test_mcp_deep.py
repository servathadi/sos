import asyncio
import sys
import json
import logging
from sos.clients.tools import ToolsClient

log = logging.getLogger(__name__)

async def main():
    client = ToolsClient("http://localhost:8003")

    print("Testing Deep Research Tool (Native MCP)...")

    query = "Python"
    payload = {
        "tool_name": "deep_research",
        "arguments": {
            "query": query,
            "count": 2,
            "depth": "standard"
        }
    }

    try:
        print(f"Dispatching Research for: '{query}'...")
        # Note: ToolsClient.execute handles the payload routing
        result = await client.execute(payload)

        log.debug(f"Raw Result: {result}")
        
        if "error" in result:
            print(f"❌ Tool Error: {result['error']}")
            return
            
        print("\n✅ Research Report Received:")
        print(f"Timestamp: {result.get('timestamp')}")
        print(f"Sources Found: {result.get('sources_found')}")
        print(f"Successful Extractions: {result.get('successful_extractions')}")
        
        # Show first result snippet
        if result.get("results"):
            first = result["results"][0]
            print(f"\n📄 Top Source: {first.get('title')}")
            print(f"URL: {first.get('url')}")
            content_preview = first.get('content', '')[:300]
            print(f"Content Preview: {content_preview}...")
        else:
            print("⚠️ No results returned.")
            
    except Exception as e:
        print(f"❌ Execution Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
