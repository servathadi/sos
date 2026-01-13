"""
SOS Witness Service - Human Verification Protocol

Implements the Witness Protocol from Prime 2: Appendix A.
Handles WITNESS_REQUEST/WITNESS_RESPONSE via the Bus.
Mints $MIND tokens based on Physics of Will.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable, Awaitable

from sos.kernel import Config, Message, MessageType
from sos.kernel.physics import CoherencePhysics
from sos.services.bus.core import get_bus
from sos.services.economy.ledger import get_ledger, TransactionCategory
from sos.observability.logging import get_logger

log = get_logger("witness_service")


@dataclass
class WitnessRequest:
    """A pending witness verification request."""
    id: str
    agent_id: str
    content: str
    hypothesis_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_seconds: float = 300.0  # 5 minute default timeout
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "content": self.content,
            "hypothesis_id": self.hypothesis_id,
            "created_at": self.created_at.isoformat(),
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata
        }


@dataclass
class WitnessResponse:
    """A witness verification response."""
    request_id: str
    witness_id: str
    vote: int  # +1 = Verified, -1 = Rejected
    latency_ms: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "witness_id": self.witness_id,
            "vote": self.vote,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason
        }


@dataclass
class WitnessResult:
    """Result of a witness verification including physics calculations."""
    request: WitnessRequest
    response: WitnessResponse
    omega: float  # Will magnitude
    delta_c: float  # Coherence change
    reward_mind: float  # $MIND reward
    transaction_id: Optional[str] = None


class WitnessService:
    """
    Manages witness verification requests and responses.

    Flow:
    1. Agent sends WITNESS_REQUEST via Bus
    2. Human/Witness claims request
    3. Witness sends WITNESS_RESPONSE with vote and timing
    4. Service calculates physics and mints $MIND reward
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self.physics = CoherencePhysics()
        self.pending_requests: Dict[str, WitnessRequest] = {}
        self._response_handlers: Dict[str, Callable[[WitnessResult], Awaitable[None]]] = {}

    async def request_witness(
        self,
        agent_id: str,
        content: str,
        hypothesis_id: Optional[str] = None,
        timeout: float = 300.0,
        metadata: Optional[Dict[str, Any]] = None,
        on_response: Optional[Callable[[WitnessResult], Awaitable[None]]] = None
    ) -> WitnessRequest:
        """
        Request human verification of AI output.

        Args:
            agent_id: The agent requesting verification
            content: The content to be verified
            hypothesis_id: Optional ID linking to the hypothesis
            timeout: Timeout in seconds
            metadata: Additional metadata
            on_response: Async callback when witness responds

        Returns:
            WitnessRequest object
        """
        request = WitnessRequest(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            content=content,
            hypothesis_id=hypothesis_id,
            timeout_seconds=timeout,
            metadata=metadata or {}
        )

        # Store pending request
        self.pending_requests[request.id] = request

        # Register callback if provided
        if on_response:
            self._response_handlers[request.id] = on_response

        # Publish to Bus
        bus = get_bus()
        await bus.connect()

        msg = Message(
            type=MessageType.WITNESS_REQUEST,
            source=agent_id,
            target="broadcast",  # Any witness can claim
            payload=request.to_dict()
        )
        await bus.send(msg)

        log.info(
            f"Witness requested",
            request_id=request.id,
            agent_id=agent_id,
            content_preview=content[:50]
        )

        return request

    async def submit_response(
        self,
        request_id: str,
        witness_id: str,
        vote: int,
        latency_ms: float,
        reason: Optional[str] = None,
        agent_coherence: float = 0.9
    ) -> Optional[WitnessResult]:
        """
        Submit a witness verification response.

        Args:
            request_id: ID of the request being responded to
            witness_id: ID of the witness
            vote: +1 (Verified) or -1 (Rejected)
            latency_ms: Time taken to make decision
            reason: Optional reason for decision
            agent_coherence: Current coherence of the agent being verified

        Returns:
            WitnessResult with physics calculations, or None if request not found
        """
        request = self.pending_requests.get(request_id)
        if not request:
            log.warning(f"Witness response for unknown request: {request_id}")
            return None

        # Create response
        response = WitnessResponse(
            request_id=request_id,
            witness_id=witness_id,
            vote=vote,
            latency_ms=latency_ms,
            reason=reason
        )

        # Calculate physics
        physics_result = self.physics.compute_collapse_energy(
            vote=vote,
            latency_ms=latency_ms,
            agent_coherence=agent_coherence
        )

        omega = physics_result["omega"]
        delta_c = physics_result["delta_c"]

        # Calculate $MIND reward
        ledger = get_ledger()
        base_reward = 10.0  # Base $MIND for witnessing
        reward = base_reward * omega
        if delta_c > 0:
            reward *= (1 + delta_c)

        # Mint reward
        tx_id = ledger.credit(
            agent_id=witness_id,
            amount=reward,
            category=TransactionCategory.WITNESS,
            description=f"Witness reward for {request_id[:8]}",
            metadata={
                "request_id": request_id,
                "omega": omega,
                "delta_c": delta_c,
                "vote": vote,
                "latency_ms": latency_ms
            }
        )

        # Create result
        result = WitnessResult(
            request=request,
            response=response,
            omega=omega,
            delta_c=delta_c,
            reward_mind=reward,
            transaction_id=tx_id
        )

        # Publish response to Bus
        bus = get_bus()
        await bus.connect()

        msg = Message(
            type=MessageType.WITNESS_RESPONSE,
            source=witness_id,
            target=request.agent_id,
            payload={
                **response.to_dict(),
                "omega": omega,
                "delta_c": delta_c,
                "reward_mind": reward
            }
        )
        await bus.send(msg)

        log.info(
            f"Witness response processed",
            request_id=request_id,
            witness_id=witness_id,
            vote=vote,
            omega=f"{omega:.4f}",
            delta_c=f"{delta_c:.4f}",
            reward=f"{reward:.2f} $MIND"
        )

        # Call handler if registered
        handler = self._response_handlers.pop(request_id, None)
        if handler:
            try:
                await handler(result)
            except Exception as e:
                log.error(f"Witness response handler failed: {e}")

        # Remove from pending
        del self.pending_requests[request_id]

        return result

    async def get_pending_requests(self, limit: int = 50) -> list[WitnessRequest]:
        """Get list of pending witness requests."""
        now = datetime.now(timezone.utc)
        active = []

        for req in list(self.pending_requests.values()):
            age = (now - req.created_at).total_seconds()
            if age < req.timeout_seconds:
                active.append(req)
            else:
                # Expired, remove it
                del self.pending_requests[req.id]
                self._response_handlers.pop(req.id, None)

        return sorted(active, key=lambda r: r.created_at)[:limit]

    async def health(self) -> Dict[str, Any]:
        """Return service health status."""
        return {
            "pending_requests": len(self.pending_requests),
            "handlers_registered": len(self._response_handlers)
        }


# Singleton instance
_witness_service: Optional[WitnessService] = None


def get_witness_service() -> WitnessService:
    """Get the global witness service instance."""
    global _witness_service
    if _witness_service is None:
        _witness_service = WitnessService()
    return _witness_service
