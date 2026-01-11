"""
SOS Kernel - Core schema, identity, and capability primitives.

The kernel is the minimal stable core of SOS. It contains:
- Message/Response schema for all service communication
- Identity primitives for agents and services
- Capability tokens for access control
- Configuration management

Constraints:
- No external network calls
- No heavy ML or vector dependencies
- Must be importable in <100ms
"""

from sos.kernel.schema import Message, Response, MessageType, ResponseStatus
from sos.kernel.identity import Identity, AgentIdentity, ServiceIdentity
from sos.kernel.capability import (
    Capability,
    CapabilityAction,
    sign_capability,
    verify_capability,
    verify_capability_signature,
)
from sos.kernel.config import Config, RuntimePaths

__all__ = [
    # Schema
    "Message",
    "Response",
    "MessageType",
    "ResponseStatus",
    # Identity
    "Identity",
    "AgentIdentity",
    "ServiceIdentity",
    # Capability
    "Capability",
    "CapabilityAction",
    "sign_capability",
    "verify_capability",
    "verify_capability_signature",
    # Config
    "Config",
    "RuntimePaths",
]
