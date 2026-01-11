from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import importlib

from sos.kernel import Config
from sos.observability.logging import get_logger

log = get_logger("tools_core")

@dataclass
class ToolDefinition:
    name: str
    description: str
    arguments: Dict[str, Any]

class ToolExecutor:
    """Abstract base for tool execution."""
    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any: ...

class LocalTools(ToolExecutor):
    """
    Executes sovereign tools (Web Search, Filesystem).
    """
    def __init__(self):
        self._tools = {
            "web_search": self._web_search,
            "filesystem_read": self._filesystem_read
        }

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        handler = self._tools[tool_name]
        return await handler(args)

    async def _web_search(self, args: Dict[str, Any]) -> str:
        query = args.get("query")
        if not query:
            return "Error: Missing query"
            
        log.info(f"Executing web_search: {query}")
        try:
            from duckduckgo_search import DDGS
            results = DDGS().text(query, max_results=3)
            return str(results)
        except Exception as e:
            log.error(f"Web search failed: {e}")
            return f"Search Error: {e}"

    async def _filesystem_read(self, args: Dict[str, Any]) -> str:
        # Simple safe read for Phase 2
        path = args.get("path")
        if not path:
            return "Error: Missing path"
        
        # Security check: Must be in /home/mumega
        if not path.startswith("/home/mumega"):
            return "Error: Access Denied (Sandbox violation)"
            
        try:
            with open(path, "r") as f:
                return f.read()
        except Exception as e:
            return f"Read Error: {e}"

from sos.services.tools.mcp_bridge import MCPBridge

class ToolsCore:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self.local_tools = LocalTools()
        self.mcp_bridge = MCPBridge()

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        log.info(f"Tool Execution Request: {tool_name}")
        
        # Route to Local or MCP
        if "__" in tool_name:
            return await self.mcp_bridge.execute(tool_name, args)
            
        return await self.local_tools.execute(tool_name, args)

    async def list_tools(self) -> List[Dict[str, Any]]:
        local = [
            {"name": "web_search", "description": "Search the web"},
            {"name": "filesystem_read", "description": "Read a file"}
        ]
        mcp = await self.mcp_bridge.list_tools()
        return local + mcp
