"""Tests for capability tokens and Ed25519 signing."""

import time
from uuid import uuid4

import pytest

from app.core.capability_jwt import (
    CapabilityTokenClaims,
    TokenConstraints,
    create_capability_token,
    verify_capability_token,
)
from app.core.ed25519 import (
    GatewayKeyManager,
    generate_ed25519_keypair,
    public_key_from_base64,
    public_key_to_base64,
)


class TestEd25519KeyManagement:
    """Test Ed25519 key generation and management."""

    def test_generate_keypair(self):
        """Test keypair generation."""
        private_key, public_key = generate_ed25519_keypair()

        assert private_key is not None
        assert public_key is not None

    def test_public_key_base64_roundtrip(self):
        """Test public key base64 encoding/decoding."""
        _, public_key = generate_ed25519_keypair()

        # Encode to base64
        b64 = public_key_to_base64(public_key)
        assert isinstance(b64, str)
        assert len(b64) > 0

        # Decode back
        decoded = public_key_from_base64(b64)
        assert decoded is not None

        # Re-encode should match
        assert public_key_to_base64(decoded) == b64

    def test_gateway_key_manager_singleton(self):
        """Test gateway key manager is a singleton."""
        manager1 = GatewayKeyManager()
        manager2 = GatewayKeyManager()

        assert manager1 is manager2

    def test_gateway_key_manager_has_keys(self):
        """Test gateway key manager has keys available."""
        manager = GatewayKeyManager()

        # Should have both keys
        assert manager.private_key is not None
        assert manager.public_key is not None

        # Public key should be base64 encodable
        b64 = manager.get_public_key_base64()
        assert isinstance(b64, str)
        assert len(b64) > 0


class TestCapabilityTokenClaims:
    """Test capability token claims."""

    def test_claims_to_dict(self):
        """Test claims serialization to dictionary."""
        claims = CapabilityTokenClaims(
            iss="gateway",
            sub="agent-123",
            org_id="org-456",
            uapk_id="uapk-789",
            allowed_action_types=["payment", "data_access"],
            allowed_tools=["stripe_transfer"],
            iat=1000,
            exp=2000,
            jti="test-jti",
        )

        data = claims.to_dict()

        assert data["iss"] == "gateway"
        assert data["sub"] == "agent-123"
        assert data["org_id"] == "org-456"
        assert data["uapk_id"] == "uapk-789"
        assert data["allowed_action_types"] == ["payment", "data_access"]
        assert data["allowed_tools"] == ["stripe_transfer"]
        assert data["iat"] == 1000
        assert data["exp"] == 2000
        assert data["jti"] == "test-jti"

    def test_claims_with_constraints(self):
        """Test claims with constraints."""
        from datetime import UTC, datetime

        constraints = TokenConstraints(
            amount_max=1000.0,
            jurisdictions=["US", "CA"],
            counterparty_allowlist=["vendor-1"],
        )

        claims = CapabilityTokenClaims(
            iss="gateway",
            sub="agent-123",
            org_id="org-456",
            uapk_id="uapk-789",
            constraints=constraints,
            iat=1000,
            exp=2000,
            jti="test-jti",
        )

        data = claims.to_dict()

        assert "constraints" in data
        assert data["constraints"]["amount_max"] == 1000.0
        assert data["constraints"]["jurisdictions"] == ["US", "CA"]
        assert data["constraints"]["counterparty_allowlist"] == ["vendor-1"]

    def test_claims_from_dict(self):
        """Test claims deserialization from dictionary."""
        data = {
            "iss": "gateway",
            "sub": "agent-123",
            "org_id": "org-456",
            "uapk_id": "uapk-789",
            "allowed_action_types": ["payment"],
            "allowed_tools": ["stripe"],
            "iat": 1000,
            "exp": 2000,
            "jti": "test-jti",
            "constraints": {
                "amount_max": 500.0,
                "jurisdictions": ["US"],
            },
        }

        claims = CapabilityTokenClaims.from_dict(data)

        assert claims.iss == "gateway"
        assert claims.sub == "agent-123"
        assert claims.org_id == "org-456"
        assert claims.constraints is not None
        assert claims.constraints.amount_max == 500.0
        assert claims.constraints.jurisdictions == ["US"]


class TestCapabilityTokenCreation:
    """Test capability token creation and verification."""

    def test_create_and_verify_token(self):
        """Test creating and verifying a token."""
        now = int(time.time())

        claims = CapabilityTokenClaims(
            iss="gateway",
            sub="agent-123",
            org_id=str(uuid4()),
            uapk_id="uapk-789",
            allowed_action_types=["payment"],
            iat=now,
            exp=now + 3600,
            jti="test-jti",
        )

        # Create token
        token = create_capability_token(claims)

        assert token is not None
        assert isinstance(token, str)
        assert token.count(".") == 2  # JWT format: header.payload.signature

        # Verify token
        verified_claims, error = verify_capability_token(token)

        assert error is None
        assert verified_claims is not None
        assert verified_claims.iss == "gateway"
        assert verified_claims.sub == "agent-123"
        assert verified_claims.allowed_action_types == ["payment"]

    def test_expired_token(self):
        """Test that expired tokens are rejected."""
        now = int(time.time())

        claims = CapabilityTokenClaims(
            iss="gateway",
            sub="agent-123",
            org_id=str(uuid4()),
            uapk_id="uapk-789",
            iat=now - 7200,  # Issued 2 hours ago
            exp=now - 3600,  # Expired 1 hour ago
            jti="test-jti",
        )

        token = create_capability_token(claims)

        # Verify should fail
        verified_claims, error = verify_capability_token(token)

        assert error is not None
        assert "expired" in error.lower()

    def test_invalid_signature(self):
        """Test that tokens with invalid signatures are rejected."""
        now = int(time.time())

        claims = CapabilityTokenClaims(
            iss="gateway",
            sub="agent-123",
            org_id=str(uuid4()),
            uapk_id="uapk-789",
            iat=now,
            exp=now + 3600,
            jti="test-jti",
        )

        token = create_capability_token(claims)

        # Tamper with the token
        parts = token.split(".")
        parts[1] = parts[1][:-5] + "XXXXX"  # Modify payload
        tampered_token = ".".join(parts)

        # Verify should fail
        verified_claims, error = verify_capability_token(tampered_token)

        assert error is not None
        assert verified_claims is None

    def test_invalid_token_format(self):
        """Test that malformed tokens are rejected."""
        # Too few parts
        _, error = verify_capability_token("not.a.valid.token.format")
        assert error is not None

        # No parts
        _, error = verify_capability_token("notavalidtoken")
        assert error is not None

    def test_wrong_algorithm(self):
        """Test that tokens with wrong algorithm are rejected."""
        import base64
        import json

        now = int(time.time())

        # Create a token with wrong algorithm header
        header = {"alg": "HS256", "typ": "JWT"}  # Wrong algorithm
        payload = {
            "iss": "gateway",
            "sub": "agent-123",
            "org_id": str(uuid4()),
            "uapk_id": "uapk-789",
            "iat": now,
            "exp": now + 3600,
            "jti": "test-jti",
        }

        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
        fake_sig = base64.urlsafe_b64encode(b"fakesignature").rstrip(b"=").decode()

        token = f"{header_b64}.{payload_b64}.{fake_sig}"

        _, error = verify_capability_token(token)
        assert error is not None
        assert "algorithm" in error.lower() or "unsupported" in error.lower()


class TestOverrideToken:
    """Test override token creation."""

    def test_create_override_token(self):
        """Test creating an override token."""
        from app.core.capability_jwt import create_override_token

        token = create_override_token(
            org_id=str(uuid4()),
            uapk_id="uapk-123",
            agent_id="agent-456",
            action_hash="abc123",
            approval_id="appr-789",
            expires_in_seconds=300,
        )

        assert token is not None
        assert isinstance(token, str)

        # Verify the token
        claims, error = verify_capability_token(token)

        assert error is None
        assert claims is not None
        assert claims.action_hash == "abc123"
        assert claims.approval_id == "appr-789"
        assert "override" in claims.jti
