from typing import Callable, Optional
import os
from datetime import datetime, timezone

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from sos.services.common.capability import CapabilityModel
from sos.services.common.fmaap import FMAAPPolicyEngine, FMAAPValidationRequest
from sos.services.common.auth import get_capability_from_request, decode_capability_header
from sos.kernel.capability import (
    Capability,
    CapabilityAction,
    verify_capability,
    verify_capability_signature,
)
from sos.observability.logging import get_logger

log = get_logger("capability_guard")
fmaap = FMAAPPolicyEngine()

# Paths that don't require capability verification
PUBLIC_PATHS = frozenset([
    "/health", "/metrics", "/docs", "/openapi.json",
    "/api/health", "/api/docs", "/"
])


def _is_strict_mode() -> bool:
    """Check if strict capability enforcement is enabled."""
    return os.getenv("SOS_STRICT_CAPABILITIES", "0").lower() in ("1", "true", "yes")


def _get_public_key() -> Optional[bytes]:
    """Load River's public key for signature verification."""
    key_hex = os.getenv("SOS_RIVER_PUBLIC_KEY_HEX") or os.getenv("SOS_CAPABILITY_PUBLIC_KEY_HEX")
    if not key_hex:
        return None
    try:
        return bytes.fromhex(key_hex)
    except ValueError:
        log.error("Invalid SOS_RIVER_PUBLIC_KEY_HEX format")
        return None


async def capability_guard_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to enforce FMAAP and Capability-Based Security.

    Enforcement modes:
    - SOS_STRICT_CAPABILITIES=0 (default): Log violations but allow requests
    - SOS_STRICT_CAPABILITIES=1: Block unauthorized requests with 403
    """
    path = request.url.path

    # Skip public paths
    if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/openapi"):
        return await call_next(request)

    agent_id = request.headers.get("X-SOS-Agent-ID", "unknown")
    strict_mode = _is_strict_mode()

    # --- FMAAP Validation ---
    validation = fmaap.validate(FMAAPValidationRequest(
        agent_id=agent_id,
        action="api_request",
        resource=path
    ))

    if not validation.valid:
        log.warning(
            f"FMAAP Validation FAILED for {agent_id} on {path}",
            score=validation.overall_score,
            strict=strict_mode
        )
        if strict_mode:
            return JSONResponse(
                status_code=403,
                content={
                    "error": "fmaap_violation",
                    "message": f"FMAAP validation failed (score: {validation.overall_score:.2f})",
                    "agent_id": agent_id,
                    "resource": path
                }
            )
    else:
        log.debug(f"FMAAP Validation PASSED", score=validation.overall_score)

    # --- Capability Token Validation (if provided) ---
    cap_header = request.headers.get("X-SOS-Capability") or request.headers.get("Authorization")

    if cap_header:
        try:
            cap_model = decode_capability_header(cap_header)
            cap = cap_model.to_capability()

            # Verify capability
            public_key = _get_public_key()
            verifier = CapabilityVerifier(public_key=public_key)

            is_valid, reason = verifier.verify_full(cap, action="api_request", resource=path)

            if not is_valid:
                log.warning(
                    f"Capability verification FAILED: {reason}",
                    agent_id=agent_id,
                    capability_id=cap.id,
                    resource=path
                )
                if strict_mode:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "error": "capability_invalid",
                            "message": reason,
                            "capability_id": cap.id
                        }
                    )
            else:
                log.info(
                    f"Capability verified",
                    capability_id=cap.id,
                    subject=cap.subject,
                    action=cap.action.value if hasattr(cap.action, 'value') else cap.action
                )
                # Attach verified capability to request state for downstream use
                request.state.capability = cap

        except Exception as e:
            log.warning(f"Capability header parse error: {e}")
            if strict_mode:
                return JSONResponse(
                    status_code=400,
                    content={"error": "invalid_capability_header", "message": str(e)}
                )

    response = await call_next(request)
    return response


class CapabilityVerifier:
    """
    Service-level verifier for capabilities with full signature verification.
    """

    def __init__(self, public_key: Optional[bytes] = None):
        """
        Initialize verifier with optional public key for signature verification.

        Args:
            public_key: Ed25519 public key bytes (32 bytes) for signature verification.
                       If None, signature verification is skipped.
        """
        self.public_key = public_key

    def verify(self, capability: CapabilityModel, action: str, resource: str) -> bool:
        """
        Verify if a capability grants permission for an action.
        Backward-compatible simple verification.
        """
        is_valid, _ = self.verify_full(capability.to_capability(), action, resource)
        return is_valid

    def verify_full(
        self,
        capability: Capability,
        action: str,
        resource: str
    ) -> tuple[bool, str]:
        """
        Full verification of a capability including signature and expiry.

        Returns:
            Tuple of (is_valid, reason)
        """
        # 1. Check expiry
        if capability.is_expired:
            return False, f"Capability expired at {capability.expires_at.isoformat()}"

        # 2. Check uses remaining
        if capability.uses_remaining is not None and capability.uses_remaining <= 0:
            return False, "Capability has no uses remaining"

        # 3. Check action matches (wildcard or exact)
        cap_action = capability.action.value if hasattr(capability.action, 'value') else str(capability.action)
        if cap_action != "*" and cap_action != action:
            return False, f"Action mismatch: capability grants '{cap_action}', requested '{action}'"

        # 4. Check resource matches (glob pattern)
        if not capability.matches_resource(resource):
            return False, f"Resource mismatch: capability grants '{capability.resource}', requested '{resource}'"

        # 5. Verify signature if public key available
        if self.public_key is not None:
            if not capability.signature:
                return False, "Capability is missing signature (required when public key is configured)"

            sig_valid, sig_reason = verify_capability_signature(capability, self.public_key)
            if not sig_valid:
                return False, f"Signature verification failed: {sig_reason}"

        return True, "Valid"

    def verify_for_action(
        self,
        capability: Capability,
        required_action: CapabilityAction,
        resource: str
    ) -> tuple[bool, str]:
        """
        Verify capability for a specific CapabilityAction enum.
        Uses the kernel's verify_capability function.
        """
        return verify_capability(
            capability=capability,
            required_action=required_action,
            resource=resource,
            public_key=self.public_key
        )
