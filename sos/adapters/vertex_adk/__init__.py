"""
SOS Vertex ADK Adapter

Provides integration between SOS (Sovereign Operating System) and
Google's Agent Development Kit (ADK).

Components:
- SOSAgent: ADK Agent backed by SOS soul definitions
- MirrorMemoryProvider: ADK memory backed by SOS Mirror API
- sos_tools_as_adk: Bridge SOS tools to ADK format

Usage:
    from sos.adapters.vertex_adk import SOSAgent, MirrorMemoryProvider

    # Create agent from SOS soul
    agent = SOSAgent(soul_id="river")

    # Use with ADK runtime
    response = await agent.on_message("Hello")
"""

from sos.adapters.vertex_adk.agent import SOSAgent
from sos.adapters.vertex_adk.memory import MirrorMemoryProvider
from sos.adapters.vertex_adk.tools import sos_tools_as_adk, SOSToolBridge

__all__ = [
    "SOSAgent",
    "MirrorMemoryProvider",
    "sos_tools_as_adk",
    "SOSToolBridge",
]

__version__ = "0.1.0"
