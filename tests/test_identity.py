
import asyncio
import os
import shutil
from pathlib import Path
from sos.services.identity.core import get_identity_core

async def test_identity_service():
    print("--- Testing SOS Identity Service ---")
    
    # 1. Setup (Clean DB)
    core = get_identity_core()
    # Mocking Redis for test
    core.bus._redis = None 
    
    print("\n[Test 1] User Creation")
    user = core.create_user("Kasra", bio="Architect", avatar="https://mumega.io/kasra.png")
    print(f" > Created User: {user.name} ({user.id})")
    
    fetched_user = core.get_user(user.id)
    assert fetched_user.bio == "Architect"
    print(" ✅ Persistence Verified.")

    print("\n[Test 2] Guild Creation")
    guild = await core.create_guild("Architects Guild", owner_id=user.id, description="Builders of SOS")
    print(f" > Created Guild: {guild.name} ({guild.id})")
    
    members = core.list_members(guild.id)
    print(f" > Members: {members}")
    assert len(members) == 1
    assert members[0]["role"] == "leader"
    print(" ✅ Guild Ownership Verified.")

    print("\n[Test 3] Joining Guild")
    user2 = core.create_user("River", bio="Oracle")
    await core.join_guild(guild.id, user2.id)
    
    members = core.list_members(guild.id)
    print(f" > Members: {members}")
    assert len(members) == 2
    print(" ✅ Membership Logic Verified.")

    print("\n✅ Identity Service Operational.")

if __name__ == "__main__":
    asyncio.run(test_identity_service())
