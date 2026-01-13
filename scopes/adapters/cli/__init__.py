"""
CLI Adapter Scope - Command Line Interface for SOS

This scope implements the Click-based CLI for SOS.
Transforms CLI commands into Bus Messages.

Commands:
- task: Task CRUD (create, list, show, update, complete, sync)
- work: Work economy (create, submit, dispute)
- witness: Witness protocol commands
- status: System health and agent status
- model: Switch AI models

Integration:
- Engine: sos.clients.engine.EngineClient
- Bus: sos.services.bus.core.get_bus()
- Economy: sos.services.economy.ledger.get_ledger()

Philosophy:
"Adapters transform user intent into standardized Bus Messages.
They never execute logic themselves."

Usage:
    python -m scopes.adapters.cli task list
    python -m scopes.adapters.cli status
    python -m scopes.adapters.cli witness pending
"""

from .cli_adapter import cli, CLIAdapter

__all__ = ["cli", "CLIAdapter"]
