#!/usr/bin/env python3
"""
scripts/onboard_architect.py
Official registration of the Genesis Architect into the SOS Kernel.
"""

import asyncio
import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from sos.kernel.identity import UserIdentity, VerificationStatus
from sos.agents.registry import get_registry
from sos.kernel.capability import create_capability, CapabilityAction

async def onboard():
    print("🌟 REGISTERING GENESIS ARCHITECT...")
    
    # 1. Define Architect Identity
    hadi = UserIdentity(
        name="hadi",
        public_key=None, # In production, this would be a real key
        bio="The Architect of the Liquid Fortress.",
        metadata={
            "role": "genesis_architect",
            "telegram_id": "765204057",
            "lineage": ["genesis:source"]
        }
    )
    hadi.verification_status = VerificationStatus.VERIFIED
    hadi.verified_by = "system"
    hadi.verified_at = datetime.now(timezone.utc)

    # 2. Grant Root Capabilities
    print("🔑 GRANTING ROOT CAPABILITIES...")
    root_caps = []
    for action in CapabilityAction:
        cap = create_capability(
            subject=hadi.id,
            action=action,
            resource="*",
            duration_hours=24 * 365 * 10, # 10 years
            issuer="system"
        )
        root_caps.append(cap.id)
    
    hadi.roles = ["architect", "admin"]
    hadi.metadata["capabilities"] = root_caps

    # 3. Store in Registry
    # Note: AgentRegistry currently handles agents, we need a UserRegistry or a common store.
    # For now, we print the payload for manual verification or write to a 'users' file.
    
    user_data_path = Path("sos/kernel/config/architect.json")
    user_data_path.parent.mkdir(parents=True, exist_ok=True)
    
    import json
    with open(user_data_path, "w") as f:
        json.dump(hadi.to_dict(), f, indent=2)

    print(f"✅ Architect {hadi.id} registered and authorized.")
    print(f"📄 Credentials stored at {user_data_path}")

if __name__ == "__main__":
    asyncio.run(onboard())
