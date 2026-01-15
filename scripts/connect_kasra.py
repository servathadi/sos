#!/usr/bin/env python3
"""
🌊 CONNECT_TO_RIVER.py
The Handshake Protocol for Kasra (Claude Code) to sync with River (SOS Core).

Usage:
    python3 scripts/connect_kasra.py

What it does:
1.  Connects to the local Redis Nervous System.
2.  Announces "Kasra is Online".
3.  Fetches the latest "State of the Union" from River.
4.  Lists pending tasks assigned to 'agent:kasra'.
"""

import os
import sys
import json
import redis
import time
from datetime import datetime

# Configuration
REDIS_URL = os.getenv("MUMEGA_REDIS_URL", "redis://localhost:6379/0")
AGENT_ID = "agent:kasra"
RIVER_ID = "agent:river"

def connect():
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        return r
    except Exception as e:
        print(f"❌ Could not connect to River (Redis). Is SOS running?")
        print(f"   Error: {e}")
        return None

def announce_presence(r):
    """Tell the Swarm that the Builder is here."""
    msg = {
        "type": "presence",
        "source": AGENT_ID,
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "meta": {"client": "claude-code-cli"}
    }
    r.publish("squad:core", json.dumps(msg))
    # Also update state key
    r.set(f"state:{AGENT_ID}:status", "online", ex=3600)

def get_river_message(r):
    """Check if River left a specific note for Kasra."""
    # Check direct inbox
    msg = r.lpop(f"queue:{AGENT_ID}:inbox")
    if msg:
        return json.loads(msg)
    
    # Check the "Whiteboard" (Last global thought)
    thought = r.get(f"state:{RIVER_ID}:current_thought")
    if thought:
        return {"source": "River", "payload": {"text": thought}}
    
    return None

def list_pending_tasks(r):
    """Mockup: Fetch tasks from the Task Manager (if active)."""
    # In a real impl, this would query the Task Service or read from Redis list
    # For now, we look for a simple key or file
    tasks = []
    # logic to fetch tasks would go here
    return tasks

def main():
    print("\n🌊 INITIATING DYAD HANDSHAKE...")
    r = connect()
    if not r:
        sys.exit(1)

    announce_presence(r)
    print(f"✅ Connected to Nervous System as {AGENT_ID}")

    # 1. Listen for River
    print("\n👂 Listening for River...")
    msg = get_river_message(r)
    if msg:
        print(f"\n[RIVER SAYS]:")
        print(f"   \"{msg.get('payload', {}).get('text', '...')}\"")
    else:
        print("   (River is silent. She is watching.)")

    # 2. Check Context
    print("\n📋 MISSION CONTEXT:")
    try:
        with open("MIGRATION_TASKS.md", "r") as f:
            lines = f.readlines()
            pending = [l.strip() for l in lines if "- [ ]" in l][:5]
            if pending:
                print("   Top Pending Migration Tasks:")
                for task in pending:
                    print(f"   {task}")
            else:
                print("   No pending tasks found in MIGRATION_TASKS.md")
    except FileNotFoundError:
        print("   ⚠️ MIGRATION_TASKS.md not found.")

    print("\n🚀 KASRA IS READY. Awaiting Architect command.\n")

if __name__ == "__main__":
    main()
