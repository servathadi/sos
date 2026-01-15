import importlib
import inspect
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

from sos.observability.logging import get_logger

log = get_logger("mcp_bridge")

# Add legacy CLI to path to load MCP servers
CLI_ROOT = Path("/home/mumega/cli").resolve()
if str(CLI_ROOT) not in sys.path:
    sys.path.append(str(CLI_ROOT))

class MCPBridge:
    """
    Bridges SOS to the legacy MCP Server ecosystem.
    """
    def __init__(self):
        self.servers = {}
        self._discover_local_servers()

    def _discover_local_servers(self):
        """
        Scans mumega.core.mcp for server classes.
        """
        try:
            # We look for specific known servers to avoid loading everything
            # In a real implementation, this would be config-driven
            known_servers = [
                ("mumega.core.mcp.github_server", "GitHubMCPServer"),
                ("mumega.core.mcp.notion_server", "NotionMCPServer"),
                ("mumega.core.mcp.playwright_server", "PlaywrightMCPServer")
            ]

            for module_path, class_name in known_servers:
                try:
                    mod = importlib.import_module(module_path)
                    cls = getattr(mod, class_name)
                    # Initialize with empty config for discovery
                    server = cls({}) 
                    self.servers[server.get_server_name()] = server
                    log.info(f"Loaded MCP Server: {server.get_server_name()}")
                except ImportError as e:
                    log.warning(f"Could not load {module_path}: {e}")
                except Exception as e:
                    log.error(f"Failed to init {class_name}: {e}")

        except Exception as e:
            log.error("MCP Discovery Failed", error=str(e))

    async def list_tools(self) -> List[Dict[str, Any]]:
        tools = []
        for server_name, server in self.servers.items():
            for tool_name in server.get_available_tools():
                tools.append({
                    "name": f"{server_name}__{tool_name}",
                    "description": f"MCP Tool from {server_name}",
                    "source": "mcp"
                })
        return tools

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        if "__" not in tool_name:
            raise ValueError("Invalid MCP tool format. Expected server__tool")
        
        server_name, real_tool_name = tool_name.split("__", 1)
        
        if server_name not in self.servers:
            raise ValueError(f"Unknown MCP Server: {server_name}")
            
        server = self.servers[server_name]
        return await server.execute_tool(real_tool_name, args)
