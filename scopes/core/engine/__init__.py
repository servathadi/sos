"""
Core Engine Scope - Intent Processing and Identity Resolution

This scope defines the pure engine components for SOS.
Implementation lives in `sos/kernel/` and `sos/services/engine/`.

Components:
- Intent Router: `sos/kernel/intent.py` - Routes user intent to agents
- Coherence Physics: `sos/kernel/physics.py` - Will magnitude and collapse energy
- Coherence Monitor: `sos/services/memory/monitor.py` - Alpha drift and regime detection
- Agent Definitions: `sos/agents/definitions.py` - AgentSoul, AgentRole

Usage:
    from sos.kernel import IntentRouter, IntentDomain, CoherencePhysics
    from sos.agents.definitions import AgentSoul, AgentRole, ALL_AGENTS

See scopes/core/README.md for philosophy.
"""

# Re-export for convenience
from sos.kernel.intent import IntentRouter, IntentDomain, route_intent
from sos.kernel.physics import CoherencePhysics

__all__ = [
    "IntentRouter",
    "IntentDomain",
    "route_intent",
    "CoherencePhysics",
]
