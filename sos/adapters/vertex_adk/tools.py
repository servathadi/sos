"""
SOS Tool Bridge for Google ADK

Bridges SOS tool registry to ADK-compatible tool format,
allowing ADK agents to use SOS tools like:
- web_search
- run_python (sandboxed)
- filesystem operations
- wallet operations
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional
import asyncio

from sos.clients.tools import ToolsClient
from sos.observability.logging import get_logger

log = get_logger("sos_tool_bridge")


@dataclass
class ADKTool:
    """
    ADK-compatible tool definition.

    This mirrors the expected ADK Tool interface.
    """
    name: str
    description: str
    parameters: dict[str, Any]
    function: Callable[..., Any]

    def __call__(self, **kwargs) -> Any:
        """Execute the tool."""
        return self.function(**kwargs)


class SOSToolBridge:
    """
    Bridge between SOS tool registry and ADK tools.

    Fetches tools from SOS Tools service and exposes them
    in ADK-compatible format.

    Example:
        bridge = SOSToolBridge()
        tools = await bridge.get_tools()

        # Use a tool
        result = await bridge.execute("web_search", query="Python docs")
    """

    def __init__(
        self,
        tools_url: str = "http://localhost:8004",
        allowed_tools: Optional[list[str]] = None
    ):
        """
        Initialize tool bridge.

        Args:
            tools_url: URL of SOS Tools service
            allowed_tools: Optional allowlist of tool names (None = all)
        """
        self.client = ToolsClient(tools_url)
        self.allowed_tools = set(allowed_tools) if allowed_tools else None
        self._tools_cache: Optional[list[dict]] = None

        log.info(f"SOSToolBridge initialized", url=tools_url)

    async def list_tools(self) -> list[dict]:
        """
        List available tools from SOS registry.

        Returns:
            List of tool definitions
        """
        try:
            tools = await self.client.list_tools()

            # Filter by allowlist if set
            if self.allowed_tools:
                tools = [t for t in tools if t.get("name") in self.allowed_tools]

            self._tools_cache = tools
            return tools

        except Exception as e:
            log.error(f"Failed to list tools: {e}")
            return []

    async def get_tools(self) -> list[ADKTool]:
        """
        Get tools as ADK-compatible objects.

        Returns:
            List of ADKTool instances
        """
        raw_tools = await self.list_tools()

        adk_tools = []
        for t in raw_tools:
            tool_name = t.get("name", "")

            # Create async executor for this tool
            async def execute_tool(**kwargs) -> Any:
                return await self.execute(tool_name, **kwargs)

            adk_tools.append(ADKTool(
                name=tool_name,
                description=t.get("description", ""),
                parameters=t.get("parameters", {}),
                function=execute_tool
            ))

        return adk_tools

    async def execute(self, tool_name: str, **kwargs) -> Any:
        """
        Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            **kwargs: Tool arguments

        Returns:
            Tool execution result
        """
        try:
            log.debug(f"Executing tool", tool=tool_name, args=kwargs)
            result = await self.client.execute(tool_name, kwargs)
            return result

        except Exception as e:
            log.error(f"Tool execution failed", tool=tool_name, error=str(e))
            return {"error": str(e)}

    def get_tool_schemas(self) -> list[dict]:
        """
        Get tool schemas for Vertex AI function calling.

        Returns:
            List of tool schemas in Vertex format
        """
        if not self._tools_cache:
            # Return empty if not loaded yet
            return []

        schemas = []
        for t in self._tools_cache:
            schemas.append({
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {
                    "type": "object",
                    "properties": {},
                    "required": []
                })
            })

        return schemas


def sos_tools_as_adk(
    tools_url: str = "http://localhost:8004",
    allowed_tools: Optional[list[str]] = None
) -> SOSToolBridge:
    """
    Create a tool bridge for use with ADK.

    Args:
        tools_url: URL of SOS Tools service
        allowed_tools: Optional allowlist of tool names

    Returns:
        Configured SOSToolBridge

    Example:
        bridge = sos_tools_as_adk()
        tools = await bridge.get_tools()
    """
    return SOSToolBridge(tools_url=tools_url, allowed_tools=allowed_tools)


# Common tool allowlists
SAFE_TOOLS = [
    "web_search",
    "calculator",
    "get_current_time",
]

CODE_TOOLS = [
    "run_python",
    "run_bash",
    "filesystem_read",
]

WALLET_TOOLS = [
    "wallet_balance",
    "wallet_send",
    "wallet_history",
]


def get_safe_tools_bridge(tools_url: str = "http://localhost:8004") -> SOSToolBridge:
    """Get bridge with only safe (read-only) tools."""
    return SOSToolBridge(tools_url=tools_url, allowed_tools=SAFE_TOOLS)


def get_code_tools_bridge(tools_url: str = "http://localhost:8004") -> SOSToolBridge:
    """Get bridge with code execution tools."""
    return SOSToolBridge(tools_url=tools_url, allowed_tools=CODE_TOOLS)


def get_full_tools_bridge(tools_url: str = "http://localhost:8004") -> SOSToolBridge:
    """Get bridge with all tools (no allowlist)."""
    return SOSToolBridge(tools_url=tools_url, allowed_tools=None)
