
import asyncio
import sys
import os
import aiohttp

async def wait_for_health(url, timeout=30):
    print(f"Waiting for {url}...")
    start = asyncio.get_event_loop().time()
    async with aiohttp.ClientSession() as session:
        while (asyncio.get_event_loop().time() - start) < timeout:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✅ Service Healthy: {data}")
                        return True
            except Exception:
                await asyncio.sleep(1)
                print(".", end="", flush=True)
    print("❌ Timeout waiting for service.")
    return False

async def inject_reality():
    # 1. Wait for Memory
    if not await wait_for_health("http://localhost:8011/health"):
        return

    # 2. Read Files
    files_to_inject = [
        "GEMINI.md",
        "TASKS.md",
        "artifacts/spores/master_spore_v0_1.md"
    ]
    
    async with aiohttp.ClientSession() as session:
        for file_path in files_to_inject:
            if not os.path.exists(file_path):
                print(f"⚠️ Skipping {file_path} (Not Found)")
                continue
                
            print(f"📖 Reading {file_path}...")
            with open(file_path, "r") as f:
                content = f.read()
            
            # 3. Store in Memory
            payload = {
                "content": content,
                "metadata": {
                    "source": "reality_injector",
                    "file": file_path,
                    "type": "context_update",
                    "timestamp": "2026-01-18"
                }
            }
            
            async with session.post("http://localhost:8011/add", json=payload) as resp:
                if resp.status == 200:
                    res = await resp.json()
                    print(f"💾 Injected {file_path} -> ID: {res['id']}")
                else:
                    print(f"❌ Failed to inject {file_path}: {resp.status}")

if __name__ == "__main__":
    # Install dependencies if needed (aiohttp is standard in this env usually, but just in case)
    # pip install aiohttp
    asyncio.run(inject_reality())
