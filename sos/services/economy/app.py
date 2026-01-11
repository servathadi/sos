from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from sos import __version__
from sos.kernel import CapabilityAction
from sos.observability.logging import clear_context, get_logger, set_agent_context
from sos.observability.metrics import MetricsRegistry, render_prometheus
from sos.observability.tracing import TRACE_ID_HEADER, SPAN_ID_HEADER, TraceContext
from sos.services.common.auth import get_capability_from_request, require_capability
from sos.services.common.capability import CapabilityModel

SERVICE_NAME = "economy"
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


class TransactionModel(BaseModel):
    id: str
    tx_type: str
    from_agent: str
    to_agent: str
    amount: int
    currency: str = "MIND"
    status: str = "proposed"
    reason: str = ""
    task_id: Optional[str] = None
    witness_id: Optional[str] = None
    created_at: datetime
    settled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BalanceModel(BaseModel):
    agent_id: str
    currency: str
    available: int
    pending: int
    total_earned: int
    total_spent: int


class PayoutRequestModel(BaseModel):
    agent_id: str
    amount: int
    currency: str = "MIND"
    task_id: str
    reason: str
    requires_witness: bool = False
    capability: Optional[CapabilityModel] = None


class SlashRequestModel(BaseModel):
    agent_id: str
    amount: int
    currency: str = "MIND"
    reason: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    requires_witness: bool = True
    capability: Optional[CapabilityModel] = None


class TransferRequestModel(BaseModel):
    from_agent: str
    to_agent: str
    amount: int
    currency: str = "MIND"
    reason: str = ""
    capability: Optional[CapabilityModel] = None


class WitnessActionModel(BaseModel):
    witness_id: str
    reason: Optional[str] = None
    capability: Optional[CapabilityModel] = None


_TRANSACTIONS: Dict[str, TransactionModel] = {}


app = FastAPI(title="SOS Economy Service", version=__version__)


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


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "version": __version__,
        "service": SERVICE_NAME,
        "uptime_seconds": time.time() - _START_TIME,
        "checks": {
            "ledger_store": os.getenv("SOS_ECONOMY_STORE", "memory"),
        },
        "stats": {
            "transactions": len(_TRANSACTIONS),
        },
    }


@app.get("/metrics")
async def metrics_endpoint():
    return PlainTextResponse(
        render_prometheus(metrics),
        media_type="text/plain; version=0.0.4",
    )


def _compute_balance(agent_id: str, currency: str) -> BalanceModel:
    available = 0
    pending = 0
    total_earned = 0
    total_spent = 0

    for tx in _TRANSACTIONS.values():
        if tx.currency != currency:
            continue

        affects = tx.status in {"committed", "settled"}
        is_pending = tx.status in {"proposed", "validated", "pending_witness", "witnessed"}

        if tx.to_agent == agent_id:
            if affects:
                available += tx.amount
                total_earned += tx.amount
            elif is_pending:
                pending += tx.amount
        if tx.from_agent == agent_id:
            if affects:
                available -= tx.amount
                total_spent += tx.amount
            elif is_pending:
                pending -= tx.amount

    return BalanceModel(
        agent_id=agent_id,
        currency=currency,
        available=available,
        pending=pending,
        total_earned=total_earned,
        total_spent=total_spent,
    )


@app.get("/balance/{agent_id}")
async def get_balance(agent_id: str, http_request: Request, currency: str = Query(default="MIND")) -> BalanceModel:
    require_capability(
        get_capability_from_request(http_request),
        action=CapabilityAction.LEDGER_READ,
        resource=f"ledger:balance/{agent_id}",
    )
    return _compute_balance(agent_id, currency)


@app.get("/transactions")
async def list_transactions(
    http_request: Request,
    agent_id: Optional[str] = None,
    tx_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[TransactionModel]:
    resource = "ledger:transactions/*"
    if agent_id:
        resource = f"ledger:transactions/{agent_id}"
    require_capability(
        get_capability_from_request(http_request),
        action=CapabilityAction.LEDGER_READ,
        resource=resource,
    )
    txs = list(_TRANSACTIONS.values())
    if agent_id:
        txs = [t for t in txs if t.from_agent == agent_id or t.to_agent == agent_id]
    if tx_type:
        txs = [t for t in txs if t.tx_type == tx_type]
    if status:
        txs = [t for t in txs if t.status == status]

    txs.sort(key=lambda t: t.created_at, reverse=True)
    return txs[offset : offset + limit]


def _create_transaction(
    *,
    tx_type: str,
    from_agent: str,
    to_agent: str,
    amount: int,
    currency: str,
    reason: str,
    task_id: Optional[str] = None,
    requires_witness: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
) -> TransactionModel:
    if amount <= 0:
        raise HTTPException(status_code=400, detail="amount_must_be_positive")

    tx_id = f"tx_{uuid.uuid4().hex[:12]}"
    status = "pending_witness" if requires_witness else "committed"
    tx = TransactionModel(
        id=tx_id,
        tx_type=tx_type,
        from_agent=from_agent,
        to_agent=to_agent,
        amount=amount,
        currency=currency,
        status=status,
        reason=reason,
        task_id=task_id,
        created_at=datetime.now(timezone.utc),
        metadata=metadata or {},
    )
    _TRANSACTIONS[tx_id] = tx
    return tx


@app.post("/payout")
async def payout(request: PayoutRequestModel) -> TransactionModel:
    require_capability(
        request.capability,
        action=CapabilityAction.LEDGER_WRITE,
        resource=f"ledger:payout/{request.agent_id}/{request.task_id}",
        expected_subject=request.agent_id,
    )
    return _create_transaction(
        tx_type="payout",
        from_agent="treasury",
        to_agent=request.agent_id,
        amount=request.amount,
        currency=request.currency,
        reason=request.reason,
        task_id=request.task_id,
        requires_witness=request.requires_witness,
    )


@app.post("/slash")
async def slash(request: SlashRequestModel) -> TransactionModel:
    require_capability(
        request.capability,
        action=CapabilityAction.LEDGER_WRITE,
        resource=f"ledger:slash/{request.agent_id}",
    )
    return _create_transaction(
        tx_type="slash",
        from_agent=request.agent_id,
        to_agent="treasury",
        amount=request.amount,
        currency=request.currency,
        reason=request.reason,
        requires_witness=request.requires_witness,
        metadata={"evidence": request.evidence},
    )


@app.post("/transfer")
async def transfer(request: TransferRequestModel) -> TransactionModel:
    require_capability(
        request.capability,
        action=CapabilityAction.LEDGER_WRITE,
        resource=f"ledger:transfer/{request.from_agent}/{request.to_agent}",
        expected_subject=request.from_agent,
    )
    return _create_transaction(
        tx_type="transfer",
        from_agent=request.from_agent,
        to_agent=request.to_agent,
        amount=request.amount,
        currency=request.currency,
        reason=request.reason,
        requires_witness=False,
    )


@app.post("/transactions/{transaction_id}/witness/approve")
async def witness_approve(transaction_id: str, request: WitnessActionModel) -> TransactionModel:
    require_capability(
        request.capability,
        action=CapabilityAction.LEDGER_WRITE,
        resource=f"ledger:witness/approve/{transaction_id}",
        expected_subject=request.witness_id,
    )
    tx = _TRANSACTIONS.get(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    if tx.status != "pending_witness":
        raise HTTPException(status_code=400, detail="transaction_not_pending_witness")

    tx.witness_id = request.witness_id
    tx.status = "committed"
    tx.settled_at = datetime.now(timezone.utc)
    return tx


@app.post("/transactions/{transaction_id}/witness/reject")
async def witness_reject(transaction_id: str, request: WitnessActionModel) -> TransactionModel:
    require_capability(
        request.capability,
        action=CapabilityAction.LEDGER_WRITE,
        resource=f"ledger:witness/reject/{transaction_id}",
        expected_subject=request.witness_id,
    )
    tx = _TRANSACTIONS.get(transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="transaction_not_found")
    if tx.status != "pending_witness":
        raise HTTPException(status_code=400, detail="transaction_not_pending_witness")

    tx.witness_id = request.witness_id
    tx.status = "rejected"
    if request.reason:
        tx.metadata["rejection_reason"] = request.reason
    return tx
