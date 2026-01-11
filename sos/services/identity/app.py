from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from sos import __version__
from sos.services.identity.core import IdentityCore, GuildPass

app = FastAPI(title="SOS Identity Service", version=__version__)
identity = IdentityCore()

class MintRequest(BaseModel):
    agent_id: str
    role: str = "Apprentice"
    edition: str = "Standard"

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/mint", response_model=Dict[str, Any])
async def mint_pass(req: MintRequest):
    try:
        qnft = await identity.mint_guild_pass(req.agent_id, req.role, req.edition)
        return {
            "status": "success",
            "token_id": qnft.token_id,
            "pass_data": qnft.metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
