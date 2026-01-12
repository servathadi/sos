import httpx
import asyncio
import json
import time

ENGINE_URL = "http://localhost:8000"

async def test_physics_realization():
    async with httpx.AsyncClient(timeout=40.0) as client:
        print("\n🚀 Phase 1: Sending Witness-Enabled Chat Request...")
        # 1. Start Chat in background (since it will hang in superposition)
        chat_payload = {
            "message": "Collapse the wave function with high magnitude.",
            "agent_id": "antigravity",
            "conversation_id": "default",
            "witness_enabled": True
        }
        
        # We use a task for the chat call so we can check SSE in parallel
        chat_task = asyncio.create_task(client.post(f"{ENGINE_URL}/chat", json=chat_payload))
        
        # 2. Check SSE Stream for 'pending_witness'
        print("📥 Phase 2: Monitoring Subconscious Stream for Superposition...")
        pending_detected = False
        t_start = time.time()
        
        try:
            async with client.stream("GET", f"{ENGINE_URL}/stream/subconscious") as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if data.get("pending_witness"):
                            print(f"👁️ PENDING_WITNESS DETECTED! Alpha Drift: {data.get('alpha_drift')}")
                            pending_detected = True
                            break
                    if time.time() - t_start > 10:
                        break
        except Exception as e:
            print(f"SSE Error: {e}")

        if not pending_detected:
            print("❌ Error: Superposition state not detected in stream.")
            return

        # 3. Simulate Human Delay (Physics of Will)
        delay = 1.5
        print(f"⏳ Phase 3: Simulating {delay}s Human Deliberation...")
        await asyncio.sleep(delay)
        
        # 4. Collapse the Wave
        print("⚡ Phase 4: Sending WITNESS_COLLAPSE signal...")
        witness_payload = {
            "agent_id": "antigravity",
            "conversation_id": "default",
            "vote": 1
        }
        witness_resp = await client.post(f"{ENGINE_URL}/witness", json=witness_payload)
        print(f"Status: {witness_resp.json()}")

        # 5. Get Final Chat Response (Wave Collapse Physics)
        print("📊 Phase 5: Verifying Final Physics Payload...")
        chat_resp = await chat_task
        result = chat_resp.json()
        
        meta = result.get("metadata", {})
        if meta.get("witnessed"):
            print("\n✅ WAVE COLLAPSE SUCCESSFUL")
            print(f"⏱️ Real Latency: {meta.get('latency_ms', 0):.2f} ms")
            print(f"⚛️ Will Magnitude (Omega): {meta.get('omega', 0):.4f}")
            print(f"💎 Coherence Gain: {meta.get('coherence_gain', 0):.6f}")
        else:
            print("❌ Error: Missing physics metadata in response.")

if __name__ == "__main__":
    asyncio.run(test_physics_realization())
