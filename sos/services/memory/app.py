from __future__ import annotations

import os
import time
from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sos import __version__
from sos.observability.logging import get_logger
from sos.services.memory.core import MemoryCore

SERVICE_NAME = "memory"
_START_TIME = time.time()

log = get_logger(SERVICE_NAME, min_level=os.getenv("SOS_LOG_LEVEL", "info"))

app = FastAPI(title="SOS Memory Service", version=__version__)
memory = MemoryCore()

class AddMemoryRequest(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}

class SearchRequest(BaseModel):
    query: str
    limit: int = 5

@app.get("/health")
async def health() -> Dict[str, Any]:
    core_health = await memory.health()
    return {
        "status": "ok",
        "version": __version__,
        "service": SERVICE_NAME,
        "uptime_seconds": time.time() - _START_TIME,
        "core": core_health
    }

@app.post("/add")
async def add_memory(request: AddMemoryRequest):
    item_id = await memory.add(request.content, request.metadata)
    return {"id": item_id, "status": "stored"}

@app.post("/search")
async def search_memory(request: SearchRequest):
    results = await memory.search(request.query, request.limit)
    return {"results": results}