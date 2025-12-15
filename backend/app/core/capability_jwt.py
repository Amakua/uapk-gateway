"""JWT utilities for Ed25519-signed capability tokens."""

import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from app.core.ed25519 import get_gateway_key_manager, public_key_from_base64
from app.core.logging import get_logger

logger = get_logger("core.capability_jwt")


class CapabilityTokenError(Exception):
    """Raised when capability token operations fail."""

    pass


@dataclass
class TokenConstraints:
    """Constraints embedded in a capability token."""

    amount_max: float | None = None
    jurisdictions: list[str] | None = None
    counterparty_allowlist: list[str] | None = None
    counterparty_denylist: list[str] | None = None
    expires_at: datetime | None = None


@dataclass
class CapabilityTokenClaims:
    """Claims in a capability token JWT."""

    iss: str  # Issuer ID
    sub: str  # Agent ID
    org_id: str
    uapk_id: str
    allowed_action_types: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    constraints: TokenConstraints | None = None
    delegation_depth: int | None = None
    iat: int = 0  # Issued at (Unix timestamp)
    exp: int = 0  # Expires at (Unix timestamp)
    jti: str = ""  # JWT ID (unique token identifier)

    # Optional: for override tokens
    action_hash: str | None = None
    approval_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert claims to dictionary for JWT encoding."""
        data: dict[str, Any] = {
            "iss": self.iss,
            "sub": self.sub,
            "org_id": self.org_id,
            "uapk_id": self.uapk_id,
            "iat": self.iat,
            "exp": self.exp,
            "jti": self.jti,
        }

        if self.allowed_action_types:
            data["allowed_action_types"] = self.allowed_action_types

        if self.allowed_tools:
            data["allowed_tools"] = self.allowed_tools

        if self.constraints:
            constraints_dict: dict[str, Any] = {}
            if self.constraints.amount_max is not None:
                constraints_dict["amount_max"] = self.constraints.amount_max
            if self.constraints.jurisdictions:
                constraints_dict["jurisdictions"] = self.constraints.jurisdictions
            if self.constraints.counterparty_allowlist:
                constraints_dict["counterparty_allowlist"] = self.constraints.counterparty_allowlist
            if self.constraints.counterparty_denylist:
                constraints_dict["counterparty_denylist"] = self.constraints.counterparty_denylist
            if self.constraints.expires_at:
                constraints_dict["expires_at"] = int(self.constraints.expires_at.timestamp())
            if constraints_dict:
                data["constraints"] = constraints_dict

        if self.delegation_depth is not None:
            data["delegation_depth"] = self.delegation_depth

        if self.action_hash:
            data["action_hash"] = self.action_hash

        if self.approval_id:
            data["approval_id"] = self.approval_id

        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CapabilityTokenClaims":
        """Create claims from dictionary."""
        constraints = None
        if "constraints" in data:
            c = data["constraints"]
            expires_at = None
            if "expires_at" in c:
                expires_at = datetime.fromtimestamp(c["expires_at"], tz=UTC)
            constraints = TokenConstraints(
                amount_max=c.get("amount_max"),
                jurisdictions=c.get("jurisdictions"),
                counterparty_allowlist=c.get("counterparty_allowlist"),
                counterparty_denylist=c.get("counterparty_denylist"),
                expires_at=expires_at,
            )

        return cls(
            iss=data["iss"],
            sub=data["sub"],
            org_id=data["org_id"],
            uapk_id=data["uapk_id"],
            allowed_action_types=data.get("allowed_action_types", []),
            allowed_tools=data.get("allowed_tools", []),
            constraints=constraints,
            delegation_depth=data.get("delegation_depth"),
            iat=data.get("iat", 0),
            exp=data.get("exp", 0),
            jti=data.get("jti", ""),
            action_hash=data.get("action_hash"),
            approval_id=data.get("approval_id"),
        )


def _base64url_encode(data: bytes) -> str:
    """Base64url encode without padding."""
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _base64url_decode(data: str) -> bytes:
    """Base64url decode with padding restoration."""
    import base64

    # Add padding if needed
    padding = 4 - len(data) % 4
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data)


def create_capability_token(
    claims: CapabilityTokenClaims,
    private_key: Ed25519PrivateKey | None = None,
) -> str:
    """Create a signed capability token JWT.

    Uses Ed25519 for signing (EdDSA algorithm).
    """
    if private_key is None:
        key_manager = get_gateway_key_manager()
        private_key = key_manager.private_key

    # Build JWT header
    header = {"alg": "EdDSA", "typ": "JWT"}
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode())

    # Build payload
    payload_b64 = _base64url_encode(
        json.dumps(claims.to_dict(), separators=(",", ":")).encode()
    )

    # Create signature
    signing_input = f"{header_b64}.{payload_b64}"
    signature = private_key.sign(signing_input.encode())
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_capability_token(
    token: str,
    public_key: Ed25519PublicKey | None = None,
    issuer_public_keys: dict[str, Ed25519PublicKey] | None = None,
) -> tuple[CapabilityTokenClaims | None, str | None]:
    """Verify and decode a capability token.

    Args:
        token: The JWT string
        public_key: Optional specific public key to verify against
        issuer_public_keys: Optional dict of issuer_id -> public_key

    Returns:
        (claims, error): Claims if valid, error message if invalid
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None, "Invalid token format"

        header_b64, payload_b64, signature_b64 = parts

        # Decode header
        try:
            header = json.loads(_base64url_decode(header_b64))
        except Exception:
            return None, "Invalid header encoding"

        if header.get("alg") != "EdDSA":
            return None, f"Unsupported algorithm: {header.get('alg')}"

        # Decode payload
        try:
            payload = json.loads(_base64url_decode(payload_b64))
        except Exception:
            return None, "Invalid payload encoding"

        # Decode signature
        try:
            signature = _base64url_decode(signature_b64)
        except Exception:
            return None, "Invalid signature encoding"

        # Get claims for issuer lookup
        claims = CapabilityTokenClaims.from_dict(payload)

        # Determine which public key to use
        verify_key = public_key
        if verify_key is None:
            if issuer_public_keys and claims.iss in issuer_public_keys:
                verify_key = issuer_public_keys[claims.iss]
            elif claims.iss == "gateway":
                # Use gateway's public key
                key_manager = get_gateway_key_manager()
                verify_key = key_manager.public_key
            else:
                return None, f"Unknown issuer: {claims.iss}"

        # Verify signature
        signing_input = f"{header_b64}.{payload_b64}"
        try:
            verify_key.verify(signature, signing_input.encode())
        except Exception:
            return None, "Invalid signature"

        # Check expiration
        now = int(time.time())
        if claims.exp > 0 and now > claims.exp:
            return None, "Token expired"

        return claims, None

    except Exception as e:
        logger.warning("capability_token_verification_failed", error=str(e))
        return None, f"Token verification failed: {e}"


def create_override_token(
    org_id: str,
    uapk_id: str,
    agent_id: str,
    action_hash: str,
    approval_id: str,
    expires_in_seconds: int = 300,
) -> str:
    """Create a short-lived override token for an approved action.

    This token allows exactly one action (identified by action_hash)
    to bypass normal policy checks.
    """
    import secrets

    now = int(time.time())

    claims = CapabilityTokenClaims(
        iss="gateway",
        sub=agent_id,
        org_id=org_id,
        uapk_id=uapk_id,
        iat=now,
        exp=now + expires_in_seconds,
        jti=f"override-{secrets.token_hex(8)}",
        action_hash=action_hash,
        approval_id=approval_id,
    )

    return create_capability_token(claims)
