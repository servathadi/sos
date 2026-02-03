"""
SOS Protocol Error Codes

Standardized error codes and exceptions for all SOS services.

Error Code Ranges:
- 1xxx: General errors
- 2xxx: Authentication/Authorization
- 3xxx: Resource errors
- 4xxx: Rate limiting
- 5xxx: Model/LLM errors
- 6xxx: Memory errors
- 7xxx: Economy errors
- 8xxx: Tools errors
"""

from enum import IntEnum
from typing import Optional, Any, Dict
from dataclasses import dataclass, field


class ErrorCode(IntEnum):
    """SOS protocol error codes."""

    # General (1xxx)
    UNKNOWN = 1000
    INVALID_REQUEST = 1001
    INTERNAL_ERROR = 1002
    SERVICE_UNAVAILABLE = 1003
    TIMEOUT = 1004
    VALIDATION_ERROR = 1005

    # Auth (2xxx)
    UNAUTHORIZED = 2001
    FORBIDDEN = 2002
    TOKEN_EXPIRED = 2003
    TOKEN_INVALID = 2004
    SCOPE_DENIED = 2005
    CAPABILITY_MISSING = 2006

    # Resource (3xxx)
    NOT_FOUND = 3001
    ALREADY_EXISTS = 3002
    CONFLICT = 3003
    GONE = 3004

    # Rate Limiting (4xxx)
    RATE_LIMITED = 4001
    QUOTA_EXCEEDED = 4002
    CIRCUIT_OPEN = 4003

    # Model (5xxx)
    MODEL_UNAVAILABLE = 5001
    MODEL_OVERLOADED = 5002
    CONTEXT_TOO_LONG = 5003
    GENERATION_FAILED = 5004
    NO_MODELS_AVAILABLE = 5005

    # Memory (6xxx)
    MEMORY_FULL = 6001
    VECTOR_ERROR = 6002
    EMBEDDING_FAILED = 6003
    RETRIEVAL_FAILED = 6004

    # Economy (7xxx)
    INSUFFICIENT_FUNDS = 7001
    INVALID_TRANSACTION = 7002
    LEDGER_ERROR = 7003

    # Tools (8xxx)
    TOOL_NOT_FOUND = 8001
    TOOL_EXECUTION_FAILED = 8002
    TOOL_TIMEOUT = 8003
    TOOL_PERMISSION_DENIED = 8004
    SANDBOX_ERROR = 8005


@dataclass
class SOSError:
    """Structured error response."""
    code: ErrorCode
    message: str
    detail: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "code": int(self.code),
            "message": self.message,
        }
        if self.detail:
            result["detail"] = self.detail
        if self.context:
            result["context"] = self.context
        return result


class SOSException(Exception):
    """Base exception for SOS services."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        detail: str = None,
        **context
    ):
        self.error = SOSError(
            code=code,
            message=message,
            detail=detail,
            context=context or {}
        )
        super().__init__(message)

    @property
    def code(self) -> ErrorCode:
        return self.error.code

    def to_dict(self) -> Dict[str, Any]:
        return {"ok": False, "error": self.error.to_dict()}


# Convenience exception classes
class AuthError(SOSException):
    """Authentication/authorization error."""
    def __init__(self, message: str = "Unauthorized", **context):
        super().__init__(ErrorCode.UNAUTHORIZED, message, **context)


class ForbiddenError(SOSException):
    """Access forbidden error."""
    def __init__(self, message: str = "Access denied", **context):
        super().__init__(ErrorCode.FORBIDDEN, message, **context)


class ScopeDeniedError(SOSException):
    """Missing required scope."""
    def __init__(self, required: list, provided: list = None):
        super().__init__(
            ErrorCode.SCOPE_DENIED,
            "Missing required scope",
            detail=f"Required: {required}",
            required=required,
            provided=provided or []
        )


class NotFoundError(SOSException):
    """Resource not found."""
    def __init__(self, resource: str, identifier: str = None):
        msg = f"{resource} not found"
        if identifier:
            msg = f"{resource} '{identifier}' not found"
        super().__init__(ErrorCode.NOT_FOUND, msg, resource=resource, id=identifier)


class RateLimitError(SOSException):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int = None):
        super().__init__(
            ErrorCode.RATE_LIMITED,
            "Rate limit exceeded",
            detail=f"Retry after {retry_after}s" if retry_after else None,
            retry_after=retry_after
        )


class ModelError(SOSException):
    """Model/LLM error."""
    def __init__(self, code: ErrorCode, message: str, model: str = None, **context):
        super().__init__(code, message, model=model, **context)


class MemoryError(SOSException):
    """Memory service error."""
    def __init__(self, code: ErrorCode, message: str, **context):
        super().__init__(code, message, **context)


class ToolError(SOSException):
    """Tool execution error."""
    def __init__(self, code: ErrorCode, message: str, tool: str = None, **context):
        super().__init__(code, message, tool=tool, **context)


class ValidationError(SOSException):
    """Request validation error."""
    def __init__(self, message: str, field: str = None, **context):
        super().__init__(
            ErrorCode.VALIDATION_ERROR,
            message,
            field=field,
            **context
        )


# Response helpers
def error_response(error: SOSException) -> Dict[str, Any]:
    """Create standardized error response."""
    return error.to_dict()


def success_response(result: Any = None, **extra) -> Dict[str, Any]:
    """Create standardized success response."""
    response = {"ok": True}
    if result is not None:
        response["result"] = result
    response.update(extra)
    return response
