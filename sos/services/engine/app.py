from __future__ import annotations

import os
import time
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse

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
engine = SOSEngine()  # Initialize Core Engine


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