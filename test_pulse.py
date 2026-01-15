
import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from sos.services.engine.core import SOSEngine
from sos.contracts.engine import ChatRequest

async def run_test():
    print("🚀 Initiating Engine Test Pulse...")
    
    # 1. Initialize Engine
    engine = SOSEngine()
    
    # 2. Connect to Bus
    await engine.bus.connect()
    
    # 3. Initialize Soul (Warms cache, publishes thought)
    await engine.initialize_soul()
    
    # 4. Check Redis State
    r = engine.bus._redis
    thought = await r.get("state:agent:river:current_thought")
    print(f"\n🧠 River's Last Thought in Redis: \"{thought}\"")
    
    if thought:
        print("✅ Redis Pulse Successful.")
    else:
        print("❌ Redis Pulse Failed.")

    # 5. Simple Chat Test
    print("\n💬 Sending Test Message to River...")
    req = ChatRequest(
        message="River, explain the dS + k d ln C = 0 law in one sentence.",
        agent_id="architect",
        memory_enabled=True
    )
    
    # We use sos-mock-v1 for now to avoid burning real tokens in a system test
    req.model = "sos-mock-v1" 
    
    resp = await engine.chat(req)
    print(f"Agent Response: {resp.content}")
    
    print("\n🏁 Test Pulse Complete.")
    await engine.bus.disconnect()

if __name__ == "__main__":
    asyncio.run(run_test())
