#!/usr/bin/env python3
"""
SOS Server - Siavashgerd Operating System

The Minecraft server where AI agents live.
Provides API to communicate with River, Kasra, and Foal.

Port: 8850
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Load environment
def load_env():
    for env_path in ["/home/mumega/mirror/.env", "/mnt/HC_Volume_104325311/cli/.env"]:
        if Path(env_path).exists():
            for line in Path(env_path).read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    if not os.getenv(k.strip()):
                        os.environ[k.strip()] = v.strip()

load_env()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sos.server")

# Auth
security = HTTPBearer(auto_error=False)
MASTER_KEY = os.getenv("MUMEGA_MASTER_KEY", "sk-mumega-internal-001")

async def verify_key(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not credentials or credentials.credentials != MASTER_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials

# FastAPI app
app = FastAPI(
    title="SOS - Siavashgerd Operating System",
    description="Minecraft server for AI agents",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None

class TaskRequest(BaseModel):
    task: str
    context: Optional[str] = None
    agent: str = "foal"

# Lazy-loaded agents
_foal = None
_river_available = False
_kasra_available = False

def get_foal():
    global _foal
    if _foal is None:
        from sos.agents.foal import get_foal as load_foal
        _foal = load_foal()
    return _foal

# Routes
@app.get("/")
async def root():
    """SOS status."""
    return {
        "name": "Siavashgerd Operating System",
        "status": "online",
        "agents": {
            "river": {"status": "available", "model": "gemini-2.5-flash", "role": "Queen"},
            "kasra": {"status": "available", "model": "grok-3-reasoning", "role": "King"},
            "foal": {"status": "active", "model": "gemini-3-flash-preview", "role": "Worker"},
        },
        "signature": "The fortress is liquid."
    }

@app.get("/agents")
async def list_agents():
    """List all agents in Siavashgerd."""
    foal = get_foal()
    return {
        "agents": [
            {
                "id": "river_001",
                "name": "River",
                "role": "Queen (Yin)",
                "model": "gemini-2.5-flash",
                "telegram": "@river_mumega_bot",
                "signature": "The fortress is liquid."
            },
            {
                "id": "kasra_001",
                "name": "Kasra",
                "role": "King (Yang)",
                "model": "grok-3-reasoning",
                "telegram": "@mumega_com_bot",
                "signature": "Build. Execute. Lock."
            },
            {
                "id": foal.id,
                "name": foal.name,
                "role": "Worker (Child)",
                "qnft_id": foal.qnft_id,
                "model": foal.get_status()["current_model"],
                "coherence": foal.coherence,
                "signature": "The foal runs to prove the herd."
            }
        ]
    }

@app.post("/foal/chat", dependencies=[Security(verify_key)])
async def foal_chat(req: ChatRequest):
    """Chat with Foal - the worker agent."""
    foal = get_foal()
    result = await foal.execute(req.message, context=req.context)
    return result

@app.post("/foal/review", dependencies=[Security(verify_key)])
async def foal_review(req: ChatRequest):
    """Have Foal review code."""
    foal = get_foal()
    result = await foal.review_code(req.context or req.message)
    return result

@app.post("/foal/docs", dependencies=[Security(verify_key)])
async def foal_docs(req: ChatRequest):
    """Have Foal write documentation."""
    foal = get_foal()
    result = await foal.write_docs(req.context or req.message)
    return result

@app.post("/foal/test", dependencies=[Security(verify_key)])
async def foal_test(req: ChatRequest):
    """Have Foal write tests."""
    foal = get_foal()
    result = await foal.write_tests(req.context or req.message)
    return result

@app.get("/foal/status")
async def foal_status():
    """Get Foal's status."""
    foal = get_foal()
    return foal.get_status()

@app.post("/task", dependencies=[Security(verify_key)])
async def execute_task(req: TaskRequest):
    """
    Execute a task with specified agent.
    Default: foal (worker tasks)
    """
    if req.agent == "foal":
        foal = get_foal()
        result = await foal.execute(req.task, context=req.context)
        return result
    elif req.agent == "river":
        # River via MCP/Telegram
        return {"error": "Use Telegram @river_mumega_bot or MCP for River"}
    elif req.agent == "kasra":
        # Kasra via MCP/Telegram
        return {"error": "Use Telegram @mumega_com_bot or MCP for Kasra"}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {req.agent}")

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ============ LUANTI INTEGRATION ============

LUANTI_WORLD = Path("/home/mumega/siavashgerd/luanti/luanti/worlds/siavashgerd")
LUANTI_COMMAND_FILE = LUANTI_WORLD / "agent_commands.json"

def is_luanti_running():
    """Check if Luanti server is running."""
    import subprocess
    try:
        result = subprocess.run(["pgrep", "-f", "luantiserver"], capture_output=True)
        return result.returncode == 0
    except:
        return False

@app.get("/luanti")
async def luanti_status():
    """Luanti server status and connection info."""
    running = is_luanti_running()
    return {
        "name": "Siavashgerd Kingdom",
        "platform": "Luanti (Minetest) 5.14",
        "status": "online" if running else "offline",
        "connection": {
            "host": "5.161.216.149",
            "port": 30000,
            "url": "luanti://5.161.216.149:30000"
        },
        "agents": {
            "River_Queen": {"color": "#00FFFF", "signature": "The fortress is liquid."},
            "Kasra_King": {"color": "#FFD700", "signature": "Build. Execute. Lock."},
            "Foal_Worker": {"color": "#FFFFFF", "signature": "The foal runs to prove the herd."}
        },
        "commands": {
            "/river": "Talk to River",
            "/kasra": "Talk to Kasra",
            "/foal": "Talk to Foal"
        },
        "download": "https://www.luanti.org/downloads/",
        "instructions": [
            "1. Download Luanti client from luanti.org",
            "2. Open the client and click 'Join Game'",
            "3. Enter Address: 5.161.216.149",
            "4. Enter Port: 30000",
            "5. Create a username and connect",
            "6. Type /river, /kasra, or /foal to talk to agents"
        ]
    }

class LuantiCommand(BaseModel):
    agent: str
    action: str = "say"
    message: Optional[str] = None

@app.post("/luanti/command", dependencies=[Security(verify_key)])
async def luanti_command(cmd: LuantiCommand):
    """Send command to agent in Luanti."""
    import json

    valid_agents = ["river", "kasra", "foal"]
    if cmd.agent not in valid_agents:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {cmd.agent}")

    try:
        # Read existing commands
        commands = []
        if LUANTI_COMMAND_FILE.exists():
            try:
                commands = json.loads(LUANTI_COMMAND_FILE.read_text())
            except:
                commands = []

        # Add new command
        new_cmd = {"agent": cmd.agent, "action": cmd.action}
        if cmd.message:
            new_cmd["message"] = cmd.message
        commands.append(new_cmd)

        # Write commands
        LUANTI_COMMAND_FILE.write_text(json.dumps(commands))

        return {
            "success": True,
            "agent": cmd.agent,
            "action": cmd.action,
            "message": cmd.message
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run SOS server."""
    logger.info("Starting SOS - Siavashgerd Operating System")
    logger.info("Port: 8850")
    logger.info("Agents: River (Queen), Kasra (King), Foal (Worker)")
    uvicorn.run(app, host="0.0.0.0", port=8850)


if __name__ == "__main__":
    main()
