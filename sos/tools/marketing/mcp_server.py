"""
Marketing MCP Server

Exposes marketing toolkit as MCP tools for any agent to use.

Run:
    python -m sos.tools.marketing.mcp_server

Or add to claude_desktop_config.json:
    {
        "mcpServers": {
            "marketing": {
                "command": "python",
                "args": ["-m", "sos.tools.marketing.mcp_server"]
            }
        }
    }
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

# MCP imports - using stdio transport
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

from .client import MarketingClient
from .schemas import Platform


# Global client cache
_clients: Dict[str, MarketingClient] = {}


def get_client(business_id: str) -> MarketingClient:
    """Get or create a marketing client."""
    if business_id not in _clients:
        _clients[business_id] = MarketingClient(business_id=business_id)
    return _clients[business_id]


# Tool definitions
TOOLS = [
    Tool(
        name="marketing_connect_ga4",
        description="Connect Google Analytics 4 to a business",
        inputSchema={
            "type": "object",
            "properties": {
                "business_id": {"type": "string", "description": "Unique business identifier"},
                "property_id": {"type": "string", "description": "GA4 property ID"},
                "access_token": {"type": "string", "description": "OAuth access token"},
            },
            "required": ["business_id", "property_id", "access_token"],
        },
    ),
    Tool(
        name="marketing_connect_google_ads",
        description="Connect Google Ads to a business",
        inputSchema={
            "type": "object",
            "properties": {
                "business_id": {"type": "string", "description": "Unique business identifier"},
                "customer_id": {"type": "string", "description": "Google Ads customer ID"},
                "access_token": {"type": "string", "description": "OAuth access token"},
            },
            "required": ["business_id", "customer_id", "access_token"],
        },
    ),
    Tool(
        name="marketing_connect_facebook_ads",
        description="Connect Facebook/Meta Ads to a business",
        inputSchema={
            "type": "object",
            "properties": {
                "business_id": {"type": "string", "description": "Unique business identifier"},
                "ad_account_id": {"type": "string", "description": "Facebook Ad Account ID"},
                "access_token": {"type": "string", "description": "Access token"},
            },
            "required": ["business_id", "ad_account_id", "access_token"],
        },
    ),
    Tool(
        name="marketing_connect_search_console",
        description="Connect Google Search Console to a business",
        inputSchema={
            "type": "object",
            "properties": {
                "business_id": {"type": "string", "description": "Unique business identifier"},
                "site_url": {"type": "string", "description": "Site URL (e.g., https://example.com)"},
                "access_token": {"type": "string", "description": "OAuth access token"},
            },
            "required": ["business_id", "site_url", "access_token"],
        },
    ),
    Tool(
        name="marketing_connect_clarity",
        description="Connect Microsoft Clarity to a business",
        inputSchema={
            "type": "object",
            "properties": {
                "business_id": {"type": "string", "description": "Unique business identifier"},
                "project_id": {"type": "string", "description": "Clarity project ID"},
            },
            "required": ["business_id", "project_id"],
        },
    ),
    Tool(
        name="marketing_get_dashboard",
        description="Get unified marketing dashboard for a business",
        inputSchema={
            "type": "object",
            "properties": {
                "business_id": {"type": "string", "description": "Unique business identifier"},
                "days": {"type": "integer", "description": "Number of days to analyze", "default": 30},
            },
            "required": ["business_id"],
        },
    ),
    Tool(
        name="marketing_get_insights",
        description="Get AI-generated marketing insights",
        inputSchema={
            "type": "object",
            "properties": {
                "business_id": {"type": "string", "description": "Unique business identifier"},
            },
            "required": ["business_id"],
        },
    ),
    Tool(
        name="marketing_pause_campaign",
        description="Pause an ad campaign",
        inputSchema={
            "type": "object",
            "properties": {
                "business_id": {"type": "string", "description": "Unique business identifier"},
                "campaign_id": {"type": "string", "description": "Campaign ID to pause"},
                "platform": {"type": "string", "enum": ["google_ads", "facebook_ads"], "default": "google_ads"},
            },
            "required": ["business_id", "campaign_id"],
        },
    ),
    Tool(
        name="marketing_resume_campaign",
        description="Resume a paused ad campaign",
        inputSchema={
            "type": "object",
            "properties": {
                "business_id": {"type": "string", "description": "Unique business identifier"},
                "campaign_id": {"type": "string", "description": "Campaign ID to resume"},
                "platform": {"type": "string", "enum": ["google_ads", "facebook_ads"], "default": "google_ads"},
            },
            "required": ["business_id", "campaign_id"],
        },
    ),
    Tool(
        name="marketing_list_platforms",
        description="List connected marketing platforms for a business",
        inputSchema={
            "type": "object",
            "properties": {
                "business_id": {"type": "string", "description": "Unique business identifier"},
            },
            "required": ["business_id"],
        },
    ),
]


async def handle_tool(name: str, arguments: Dict[str, Any]) -> str:
    """Handle a tool call."""
    business_id = arguments.get("business_id", "default")
    client = get_client(business_id)

    try:
        if name == "marketing_connect_ga4":
            success = await client.connect_google_analytics(
                property_id=arguments["property_id"],
                access_token=arguments["access_token"],
            )
            return json.dumps({"success": success, "platform": "google_analytics"})

        elif name == "marketing_connect_google_ads":
            success = await client.connect_google_ads(
                customer_id=arguments["customer_id"],
                access_token=arguments["access_token"],
            )
            return json.dumps({"success": success, "platform": "google_ads"})

        elif name == "marketing_connect_facebook_ads":
            success = await client.connect_facebook_ads(
                ad_account_id=arguments["ad_account_id"],
                access_token=arguments["access_token"],
            )
            return json.dumps({"success": success, "platform": "facebook_ads"})

        elif name == "marketing_connect_search_console":
            success = await client.connect_search_console(
                site_url=arguments["site_url"],
                access_token=arguments["access_token"],
            )
            return json.dumps({"success": success, "platform": "search_console"})

        elif name == "marketing_connect_clarity":
            success = await client.connect_clarity(
                project_id=arguments["project_id"],
            )
            return json.dumps({"success": success, "platform": "clarity"})

        elif name == "marketing_get_dashboard":
            days = arguments.get("days", 30)
            dashboard = await client.get_dashboard(days=days)
            return json.dumps({
                "business_id": dashboard.business_id,
                "date_range": [str(dashboard.date_range[0]), str(dashboard.date_range[1])],
                "total_traffic": dashboard.total_traffic,
                "total_leads": dashboard.total_leads,
                "total_ad_spend": dashboard.total_ad_spend,
                "cost_per_lead": dashboard.cost_per_lead,
                "health_score": dashboard.health_score,
                "connected_platforms": [p.value for p in dashboard.connected_platforms],
                "insights_count": len(dashboard.insights),
            })

        elif name == "marketing_get_insights":
            dashboard = await client.get_dashboard()
            insights = [
                {
                    "type": i.type.value,
                    "priority": i.priority.value,
                    "title": i.title,
                    "description": i.description,
                    "recommendation": i.recommendation,
                    "platform": i.platform.value if i.platform else None,
                }
                for i in dashboard.insights
            ]
            return json.dumps({"insights": insights})

        elif name == "marketing_pause_campaign":
            platform = Platform(arguments.get("platform", "google_ads"))
            success = await client.pause_campaign(
                campaign_id=arguments["campaign_id"],
                platform=platform,
            )
            return json.dumps({"success": success, "action": "paused"})

        elif name == "marketing_resume_campaign":
            platform = Platform(arguments.get("platform", "google_ads"))
            success = await client.resume_campaign(
                campaign_id=arguments["campaign_id"],
                platform=platform,
            )
            return json.dumps({"success": success, "action": "resumed"})

        elif name == "marketing_list_platforms":
            platforms = client.get_connected_platforms()
            return json.dumps({
                "connected_platforms": [p.value for p in platforms],
                "count": len(platforms),
            })

        else:
            return json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as e:
        return json.dumps({"error": str(e)})


def create_server() -> "Server":
    """Create the MCP server."""
    if not HAS_MCP:
        raise ImportError("MCP package not installed. Run: pip install mcp")

    server = Server("marketing")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        result = await handle_tool(name, arguments)
        return [TextContent(type="text", text=result)]

    return server


async def main():
    """Run the MCP server."""
    if not HAS_MCP:
        print("Error: MCP package not installed. Run: pip install mcp", file=sys.stderr)
        sys.exit(1)

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    asyncio.run(main())
