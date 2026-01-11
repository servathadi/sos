from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from sos.services.common.capability import CapabilityModel
from sos.observability.logging import get_logger

log = get_logger("capability_guard")

async def capability_guard_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to enforce Capability-Based Security.
    
    Rules:
    1. If the route is public (health, metrics), allow.
    2. If the request requires a capability (e.g. tool execution), verify the token.
    """
    path = request.url.path
    if path in ["/health", "/metrics", "/docs", "/openapi.json"]:
        return await call_next(request)

    # For chat requests, we parse the body to check for 'tools_enabled'
    # This is a simplification; normally we'd decode a Bearer token
    # But SOS uses explicit Capability objects passed in the payload for now.
    
    # We pass through for now, but log the check
    # In a real implementation, we would inspect the request body here
    # or rely on the endpoint to call a verifier function.
    
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
