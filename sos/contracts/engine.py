"""
SOS Engine Service Contract.

The Engine is the orchestration layer that:
- Receives messages from adapters
- Routes to appropriate services (memory, economy, tools)
- Manages model selection and failover
- Enforces capability requirements
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

from sos.kernel import Message, Response, Capability


@dataclass
class ChatRequest:
    """Request for chat completion."""
    message: str
    agent_id: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None  # Override default model
    stream: bool = False
    tools_enabled: bool = True
    memory_enabled: bool = True
    capability: Optional[Capability] = None


@dataclass
class ChatResponse:
    """Response from chat completion."""
    content: str
    agent_id: str
    model_used: str
    conversation_id: str
    tool_calls: list[dict[str, Any]] = None
    memory_refs: list[str] = None
    tokens_used: int = 0


@dataclass
class ToolCallRequest:
    """Request to execute a tool."""
    tool_name: str
    arguments: dict[str, Any]
    agent_id: str
    capability: Capability


@dataclass
class ToolCallResult:
    """Result of tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    duration_ms: int = 0


class EngineContract(ABC):
    """
    Abstract contract for the SOS Engine Service.

    All Engine implementations must conform to this interface.
    """

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat message and return response.

        Args:
            request: Chat request with message and context

        Returns:
            ChatResponse with generated content
        """
        pass

    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """
        Process a chat message and stream response tokens.

        Args:
            request: Chat request with message and context

        Yields:
            Response tokens as they're generated
        """
        pass

    @abstractmethod
    async def execute_tool(self, request: ToolCallRequest) -> ToolCallResult:
        """
        Execute a tool with given arguments.

        Args:
            request: Tool execution request

        Returns:
            Tool execution result
        """
        pass

    @abstractmethod
    async def get_models(self) -> list[dict[str, Any]]:
        """
        Get available models and their status.

        Returns:
            List of model info dicts with name, status, capabilities
        """
        pass

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        """
        Get engine health status.

        Returns:
            Health status dict with status, version, dependencies
        """
        pass

    # Message-based interface (for service-to-service communication)

    @abstractmethod
    async def handle_message(self, message: Message) -> Response:
        """
        Handle an incoming message.

        This is the low-level interface for service-to-service communication.

        Args:
            message: Incoming message

        Returns:
            Response to the message
        """
        pass


# HTTP API spec for documentation
ENGINE_API_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "SOS Engine Service",
        "version": "0.1.0",
    },
    "paths": {
        "/chat": {
            "post": {
                "summary": "Process chat message",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ChatRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ChatResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/chat/stream": {
            "post": {
                "summary": "Process chat message with streaming",
                "responses": {
                    "200": {
                        "content": {
                            "text/event-stream": {}
                        }
                    }
                }
            }
        },
        "/tools/{tool_name}": {
            "post": {
                "summary": "Execute a tool",
            }
        },
        "/models": {
            "get": {
                "summary": "List available models",
            }
        },
        "/health": {
            "get": {
                "summary": "Health check",
            }
        },
    },
}
