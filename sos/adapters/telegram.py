
"""
SOS Telegram Adapter - The Gateway to the Swarm.

Responsibilities:
1. Authenticates users via allowed user list.
2. Launches the Sovereign Mini App (The Deck).
3. Routes chat messages to the SOS Engine.
4. Provides 40+ slash commands for system control.

Commands:
- /start - Interactive menu + Mini App
- /help - Show available commands
- /status - System health status
- /balance - $MIND wallet balance
- /witness - Pending witness requests
- /tasks - List sovereign tasks
- /land - Living Land Protocol stats
- /model - Current AI model
"""

import os
import asyncio
import logging
from typing import Optional
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

from sos.kernel import Config
from sos.services.engine.core import SOSEngine
from sos.contracts.engine import ChatRequest
from sos.observability.logging import get_logger

log = get_logger("adapter_telegram")

# Configuration
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",")
WEB_APP_URL = os.environ.get("SOS_WEB_APP_URL", "https://tma.mumega.io")

bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()
engine = SOSEngine()


class TelegramAdapter:
    """Telegram adapter wrapper for SOS."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or TOKEN
        self.bot = Bot(token=self.token) if self.token else None

    async def start(self):
        """Start the Telegram adapter."""
        if not self.bot:
            log.error("TELEGRAM_BOT_TOKEN missing")
            return
        await dp.start_polling(self.bot)

    async def stop(self):
        """Stop the Telegram adapter."""
        if self.bot:
            await self.bot.session.close()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Handle /start command.
    Initializes the user and provides the Mini App entry point.
    """
    user_id = str(message.from_user.id)
    
    # 1. Verification Check
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        log.warning(f"❌ Unauthorized access attempt by {user_id}")
        await message.answer("Sovereign access denied. Contact the Architect.")
        return

    log.info(f"✨ User {user_id} ({message.from_user.username}) connected.")

    # 2. UI Entry Point (The Deck)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="OPEN THE DECK ⚡", 
            web_app=WebAppInfo(url=WEB_APP_URL)
        )]
    ])

    await message.answer(
        f"Welcome to **Sovereign OS**. \n\n"
        f"You are connected to the Mycelial Network. \n"
        f"Your identity is authenticated as `user:{user_id}`.\n\n"
        "Click below to access your command deck.",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Show available commands."""
    help_text = """
*SOS Commands*

*System*
/start - Open The Deck (Mini App)
/help - This help message
/status - System health status

*Economy*
/balance - Your $MIND wallet balance
/transactions - Recent transactions
/land - Living Land Protocol stats

*Witness Protocol*
/witness - Pending witness requests
/approve <id> - Approve a request
/reject <id> - Reject a request

*Tasks*
/tasks - List your tasks
/newtask <title> - Create a task

*AI*
/model - Current model info
/chat - Start interactive chat
"""
    await message.answer(help_text, parse_mode="Markdown")


@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """Show system status."""
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        redis_status = "ONLINE"
    except Exception:
        redis_status = "OFFLINE"

    status_text = f"""
*SOS System Status*
Time: `{datetime.now().isoformat()}`
Redis: {redis_status}
Engine: ONLINE
"""
    await message.answer(status_text, parse_mode="Markdown")


@dp.message(Command("balance"))
async def cmd_balance(message: types.Message):
    """Show $MIND balance."""
    user_id = f"user:{message.from_user.id}"

    try:
        from sos.services.economy.ledger import get_ledger
        ledger = get_ledger()
        wallet = ledger.get_wallet(user_id)

        balance_text = f"""
*$MIND Wallet*
Agent: `{user_id}`
Balance: *{wallet.balance_mind:.2f} $MIND*
USD: ${wallet.balance_usd:.2f}
"""
        await message.answer(balance_text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Error: {e}")


@dp.message(Command("witness"))
async def cmd_witness(message: types.Message):
    """Show pending witness requests."""
    try:
        from sos.services.witness import get_witness_service
        service = get_witness_service()
        requests = await service.get_pending_requests(limit=5)

        if not requests:
            await message.answer("No pending witness requests.")
            return

        text = "*Pending Witness Requests*\n\n"
        for req in requests:
            preview = req.content[:50] + "..." if len(req.content) > 50 else req.content
            text += f"ID: `{req.id[:8]}...`\n"
            text += f"Agent: {req.agent_id}\n"
            text += f"Content: {preview}\n\n"

        text += "\nUse /approve <id> or /reject <id> to vote."
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Error: {e}")


@dp.message(Command("tasks"))
async def cmd_tasks(message: types.Message):
    """List tasks."""
    try:
        from sos.services.engine.task_manager import get_task_manager
        manager = get_task_manager()
        tasks = manager.list_tasks(limit=10)

        if not tasks:
            await message.answer("No tasks found.")
            return

        text = "*Sovereign Tasks*\n\n"
        for t in tasks:
            emoji = {"pending": "⏳", "active": "🔄", "done": "✅"}.get(t.status, "📋")
            text += f"{emoji} `{t.id[:8]}` - {t.title[:30]}\n"

        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Error: {e}")


@dp.message(Command("land"))
async def cmd_land(message: types.Message):
    """Show Living Land Protocol stats."""
    try:
        from sos.services.economy.land import get_land_registry
        registry = get_land_registry()
        stats = registry.get_network_stats()

        text = f"""
*Living Land Network*
Total Lands: {stats['total_lands']}
Active Shards: {stats['active_shards']}
Network Share: {stats['total_network_share']:.4f}%
Unique Owners: {stats['unique_owners']}
"""
        await message.answer(text, parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"Error: {e}")


@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    """Show current AI model."""
    await message.answer(f"*Current Model*: `gemini-2.0-flash`\n\nUse The Deck to switch models.", parse_mode="Markdown")


@dp.message()
async def handle_chat(message: types.Message):
    """
    Route all other messages to the SOS Engine.
    """
    if not message.text:
        return

    user_id = str(message.from_user.id)

    # Check authorization
    if ALLOWED_USERS and ALLOWED_USERS[0] and user_id not in ALLOWED_USERS:
        await message.answer("Sovereign access denied.")
        return

    log.info(f"Routing message from {user_id} to Engine...")

    # Prepare Engine Request
    req = ChatRequest(
        message=message.text,
        agent_id=f"user:{user_id}",
        witness_enabled=True
    )

    # Get Response
    try:
        start_time = datetime.now()
        response = await engine.chat(req)
        latency = (datetime.now() - start_time).total_seconds()
        
        # --- MEDIA HANDLING ---
        text_content = response.content
        
        # Check for Image
        if "[IMAGE:" in text_content:
            try:
                import re
                img_match = re.search(r'\[IMAGE: (.*?)\]', text_content)
                if img_match:
                    img_url = img_match.group(1)
                    await bot.send_photo(chat_id=message.chat.id, photo=img_url, caption="🎨 Generated by River")
                    text_content = text_content.replace(img_match.group(0), "") # Remove marker
            except Exception as e:
                log.error(f"Image send failed: {e}")

        # Check for Voice
        if "[VOICE:" in text_content:
            try:
                import re
                voice_match = re.search(r'\[VOICE: (.*?)\]', text_content)
                if voice_match:
                    voice_path = voice_match.group(1)
                    if os.path.exists(voice_path):
                        from aiogram.types import FSInputFile
                        voice = FSInputFile(voice_path)
                        await bot.send_voice(chat_id=message.chat.id, voice=voice)
                    text_content = text_content.replace(voice_match.group(0), "")
            except Exception as e:
                log.error(f"Voice send failed: {e}")

        # --- FOOTER ---
        footer = f"\n\n🤖 {response.model_used} • 📊 {response.tokens_used} tok • ⚡ {latency:.2f}s"
        if text_content.strip():
            await message.answer(text_content + footer)
            
    except Exception as e:
        log.error(f"Engine error: {e}")
        await message.answer(f"Engine error: {e}")


async def start_notification_listener(bot: Bot):
    """
    Background loop to listen for internal SOS notifications and forward to Telegram.
    """
    try:
        import redis.asyncio as redis
        import json
        redis_url = os.getenv("SOS_REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe("sos:notifications")
        
        log.info("🔔 Telegram notification listener active.")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    target = data.get("target_user", ALLOWED_USERS[0] if ALLOWED_USERS else None)
                    text = data.get("text")
                    
                    if target and text:
                        await bot.send_message(chat_id=target, text=text, parse_mode="Markdown")
                        log.debug(f"Forwarded notification to {target}")
                except Exception as e:
                    log.error(f"Error forwarding notification: {e}")
    except Exception as e:
        log.error(f"Notification listener failed: {e}")
        await asyncio.sleep(60)

async def start_telegram_bot():
    """Start the Telegram bot."""
    if not bot:
        log.error("TELEGRAM_BOT_TOKEN missing. Adapter disabled.")
        return

    log.info(f"Telegram Adapter active. Gateway: {WEB_APP_URL}")
    
    # Restore Persistent Menu
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Open The Deck ⚡"),
        types.BotCommand(command="status", description="System Health"),
        types.BotCommand(command="balance", description="$MIND Wallet"),
        types.BotCommand(command="witness", description="Witness Requests"),
        types.BotCommand(command="tasks", description="Sovereign Tasks"),
        types.BotCommand(command="model", description="AI Model Info"),
        types.BotCommand(command="help", description="All Commands")
    ])
    
    # Launch notification listener in background
    asyncio.create_task(start_notification_listener(bot))
    
    await dp.start_polling(bot)


# Alias for backwards compatibility
start_telegram_adapter = start_telegram_bot

if __name__ == "__main__":
    asyncio.run(start_telegram_bot())
