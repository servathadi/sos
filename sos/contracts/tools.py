"""
SOS Tools Service Contract.

The Tools Service handles:
- Tool registry and discovery
- MCP server management
- Tool execution with sandboxing
- Capability gating for tool access
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from enum import Enum

from sos.kernel import Capability


class ToolCategory(Enum):
    """Categories of tools."""
    SEARCH = "search"       # Web search, document search
    CODE = "code"           # Code execution, analysis
    FILE = "file"           # File operations
    NETWORK = "network"     # Network requests
    DATA = "data"           # Data processing
    MEMORY = "memory"       # Memory operations (via memory service)
    SYSTEM = "system"       # System operations
    CUSTOM = "custom"       # Custom/plugin tools


class ToolStatus(Enum):
    """Tool availability status."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    DISABLED = "disabled"


class ToolsRpcErrorCode(Enum):
    """Standard gateway RPC error codes."""
    CAPABILITY_REQUIRED = 40101
    CAPABILITY_INVALID = 40102
    CAPABILITY_EXPIRED = 40103
    CAPABILITY_DENIED = 40301
    TOOL_NOT_FOUND = 40401
    RATE_LIMITED = 42901
    TOOL_ERROR = 50001
    GATEWAY_ERROR = 50002
    TOOL_UNAVAILABLE = 50301


@dataclass
class ToolsRpcError:
    """JSON-RPC error object for gateway responses."""
    code: ToolsRpcErrorCode
    message: str
    data: Optional[dict[str, Any]] = None


@dataclass
class ToolsRpcRequest:
    """JSON-RPC request envelope for tools gateway."""
    jsonrpc: str
    id: str
    method: str
    params: dict[str, Any]


@dataclass
class ToolsRpcResponse:
    """JSON-RPC response envelope for tools gateway."""
    jsonrpc: str
    id: str
    result: Optional[dict[str, Any]] = None
    error: Optional[ToolsRpcError] = None


@dataclass
class ToolDefinition:
    """
    Definition of a tool in SOS.

    Attributes:
        name: Unique tool name
        description: Human-readable description
        category: Tool category
        parameters: JSON Schema for parameters
        returns: Description of return value
        required_capability: Capability action required
        rate_limit: Rate limit (e.g., "10/minute")
        timeout_seconds: Execution timeout
        sandbox_required: Whether sandboxing is required
        metadata: Additional metadata
    """
    name: str
    description: str
    category: ToolCategory
    parameters: dict[str, Any]  # JSON Schema
    returns: str
    required_capability: str = "tool:execute"
    rate_limit: Optional[str] = None
    timeout_seconds: int = 30
    sandbox_required: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionRequest:
    """Request to execute a tool."""
    tool_name: str
    arguments: dict[str, Any]
    agent_id: str
    capability: Capability
    timeout_override: Optional[int] = None


@dataclass
class ToolExecutionResult:
    """Result of tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: int = 0
    logs: list[str] = field(default_factory=list)


@dataclass
class MCPServer:
    """
    MCP (Model Context Protocol) server definition.

    Attributes:
        name: Server name
        url: Server URL or socket path
        transport: Transport type (http, stdio, sse)
        tools: List of tools provided
        status: Current status
        last_health_check: Last successful health check
    """
    name: str
    url: str
    transport: str = "http"  # http | stdio | sse
    tools: list[str] = field(default_factory=list)
    status: ToolStatus = ToolStatus.AVAILABLE
    last_health_check: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ToolsContract(ABC):
    """
    Abstract contract for the SOS Tools Service.

    All Tools implementations must conform to this interface.
    """

    @abstractmethod
    async def register_tool(
        self,
        definition: ToolDefinition,
        handler: Optional[Callable] = None,
        capability: Optional[Capability] = None,
    ) -> bool:
        """
        Register a new tool.

        Args:
            definition: Tool definition
            handler: Optional handler function (for local tools)
            capability: Authorization capability

        Returns:
            True if registered successfully
        """
        pass

    @abstractmethod
    async def unregister_tool(
        self,
        tool_name: str,
        capability: Optional[Capability] = None,
    ) -> bool:
        """
        Unregister a tool.

        Args:
            tool_name: Tool to unregister
            capability: Authorization capability

        Returns:
            True if unregistered
        """
        pass

    @abstractmethod
    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """
        Execute a tool.

        Args:
            request: Execution request

        Returns:
            Execution result
        """
        pass

    @abstractmethod
    async def get_tool(self, tool_name: str) -> Optional[ToolDefinition]:
        """
        Get tool definition.

        Args:
            tool_name: Tool name

        Returns:
            Tool definition if found
        """
        pass

    @abstractmethod
    async def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        available_only: bool = True,
    ) -> list[ToolDefinition]:
        """
        List available tools.

        Args:
            category: Filter by category
            available_only: Only show available tools

        Returns:
            List of tool definitions
        """
        pass

    @abstractmethod
    async def get_tool_status(self, tool_name: str) -> ToolStatus:
        """
        Get tool availability status.

        Args:
            tool_name: Tool to check

        Returns:
            Tool status
        """
        pass

    # MCP Server Management

    @abstractmethod
    async def register_mcp_server(
        self,
        server: MCPServer,
        capability: Optional[Capability] = None,
    ) -> bool:
        """
        Register an MCP server.

        Args:
            server: MCP server definition
            capability: Authorization capability

        Returns:
            True if registered
        """
        pass

    @abstractmethod
    async def unregister_mcp_server(
        self,
        server_name: str,
        capability: Optional[Capability] = None,
    ) -> bool:
        """
        Unregister an MCP server.

        Args:
            server_name: Server to unregister
            capability: Authorization capability

        Returns:
            True if unregistered
        """
        pass

    @abstractmethod
    async def list_mcp_servers(self) -> list[MCPServer]:
        """
        List registered MCP servers.

        Returns:
            List of MCP servers
        """
        pass

    @abstractmethod
    async def discover_mcp_tools(self, server_name: str) -> list[ToolDefinition]:
        """
        Discover tools from an MCP server.

        Args:
            server_name: Server to query

        Returns:
            List of discovered tools
        """
        pass

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """
        Get tools service health status.

        Returns:
            Health status with stats
        """
        pass


# Built-in tool definitions
BUILTIN_TOOLS = [
    ToolDefinition(
        name="web_search",
        description="Search the web for information",
        category=ToolCategory.SEARCH,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
        returns="List of search results with title, url, and snippet",
        rate_limit="10/minute",
    ),
    ToolDefinition(
        name="read_file",
        description="Read contents of a file",
        category=ToolCategory.FILE,
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
                "encoding": {"type": "string", "default": "utf-8"},
            },
            "required": ["path"],
        },
        returns="File contents as string",
        required_capability="file:read",
    ),
    ToolDefinition(
        name="write_file",
        description="Write contents to a file",
        category=ToolCategory.FILE,
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
                "encoding": {"type": "string", "default": "utf-8"},
            },
            "required": ["path", "content"],
        },
        returns="Boolean indicating success",
        required_capability="file:write",
    ),
    ToolDefinition(
        name="execute_code",
        description="Execute code in a sandboxed environment",
        category=ToolCategory.CODE,
        parameters={
            "type": "object",
            "properties": {
                "language": {"type": "string", "enum": ["python", "javascript"]},
                "code": {"type": "string", "description": "Code to execute"},
            },
            "required": ["language", "code"],
        },
        returns="Execution output and any errors",
        timeout_seconds=60,
        sandbox_required=True,
    ),
]
