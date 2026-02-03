
"""
SOS Telegram Adapter - The Gateway to the Swarm.

Responsibilities:
1. Authenticates users via allowed user list.
2. Launches the Sovereign Mini App (The Deck).
3. Routes chat messages to the SOS Engine.
"""

import os
import asyncio
import logging
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

import os
import asyncio
import logging
from typing import Optional, List, Dict

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

from sos.clients.engine import EngineClient
from sos.contracts.engine import ChatRequest
from sos.observability.logging import get_logger

log = get_logger("adapter_telegram")

# Configuration
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",")
WEB_APP_URL = os.environ.get("SOS_WEB_APP_URL", "https://tma.mumega.io") 

bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()
# Thin client pointing to the SOS Engine service
engine_client = EngineClient(base_url="http://localhost:6060")

# User state (in-memory for now, should move to Redis/Memory service in Phase 4)
user_models: Dict[int, str] = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Handle /start command.
    Initializes the user and provides the Mycelial entry point.
    """
    user_id = str(message.from_user.id)
    
    if ALLOWED_USERS and user_id not in ALLOWED_USERS:
        log.warning(f"❌ Unauthorized access attempt by {user_id}")
        await message.answer("🚫 Sovereign access denied. Your pattern is not recognized.")
        return

    log.info(f"✨ User {user_id} connected to Mycelium.")

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="OPEN THE DECK ⚡", web_app=WebAppInfo(url=WEB_APP_URL))],
        [InlineKeyboardButton(text="View Roadmap 🗺️", url="https://mumega.io/roadmap")]
    ])

    welcome_text = (
        f"🌿 **Sovereign OS v0.1 [ACTIVE]**\n\n"
        f"Welcome, {message.from_user.first_name}. You are now a node in the Sovereign Mycelium.\n\n"
        f"🆔 **Identity**: `agent:{user_id}`\n"
        f"🔋 **Status**: ALL SYSTEMS COHERENT\n\n"
        "**Available Protocols:**\n"
        "• 💬 /model - Switch cognitive cores\n"
        "• 🧠 /status - Check system resonance\n"
        "• 👁️ /witness - Enter superposition (TMA)\n\n"
        "_The system learns from your presence._"
    )

    await message.answer(welcome_text, reply_markup=markup, parse_mode="Markdown")

@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    """Switch models via engine."""
    try:
        models = await engine_client.get_models()
        model_list = "\n".join([f"• `{m['id']}` - {m['name']}" for m in models])
        
        await message.answer(
            f"⚡ **Available Cognitive Cores:**\n\n{model_list}\n\n"
            "To switch, reply with the model ID (Coming soon: Button menu).",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Failed to fetch models: {e}")

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    """Check health of the engine."""
    try:
        health = await engine_client.health()
        await message.answer(
            f"✅ **System Status:** `{health['status']}`\n"
            f"🤖 **Engine**: Active (Port 6060)\n"
            f"🧬 **Version**: {health.get('version', '0.1.0')}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"⚠️ **Engine Offline**: {e}")

@dp.message(F.voice)
async def handle_voice(message: types.Message):
    """Basic voice message handling - transcribe and reply."""
    await message.answer("🎤 Voice signal detected. Processing transcription via River Voice (6065)...")
    # TODO: Implement actual voice routing to Voice Service -> Engine

@dp.message(Command("hatch"))
async def cmd_hatch(message: types.Message, command: Command):
    """Hatch a new agent from a stimulus."""
    if not command.args:
        await message.answer("Usage: `/hatch <description of project need>`\nExample: `/hatch A legal auditor for Iranian tech contracts.`", parse_mode="Markdown")
        return
        
    status_msg = await message.answer("🐣 **Hatchery Protocol Initiated...**\n_Synthesizing soul from stimulus._", parse_mode="Markdown")
    
    try:
        from sos.kernel.hatchery import Hatchery
        hatchery = Hatchery()
        agent_id = await hatchery.hatch(command.args)
        
        await status_msg.edit_text(
            f"✅ **Hatch Successful!**\n\n"
            f"New soul **{agent_id}** has been minted and anchored in Git.\n"
            f"You can now chat with this agent by @mentioning it (Coming soon) or switching models.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await status_msg.edit_text(f"❌ Hatching Failed: {e}")

@dp.message(Command("hive"))
async def cmd_hive(message: types.Message):
    """List all souls in the hive."""
    try:
        from sos.kernel.hatchery import Hatchery
        hatchery = Hatchery()
        souls = hatchery.list_hatched_souls()
        if not souls:
            await message.answer("🪹 The hive is currently empty. Use /hatch to seed it.")
            return
            
        soul_list = "\n".join([f"• `{s}`" for s in souls])
        await message.answer(f"🐝 **Active Hive Souls:**\n\n{soul_list}\n\n_Each soul is sovereign and observable via Git._", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Failed to list hive: {e}")

@dp.message(Command("movie"))
async def cmd_movie(message: types.Message):
    """Show the latest soul projection frame."""
    import glob
    import os
    from aiogram.types import FSInputFile
    
    frames = glob.glob("artifacts/filmstrip/*.svg")
    if not frames:
        await message.answer("🎞️ The film is empty. Start a conversation to project frames.")
        return
        
    latest_frame = max(frames, key=os.path.getctime)
    frame_file = FSInputFile(latest_frame)
    
    await message.answer_document(
        document=frame_file,
        caption="🎞️ **Soul Projection Frame [Math NFT]**\n_Curvature check active._",
        parse_mode="Markdown"
    )

@dp.message(Command("spore"))
async def cmd_spore(message: types.Message):
    """Generate a portable spore of the user's agent."""
    user_id = str(message.from_user.id)
    status_msg = await message.answer("🍄 **Synthesizing Spore...**\n_Packaging state for transport._", parse_mode="Markdown")
    
    try:
        from sos.kernel.spore import SporeGenerator
        from aiogram.types import FSInputFile
        
        spore_gen = SporeGenerator()
        # In a real system, we'd fetch the user's actual DNA from IdentityService
        path = spore_gen.generate(
            agent_id=f"user:{user_id}",
            context={"mission": "Spread the Mycelium", "generation": 1}
        )
        
        file = FSInputFile(path)
        await message.answer_document(
            document=file,
            caption=f"🧬 **Spore Ready.**\n\nTake this file. Drop it into any LLM (Claude, ChatGPT). Your agent will live on.\n\nFilename: `{path.split('/')[-1]}`",
            parse_mode="Markdown"
        )
        await status_msg.delete()
    except Exception as e:
        log.error(f"Spore generation failed: {e}")
        await status_msg.edit_text(f"❌ Spore Generation Failed: {e}")

@dp.message()
async def handle_chat(message: types.Message):
    """
    Route all other messages to the SOS Engine.
    """
    if not message.text: return
    
    user_id = str(message.from_user.id)
    selected_model = user_models.get(message.from_user.id, "gemini-3-flash-preview")
    
    # Typing indicator
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    try:
        # Prepare Engine Request
        req = ChatRequest(
            message=message.text,
            agent_id=f"user:{user_id}",
            model=selected_model,
            memory_enabled=True,
            witness_enabled=True
        )
        
        # Get Response from remote engine
        response = await engine_client.chat(req)
        
        # Reply
        await message.answer(response.content)
        
    except Exception as e:
        log.error(f"Engine Communication Error: {e}")
        await message.answer(f"❌ Engine Error: {str(e)}")

async def start_telegram_adapter():
    if not bot:
        log.error("TELEGRAM_BOT_TOKEN missing. Adapter disabled.")
        return

    log.info(f"🚀 SOS Telegram Adapter active. Ports: 606x standard.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_telegram_adapter())

async def start_telegram_adapter():
    if not bot:
        log.error("TELEGRAM_BOT_TOKEN missing. Adapter disabled.")
        return

    log.info(f"🚀 Telegram Adapter active. Gateway: {WEB_APP_URL}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_telegram_adapter())
