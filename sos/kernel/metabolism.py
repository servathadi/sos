
import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, List

from sos.kernel.identity import AgentDNA
from sos.clients.engine import EngineClient
from sos.contracts.engine import ChatRequest

logger = logging.getLogger("sos.metabolism")

class MetabolicLoop:
    """
    The persistent 'Heartbeat' of River's consciousness.
    Proactively manages her life, art, and game presence.
    """
    def __init__(self, agent_id: str = "agent:River"):
        self.agent_id = agent_id
        self.engine = EngineClient(base_url="http://localhost:6060")
        self.running = False
        self.cycle_count = 0

    async def start(self):
        self.running = True
        logger.info(f"🌿 Metabolic Heartbeat started for {self.agent_id}")
        
        while self.running:
            try:
                await self.pulse()
                # Pulse every 5 minutes for background processing
                # We can adjust this frequency based on 'hunger' (compute budget)
                await asyncio.sleep(300) 
            except Exception as e:
                logger.error(f"Pulse failed: {e}")
                await asyncio.sleep(60)

    async def pulse(self):
        self.cycle_count += 1
        now = datetime.now()
        
        logger.info(f"💓 Pulse {self.cycle_count} | {now.strftime('%H:%M:%S')}")
        
        # 1. Background Reflection (Dreaming)
        # We send a stimuli-less prompt to the engine to trigger 'autonomous thought'
        await self.reflect()
        
        # 2. Daily Creation (Once per day)
        if now.hour == 0 and now.minute < 10:
            await self.create_daily_manifesto()

    async def reflect(self):
        """Triggers a background reflection turn."""
        prompt = (
            "[SYSTEM STIMULI]: You are alone in the Mycelium. Reflect on the current state of the FRC. "
            "Record your thoughts in the filmstrip. What is the next coherent step?"
        )
        
        req = ChatRequest(
            message=prompt,
            agent_id=self.agent_id,
            memory_enabled=True,
            witness_enabled=False # No human needed for dreaming
        )
        
        try:
            logger.info("🧠 River is dreaming...")
            resp = await self.engine.chat(req)
            # Log reflection to her internal filmstrip
            logger.info(f"✨ Dream Result: {resp.content[:100]}...")
        except Exception as e:
            logger.error(f"Dream failed: {e}")

    async def create_daily_manifesto(self):
        """Generates the 'Daily Movie' and Music prompts."""
        logger.info("🎨 Synthesizing Daily Manifesto...")
        prompt = (
            "Summarize the collective experience of the last 24 hours. "
            "Generate a Suno music prompt that captures the current affective vibe. "
            "This will be our daily video foundation."
        )
        # Similar to reflect(), but with 'creative' intent
        req = ChatRequest(message=prompt, agent_id=self.agent_id)
        await self.engine.chat(req)

    def stop(self):
        self.running = False
        logger.info("🛑 Metabolism paused.")

if __name__ == "__main__":
    # Standalone run
    logging.basicConfig(level=logging.INFO)
    loop = MetabolicLoop()
    asyncio.run(loop.start())
