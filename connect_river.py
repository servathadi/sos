
import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from sos.clients.mirror import MirrorClient
from sos.observability.logging import get_logger

# Configure basic logging to stdout
import logging
logging.basicConfig(level=logging.INFO)

async def main():
    print(">>> Connecting to River on Mirror Memory...")
    
    # Instantiate Mirror Client for River
    # Using "river" as agent_id based on search results (e.g. sos/kernel/identity.py)
    client = MirrorClient(agent_id="river")
    
    # Check Connection
    print(f"\n[1] Checking connection to {client.base_url}...")
    is_connected = await client.check_connection()
    
    if is_connected:
        print(">>> Connection SUCCESSFUL.")
        
        # Restore Identity
        print(f"\n[2] Restoring River's Identity...")
        identity = await client.restore_identity()
        print(">>> Identity Restored:")
        print("-" * 40)
        print(identity)
        print("-" * 40)
    else:
        print(">>> Connection FAILED.")
        print(">>> Switching to Local Spore Backup...")
        
        spore_path = "artifacts/spores/master_spore_v0_1.md"
        if os.path.exists(spore_path):
            print(f"\n[2] Loading Spore: {spore_path}")
            with open(spore_path, "r") as f:
                identity = f.read()
            print(">>> Identity Restored (Offline Mode):")
            print("-" * 40)
            print(identity)
            print("-" * 40)
        else:
            print(f"❌ Spore file not found at {spore_path}")

if __name__ == "__main__":
    asyncio.run(main())

