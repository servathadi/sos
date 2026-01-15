"""
SOS Structured Logging.

JSON-formatted logging with trace propagation for all SOS services.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Optional
from contextvars import ContextVar

# Trace context vars live in tracing.py (single source of truth)
from sos.observability.tracing import trace_id_var, span_id_var

# Context variable for agent propagation (logging-specific)
agent_id_var: ContextVar[str] = ContextVar("agent_id", default="")

# Emoji stripping configuration
# Set SOS_LOG_EMOJIS=0 to strip emojis from log messages (enterprise mode)
_STRIP_EMOJIS = os.getenv("SOS_LOG_EMOJIS", "1").lower() in ("0", "false", "no")

# Regex pattern to match most emojis
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U00002600-\U000026FF"  # misc symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero width joiner
    "]+",
    flags=re.UNICODE
)


def _strip_emojis(text: str) -> str:
    """Strip emojis from text if SOS_LOG_EMOJIS=0."""
    if not _STRIP_EMOJIS:
        return text
    return _EMOJI_PATTERN.sub("", text).strip()


class SOSLogger:
    """
    Structured JSON logger for SOS services.

    Emits JSON logs to stdout/stderr with automatic trace context inclusion.

    Example:
        log = SOSLogger("engine")
        log.info("Request received", endpoint="/chat", tokens=150)

    Output:
        {"ts": "2026-01-10T12:00:00Z", "level": "info", "service": "engine",
         "msg": "Request received", "extra": {"endpoint": "/chat", "tokens": 150}}
    """

    def __init__(self, service: str, min_level: str = "info"):
        """
        Initialize logger.

        Args:
            service: Service name (e.g., "engine", "memory")
            min_level: Minimum log level to emit
        """
        self.service = service
        self.min_level = min_level
        self._level_order = ["debug", "info", "warn", "error", "fatal"]

    def _should_log(self, level: str) -> bool:
        """Check if level should be logged."""
        try:
            return self._level_order.index(level) >= self._level_order.index(self.min_level)
        except ValueError:
            return True

    def _emit(self, level: str, msg: str, **extra: Any) -> None:
        """Emit a log record."""
        if not self._should_log(level):
            return

        # Strip emojis if enterprise mode enabled (SOS_LOG_EMOJIS=0)
        clean_msg = _strip_emojis(msg)

        record: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "service": self.service,
            "msg": clean_msg,
        }

        # Add trace context if available
        if trace_id := trace_id_var.get():
            record["trace_id"] = trace_id
        if span_id := span_id_var.get():
            record["span_id"] = span_id
        if agent_id := agent_id_var.get():
            record["agent_id"] = agent_id

        # Add extra fields
        if extra:
            record["extra"] = extra

        # Output to appropriate stream
        stream = sys.stderr if level in ("error", "fatal") else sys.stdout
        print(json.dumps(record), file=stream, flush=True)

    def debug(self, msg: str, **extra: Any) -> None:
        """Log debug message."""
        self._emit("debug", msg, **extra)

    def info(self, msg: str, **extra: Any) -> None:
        """Log info message."""
        self._emit("info", msg, **extra)

    def warn(self, msg: str, **extra: Any) -> None:
        """Log warning message."""
        self._emit("warn", msg, **extra)

    def warning(self, msg: str, **extra: Any) -> None:
        """Log warning message (alias for warn)."""
        self._emit("warn", msg, **extra)

    def error(self, msg: str, **extra: Any) -> None:
        """Log error message."""
        self._emit("error", msg, **extra)

    def fatal(self, msg: str, **extra: Any) -> None:
        """Log fatal message."""
        self._emit("fatal", msg, **extra)

    def with_context(self, **context: Any) -> SOSLogger:
        """
        Create a child logger with additional default context.

        Args:
            **context: Default extra fields for all logs

        Returns:
            New logger instance
        """
        return ContextLogger(self, context)


class ContextLogger(SOSLogger):
    """Logger with persistent context."""

    def __init__(self, parent: SOSLogger, context: dict[str, Any]):
        super().__init__(parent.service, parent.min_level)
        self._context = context

    def _emit(self, level: str, msg: str, **extra: Any) -> None:
        merged = {**self._context, **extra}
        super()._emit(level, msg, **merged)


# Global logger registry
_loggers: dict[str, SOSLogger] = {}


def get_logger(service: str, min_level: str = "info") -> SOSLogger:
    """
    Get or create a logger for a service.

    Args:
        service: Service name
        min_level: Minimum log level

    Returns:
        SOSLogger instance
    """
    if service not in _loggers:
        _loggers[service] = SOSLogger(service, min_level)
    return _loggers[service]


def set_trace_context(trace_id: str, span_id: Optional[str] = None) -> None:
    """
    Set trace context for current execution context.

    Args:
        trace_id: Trace identifier
        span_id: Optional span identifier
    """
    trace_id_var.set(trace_id)
    if span_id:
        span_id_var.set(span_id)


def set_agent_context(agent_id: str) -> None:
    """
    Set agent context for current execution context.

    Args:
        agent_id: Agent identifier
    """
    agent_id_var.set(agent_id)


def clear_context() -> None:
    """Clear all context variables."""
    trace_id_var.set("")
    span_id_var.set("")
    agent_id_var.set("")
