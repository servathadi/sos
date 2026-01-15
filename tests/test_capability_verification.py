"""
TEST-002: Capability Verification Tests

Tests for the capability-based access control system including:
- Signature verification (forgery rejection)
- Expiry checking
- Action/resource matching
- Uses remaining tracking
- Middleware integration
"""

import pytest
from datetime import datetime, timedelta, timezone
from nacl.signing import SigningKey

from sos.kernel.capability import (
    Capability,
    CapabilityAction,
    create_capability,
    sign_capability,
    verify_capability,
    verify_capability_signature,
)
from sos.services.engine.middleware import CapabilityVerifier


class TestCapabilityExpiry:
    """Tests for capability expiration."""

    def test_fresh_capability_is_valid(self):
        """A freshly created capability should not be expired."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )
        assert not cap.is_expired
        assert cap.is_valid

    def test_expired_capability_is_rejected(self):
        """An expired capability should be rejected."""
        cap = Capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            issued_at=datetime.now(timezone.utc) - timedelta(hours=2),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert cap.is_expired
        assert not cap.is_valid

        # Verify function should also reject
        is_valid, reason = verify_capability(
            cap,
            required_action=CapabilityAction.MEMORY_READ,
            resource="memory:test"
        )
        assert not is_valid
        assert "expired" in reason.lower()

    def test_capability_expires_at_exact_time(self):
        """Capability should expire exactly at expires_at."""
        # Create capability that expires in the past by 1 second
        cap = Capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            issued_at=datetime.now(timezone.utc) - timedelta(hours=1),
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        assert cap.is_expired


class TestCapabilitySignature:
    """Tests for Ed25519 signature verification."""

    @pytest.fixture
    def signing_key(self):
        """Generate a signing key for tests."""
        return SigningKey.generate()

    @pytest.fixture
    def public_key(self, signing_key):
        """Get public key bytes from signing key."""
        return bytes(signing_key.verify_key)

    def test_valid_signature_accepted(self, signing_key, public_key):
        """A properly signed capability should verify."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )
        sign_capability(cap, signing_key)

        is_valid, reason = verify_capability_signature(cap, public_key)
        assert is_valid
        assert "valid" in reason.lower()

    def test_forged_signature_rejected(self, public_key):
        """A forged/tampered signature should be rejected."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )
        # Forge a fake signature
        cap.signature = "ed25519:" + "00" * 64

        is_valid, reason = verify_capability_signature(cap, public_key)
        assert not is_valid
        assert "invalid" in reason.lower()

    def test_missing_signature_rejected_when_key_provided(self, public_key):
        """Capability without signature should be rejected when public key is set."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )
        # No signature

        is_valid, reason = verify_capability_signature(cap, public_key)
        assert not is_valid
        assert "missing" in reason.lower()

    def test_tampered_capability_rejected(self, signing_key, public_key):
        """A capability modified after signing should be rejected."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )
        sign_capability(cap, signing_key)

        # Tamper with the capability after signing
        cap.resource = "memory:secret/*"  # Changed resource

        is_valid, reason = verify_capability_signature(cap, public_key)
        assert not is_valid

    def test_wrong_key_signature_rejected(self, signing_key):
        """Signature from different key should be rejected."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )
        sign_capability(cap, signing_key)

        # Use a different public key
        different_key = SigningKey.generate()
        wrong_public_key = bytes(different_key.verify_key)

        is_valid, reason = verify_capability_signature(cap, wrong_public_key)
        assert not is_valid


class TestCapabilityActionMatching:
    """Tests for action permission matching."""

    def test_matching_action_accepted(self):
        """Capability with matching action should be accepted."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )

        is_valid, _ = verify_capability(
            cap,
            required_action=CapabilityAction.MEMORY_READ,
            resource="memory:test"
        )
        assert is_valid

    def test_mismatched_action_rejected(self):
        """Capability with wrong action should be rejected."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )

        is_valid, reason = verify_capability(
            cap,
            required_action=CapabilityAction.MEMORY_WRITE,  # Different action
            resource="memory:test"
        )
        assert not is_valid
        assert "action" in reason.lower()

    def test_read_capability_cannot_write(self):
        """Read capability should not allow write operations."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.FILE_READ,
            resource="file:*",
            duration_hours=1
        )

        is_valid, _ = verify_capability(
            cap,
            required_action=CapabilityAction.FILE_WRITE,
            resource="file:/etc/passwd"
        )
        assert not is_valid


class TestCapabilityResourceMatching:
    """Tests for resource pattern matching."""

    def test_exact_resource_match(self):
        """Exact resource match should work."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.TOOL_EXECUTE,
            resource="tool:web_search",
            duration_hours=1
        )

        is_valid, _ = verify_capability(
            cap,
            required_action=CapabilityAction.TOOL_EXECUTE,
            resource="tool:web_search"
        )
        assert is_valid

    def test_wildcard_resource_match(self):
        """Wildcard resource pattern should match."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:kasra/*",
            duration_hours=1
        )

        is_valid, _ = verify_capability(
            cap,
            required_action=CapabilityAction.MEMORY_READ,
            resource="memory:kasra/notes"
        )
        assert is_valid

    def test_star_matches_all(self):
        """Star resource should match everything."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="*",
            duration_hours=1
        )

        is_valid, _ = verify_capability(
            cap,
            required_action=CapabilityAction.MEMORY_READ,
            resource="memory:anything/here"
        )
        assert is_valid

    def test_resource_mismatch_rejected(self):
        """Resource mismatch should be rejected."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:kasra/*",
            duration_hours=1
        )

        is_valid, reason = verify_capability(
            cap,
            required_action=CapabilityAction.MEMORY_READ,
            resource="memory:river/secrets"  # Different scope
        )
        assert not is_valid
        assert "resource" in reason.lower()

    def test_partial_match_rejected(self):
        """Partial resource match should be rejected."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:kasra",
            duration_hours=1
        )

        # Should not match subpath without wildcard
        is_valid, _ = verify_capability(
            cap,
            required_action=CapabilityAction.MEMORY_READ,
            resource="memory:kasra/subdir"
        )
        assert not is_valid


class TestCapabilityUsesRemaining:
    """Tests for uses_remaining limits."""

    def test_unlimited_uses_always_valid(self):
        """Capability with no uses limit should always be valid."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1,
            uses=None
        )
        assert cap.uses_remaining is None
        assert cap.is_valid

    def test_positive_uses_valid(self):
        """Capability with positive uses should be valid."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1,
            uses=5
        )
        assert cap.uses_remaining == 5
        assert cap.is_valid

    def test_zero_uses_rejected(self):
        """Capability with zero uses should be rejected."""
        cap = Capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            uses_remaining=0,
        )
        assert not cap.is_valid

        is_valid, reason = verify_capability(
            cap,
            required_action=CapabilityAction.MEMORY_READ,
            resource="memory:test"
        )
        assert not is_valid
        assert "uses" in reason.lower()

    def test_negative_uses_rejected(self):
        """Capability with negative uses should be rejected."""
        cap = Capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            uses_remaining=-1,
        )
        assert not cap.is_valid


class TestCapabilityVerifier:
    """Tests for the CapabilityVerifier service class."""

    @pytest.fixture
    def verifier(self):
        """Create verifier without public key (no signature check)."""
        return CapabilityVerifier(public_key=None)

    @pytest.fixture
    def signing_key(self):
        return SigningKey.generate()

    @pytest.fixture
    def verifier_with_key(self, signing_key):
        """Create verifier with public key (signature check enabled)."""
        return CapabilityVerifier(public_key=bytes(signing_key.verify_key))

    def test_verifier_accepts_valid_capability(self, verifier):
        """Verifier should accept valid capability."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )

        is_valid, reason = verifier.verify_full(cap, action="memory:read", resource="memory:test")
        assert is_valid

    def test_verifier_rejects_expired(self, verifier):
        """Verifier should reject expired capability."""
        cap = Capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        is_valid, reason = verifier.verify_full(cap, action="memory:read", resource="memory:test")
        assert not is_valid
        assert "expired" in reason.lower()

    def test_verifier_requires_signature_when_key_set(self, verifier_with_key):
        """Verifier with public key should require signature."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )
        # No signature set

        is_valid, reason = verifier_with_key.verify_full(cap, action="memory:read", resource="memory:test")
        assert not is_valid
        assert "signature" in reason.lower()

    def test_verifier_accepts_signed_capability(self, verifier_with_key, signing_key):
        """Verifier should accept properly signed capability."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )
        sign_capability(cap, signing_key)

        is_valid, reason = verifier_with_key.verify_full(cap, action="memory:read", resource="memory:test")
        assert is_valid


class TestCapabilitySerialization:
    """Tests for capability serialization/deserialization."""

    def test_roundtrip_dict(self):
        """Capability should survive dict roundtrip."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1,
            uses=10
        )

        data = cap.to_dict()
        restored = Capability.from_dict(data)

        assert restored.id == cap.id
        assert restored.subject == cap.subject
        assert restored.action == cap.action
        assert restored.resource == cap.resource
        assert restored.uses_remaining == cap.uses_remaining

    def test_roundtrip_json(self):
        """Capability should survive JSON roundtrip."""
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.TOOL_EXECUTE,
            resource="tool:*",
            duration_hours=24
        )

        json_str = cap.to_json()
        restored = Capability.from_json(json_str)

        assert restored.id == cap.id
        assert restored.action == cap.action

    def test_signed_capability_roundtrip(self):
        """Signed capability should preserve signature through roundtrip."""
        signing_key = SigningKey.generate()
        cap = create_capability(
            subject="agent:kasra",
            action=CapabilityAction.MEMORY_READ,
            resource="memory:*",
            duration_hours=1
        )
        sign_capability(cap, signing_key)

        restored = Capability.from_json(cap.to_json())
        assert restored.signature == cap.signature

        # Signature should still be valid
        public_key = bytes(signing_key.verify_key)
        is_valid, _ = verify_capability_signature(restored, public_key)
        assert is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
