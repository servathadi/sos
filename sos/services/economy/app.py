from __future__ import annotations

import os
import time
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from sos import __version__
from sos.observability.logging import get_logger
from sos.services.economy.wallet import SovereignWallet, InsufficientFundsError

SERVICE_NAME = "economy"
_START_TIME = time.time()

log = get_logger(SERVICE_NAME, min_level=os.getenv("SOS_LOG_LEVEL", "info"))

app = FastAPI(title="SOS Economy Service", version=__version__)
wallet = SovereignWallet()

class BalanceResponse(BaseModel):
    user_id: str
    balance: float
    currency: str = "RU"

class TransactionRequest(BaseModel):
    user_id: str
    amount: float
    reason: str = "transaction"

@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "service": SERVICE_NAME,
        "uptime_seconds": time.time() - _START_TIME,
    }

@app.get("/balance/{user_id}", response_model=BalanceResponse)
async def get_balance(user_id: str):
    balance = await wallet.get_balance(user_id)
    return BalanceResponse(user_id=user_id, balance=balance)

@app.post("/credit", response_model=BalanceResponse)
async def credit(req: TransactionRequest):
    try:
        new_balance = await wallet.credit(req.user_id, req.amount, req.reason)
        return BalanceResponse(user_id=req.user_id, balance=new_balance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class MintProofRequest(BaseModel):
    metadata_uri: str

@app.post("/mint_proof")
async def mint_proof(req: MintProofRequest):
    """
    Log an on-chain proof for a QNFT.
    """
    try:
        signature = await wallet.mint_proof(req.metadata_uri)
        return {"signature": signature, "status": "confirmed"}
    except Exception as e:
        log.error("Mint proof failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/debit", response_model=BalanceResponse)
async def debit(req: TransactionRequest):
    try:
        new_balance = await wallet.debit(req.user_id, req.amount, req.reason)
        return BalanceResponse(user_id=req.user_id, balance=new_balance)
    except InsufficientFundsError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))