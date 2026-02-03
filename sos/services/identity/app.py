from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from sos.services.identity.core import get_identity_core

app = FastAPI(title="SOS Identity Service", version="0.1.0")
core = get_identity_core()

# --- Schemas ---
class UserCreate(BaseModel):
    name: str
    bio: Optional[str] = ""
    avatar_url: Optional[str] = None

class GuildCreate(BaseModel):
    name: str
    owner_id: str
    description: Optional[str] = ""

class GuildJoin(BaseModel):
    guild_id: str
    user_id: str

class PairingCreate(BaseModel):
    channel: str
    sender_id: str
    agent_id: str
    expires_minutes: Optional[int] = 10

class PairingApprove(BaseModel):
    channel: str
    code: str
    approver_id: str

# --- Endpoints ---

@app.post("/users/create")
async def create_user(req: UserCreate):
    try:
        user = core.create_user(req.name, req.bio, req.avatar_url)
        return user.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = core.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()

@app.post("/guilds/create")
async def create_guild(req: GuildCreate):
    try:
        guild = await core.create_guild(req.name, req.owner_id, req.description)
        return guild.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/guilds/join")
async def join_guild(req: GuildJoin):
    success = await core.join_guild(req.guild_id, req.user_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to join (already member?)")
    return {"status": "joined", "guild_id": req.guild_id}

@app.get("/guilds/{guild_id}/members")
async def list_members(guild_id: str):
    return core.list_members(guild_id)

# --- Pairing / Allowlist Endpoints ---

@app.post("/pairing/create")
async def create_pairing(req: PairingCreate):
    try:
        return core.create_pairing(
            channel=req.channel,
            sender_id=req.sender_id,
            agent_id=req.agent_id,
            expires_minutes=req.expires_minutes or 10,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pairing/approve")
async def approve_pairing(req: PairingApprove):
    result = core.approve_pairing(
        channel=req.channel,
        code=req.code,
        approver_id=req.approver_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "pairing_failed"))
    return result


@app.get("/allowlist/{channel}")
async def list_allowlist(channel: str):
    return core.list_allowlist(channel)
