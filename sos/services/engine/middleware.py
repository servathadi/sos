from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from sos.services.common.capability import CapabilityModel
from sos.services.common.fmaap import FMAAPPolicyEngine, FMAAPValidationRequest
from sos.observability.logging import get_logger

log = get_logger("capability_guard")
fmaap = FMAAPPolicyEngine()

async def capability_guard_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to enforce FMAAP and Capability-Based Security.
    """
    path = request.url.path
    if path in ["/health", "/metrics", "/docs", "/openapi.json"]:
        return await call_next(request)

    # For Phase 1, we perform a background FMAAP validation
    # to witness the resonance without blocking.
    agent_id = request.headers.get("X-SOS-Agent-ID", "unknown")
    
    validation = fmaap.validate(FMAAPValidationRequest(
        agent_id=agent_id,
        action="api_request",
        resource=path
    ))
    
    if not validation.valid:
        log.warning(f"FMAAP Validation FAILED for {agent_id}", score=validation.overall_score)
        # In strict mode, we would return 403 here.
    else:
        log.info(f"FMAAP Validation PASSED", score=validation.overall_score)
    
    response = await call_next(request)
    return response

class CapabilityVerifier:
    """
    Service-level verifier for capabilities.
    """
    def verify(self, capability: CapabilityModel, action: str, resource: str) -> bool:
        """
        Verify if a capability grants permission for an action.
        """
        if capability.action != "*" and capability.action != action:
            log.warning(f"Capability mismatch: {capability.action} != {action}")
            return False
            
        if capability.resource != "*" and capability.resource != resource:
            log.warning(f"Resource mismatch: {capability.resource} != {resource}")
            return False
            
        # TODO: Check signature and expiry
        return True
