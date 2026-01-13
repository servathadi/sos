"""
Telegram Adapter Scope - Bot Interface for SOS

This scope implements the Telegram bot adapter using aiogram.
Transforms Telegram messages into Bus Messages.

Commands (40+):
- /start - Interactive menu
- /help - Display help
- /status - System status
- /model - Switch AI model
- /balance - $MIND balance
- /witness - Witness protocol
- /tasks - Task management
- /land - Living Land Protocol

Integration:
- Engine: sos.services.engine.core.SOSEngine
- Bus: sos.services.bus.core.get_bus()
- Economy: sos.services.economy.ledger.get_ledger()
- Witness: sos.services.witness.get_witness_service()

Philosophy:
"Adapters transform user intent into standardized Bus Messages.
They never execute logic themselves."

See sos/adapters/telegram.py for core implementation.
"""

from sos.adapters.telegram import TelegramAdapter, start_telegram_bot

__all__ = ["TelegramAdapter", "start_telegram_bot"]
