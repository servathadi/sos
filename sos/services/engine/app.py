from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from sos import __version__
from sos.kernel import Config
from sos.observability.logging import clear_context, get_logger, set_agent_context
from sos.observability.metrics import MetricsRegistry, render_prometheus
from sos.observability.tracing import (
    TRACE_ID_HEADER,
    SPAN_ID_HEADER,
    TraceContext,
)
from sos.contracts.engine import ChatRequest, ChatResponse
from sos.services.engine.core import SOSEngine
from sos.services.engine.middleware import capability_guard_middleware
from sos.services.bus.core import get_bus

SERVICE_NAME = "engine"
_START_TIME = time.time()

log = get_logger(SERVICE_NAME, min_level=os.getenv("SOS_LOG_LEVEL", "info"))

metrics = MetricsRegistry()
REQUEST_COUNT = metrics.counter(
    name="sos_requests_total",
    description="Total requests",
    label_names=("service", "status"),
)
REQUEST_DURATION = metrics.histogram(
    name="sos_request_duration_seconds",
    description="Request duration",
    label_names=("service",),
)

app = FastAPI(title="SOS Engine Service", version=__version__)
app.middleware("http")(capability_guard_middleware) # Register FMAAP Guard
engine = SOSEngine()


@app.on_event("startup")
async def startup_event():
    import asyncio
    # Initialize River's Soul (Memory + Cache)
    await engine.initialize_soul()

    # Start SOSDaemon (Heartbeat, Dreams, Maintenance, Task Claiming, Reporting)
    from sos.services.engine.daemon import start_daemon
    await start_daemon()

    # Start AsyncWorker for task execution (AI Employee muscle)
    from sos.services.execution.worker import get_worker
    worker = get_worker()
    asyncio.create_task(worker.start())
    log.info("AsyncWorker started for AI Employee task execution")

    # Start listening for signals on the Redis Bus
    asyncio.create_task(engine.listen_to_bus())

    log.info("Engine fully awake and listening to the Bus.")


@app.websocket("/ws/nervous-system/{agent_id}")
async def websocket_endpoint(websocket: WebSocket, agent_id: str):
    """
    WebSocket bridge to the Redis Nervous System.
    """
    await websocket.accept()
    bus = get_bus()
    await bus.connect()
    
    log.info(f"🔌 WebSocket connection established for agent: {agent_id}")
    
    try:
        # Subscribe to private + squad (marketing for now) + global
        async for message in bus.subscribe(agent_id, squads=["marketing"]):
            # Forward SOS Message to WebSocket as JSON
            await websocket.send_json(message.to_dict())
            log.debug(f"📤 Forwarded signal to {agent_id}: {message.type.value}")
            
    except WebSocketDisconnect:
        log.info(f"🛑 WebSocket disconnected for agent: {agent_id}")
    except Exception as e:
        log.error(f"❌ WebSocket error: {e}")
    finally:
        # Cleanup if needed
        pass


@app.middleware("http")
async def _observability_middleware(request: Request, call_next):
    ctx = TraceContext.from_headers(dict(request.headers))
    ctx.activate()

    if agent_id := request.headers.get("X-SOS-Agent-ID"):
        set_agent_context(agent_id)

    status_label = "success"
    with REQUEST_DURATION.labels(service=SERVICE_NAME).time():
        try:
            response = await call_next(request)
            status_label = "success" if response.status_code < 400 else "error"
        except Exception as e:
            status_label = "error"
            log.error("Unhandled exception", error=str(e), path=str(request.url.path))
            response = JSONResponse(status_code=500, content={"detail": "internal_error"})

    REQUEST_COUNT.labels(service=SERVICE_NAME, status=status_label).inc()

    response.headers[TRACE_ID_HEADER] = ctx.trace_id
    response.headers[SPAN_ID_HEADER] = ctx.span_id

    clear_context()
    return response


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Process a chat message via the SOS Engine.
    """
    if request.stream:
        # Return streaming response
        return StreamingResponse(
            engine.chat_stream(request),
            media_type="text/event-stream"
        )
    
    # Return standard response
    return await engine.chat(request)


from sos.services.engine.swarm import get_swarm

@app.get("/tasks")
async def list_tasks():
    """
    List pending tasks from the Swarm Dispatcher.
    SOS is agnostic; it returns whatever is in the repository.
    """
    swarm = get_swarm()
    tasks = await swarm.list_pending_tasks()
    return {"tasks": tasks}


class TaskSubmission(BaseModel):
    """Result submission for a completed task."""
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None


@app.post("/tasks/{task_id}/submit")
async def submit_task_result(task_id: str, result: TaskSubmission):
    """
    Submit result for a claimed task.

    Used by workers to report task completion.
    """
    swarm = get_swarm()
    success = await swarm.submit_result(task_id, result.dict())

    if success:
        return {"status": "ok", "task_id": task_id}
    else:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Task {task_id} not found or already completed"}
        )


@app.post("/tasks/{task_id}/claim")
async def claim_task(task_id: str, worker_id: str = "api_worker"):
    """
    Claim a pending task for execution.

    Used by external workers to claim tasks.
    """
    swarm = get_swarm()
    success = await swarm.claim_task(task_id, worker_id)

    if success:
        return {"status": "claimed", "task_id": task_id, "worker_id": worker_id}
    else:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Task {task_id} could not be claimed"}
        )

class ConnectRequest(BaseModel):
    action: str  # "publish" | "recall"
    target: Optional[str] = "global"
    payload: Dict[str, Any]

@app.post("/v1/connect")
async def nervous_system_gateway(req: ConnectRequest, request: Request):
    """
    Secure Gateway for External Agents to access the Nervous System.
    Auth: X-SOS-API-KEY header.
    """
    api_key = request.headers.get("X-SOS-API-KEY")
    # In production, check against config.secrets or DB
    # For Alpha, we accept a hardcoded key or match environment variable
    valid_key = os.environ.get("SOS_MASTER_KEY", "sk-mumega-alpha-001")
    
    if api_key != valid_key:
        return JSONResponse(status_code=401, content={"detail": "Invalid API Key"})

    bus = get_bus()
    await bus.connect()

    if req.action == "publish":
        # External agent speaking to the Hive
        msg = Message(
            type=MessageType.CHAT, # Use proper Enum
            source="external_gateway",
            target=req.target,
            payload=req.payload
        )
        await bus.send(msg)
        return {"status": "sent", "channel": req.target}

    elif req.action == "recall":
        # External agent querying memory
        agent_id = req.target
        memories = await bus.memory_recall(agent_id, limit=5)
        return {"status": "success", "memories": memories}

    return JSONResponse(status_code=400, content={"detail": "Unknown action"})

@app.get("/health")
async def health() -> Dict[str, Any]:
    # Check core health
    engine_health = await engine.health()
    
    return {
        "status": "ok",
        "version": __version__,
        "service": SERVICE_NAME,
        "uptime_seconds": time.time() - _START_TIME,
        "engine": engine_health,
    }


@app.get("/metrics")
async def metrics_endpoint():
    return PlainTextResponse(
        render_prometheus(metrics),
        media_type="text/plain; version=0.0.4",
    )
# --- Sovereign Gateway Proxies ---
from pydantic import BaseModel
import httpx

class MintRequest(BaseModel):
    agent_id: str
    role: str

@app.get("/wallet/balance/{agent_id}")
async def proxy_wallet_balance(agent_id: str):
    """Proxy to Economy Service"""
    async with httpx.AsyncClient() as client:
        url = f"{engine.config.economy_url}/balance/{agent_id}"
        resp = await client.get(url)
        return JSONResponse(content=resp.json(), status_code=resp.status_code)

@app.post("/identity/mint")
async def proxy_identity_mint(request: MintRequest):
    """Proxy to Identity Service"""
    async with httpx.AsyncClient() as client:
        url = f"{engine.config.identity_url}/mint"
        resp = await client.post(url, json=request.dict())
        return JSONResponse(content=resp.json(), status_code=resp.status_code)
