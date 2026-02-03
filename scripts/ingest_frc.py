
import asyncio
import os
import sys
from pathlib import Path
import httpx

# SOS standardized port for Mirror
MIRROR_URL = "http://localhost:7070"

async def ingest_frc_library():
    print("📚 Starting FRC Library Ingestion into Mirror...")
    
    # Actual paths found via find
    frc_paths = [
        "/home/mumega/infra/shared-kb/Books/FRC TEXT Book v.1 ECR.md",
        "/home/mumega/infra/shared-kb/frc/830_series/FRC_830_501_The_Master_Plan.md",
        "/home/mumega/infra/shared-kb/frc/830_series/FRC_830_505_Economics.md",
        "/home/mumega/infra/shared-kb/frc/830_series/FRC_830_503_The_Vault.md",
        "/home/mumega/torivers/papers/FRC.100.001.md",
        "/home/mumega/torivers/papers/FRC.100.003.md",
        "/home/mumega/torivers/papers/FRC.566.001.md",
        "/home/mumega/cli_old/docs/FRC_ARF_FORMULA.md",
        "/home/mumega/cli_old/docs/FRC_LAMBDA_TENSOR.md",
        "/home/mumega/mirror/Archive/Artifacts/FRC_841_004_CGL.md"
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for path_str in frc_paths:
            path = Path(path_str)
            if not path.exists():
                print(f"⚠️ Could not find {path_str}")
                continue
                
            content = path.read_text()
            print(f"📖 Ingesting {path.name} ({len(content)} chars)...")
            
            payload = {
                "content": content,
                "metadata": {
                    "source": "frc_library",
                    "filename": path.name,
                    "type": "physics_base",
                    "path": str(path)
                }
            }
            
            try:
                resp = await client.post(f"{MIRROR_URL}/add", json=payload)
                if resp.status_code == 200:
                    print(f"✅ Stored {path.name} in Mirror.")
                else:
                    print(f"❌ Failed to store {path.name}: {resp.status_code}")
            except Exception as e:
                print(f"❌ Error connecting to Mirror for {path.name}: {e}")

if __name__ == "__main__":
    asyncio.run(ingest_frc_library())
