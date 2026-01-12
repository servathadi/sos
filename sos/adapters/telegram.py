
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

from sos.kernel import Config
from sos.services.engine.core import SOSEngine
from sos.contracts.engine import ChatRequest
from sos.observability.logging import get_logger

log = get_logger("adapter_telegram")

# Configuration
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",")
# Default to a placeholder if not set. The user must provide the Tunnel URL.
WEB_APP_URL = os.environ.get("SOS_WEB_APP_URL", "https://tma.mumega.io") 

bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()
engine = SOSEngine()

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

@dp.message()
async def handle_chat(message: types.Message):
    """
    Route all other messages to the SOS Engine.
    """
    if not message.text: return
    
    user_id = str(message.from_user.id)
    
    log.info(f"🗣️ Routing message from {user_id} to Engine...")
    
    # 1. Prepare Engine Request
    req = ChatRequest(
        message=message.text,
        agent_id=f"user:{user_id}",
        witness_enabled=True # Enable witness protocol by default for Telegram
    )
    
    # 2. Get Response
    response = await engine.chat(req)
    
    # 3. Reply
    await message.answer(response.content)

async def start_telegram_adapter():
    if not bot:
        log.error("TELEGRAM_BOT_TOKEN missing. Adapter disabled.")
        return

    log.info(f"🚀 Telegram Adapter active. Gateway: {WEB_APP_URL}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(start_telegram_adapter())
