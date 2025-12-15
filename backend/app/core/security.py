"""Security utilities for password hashing and JWT tokens."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Optional custom expiration time
        extra_claims: Optional extra claims to include in the token

    Returns:
        Encoded JWT token string
    """
    settings = get_settings()

    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expiration_minutes)

    to_encode: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
    }

    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token.

    Args:
        token: The JWT token string

    Returns:
        Token payload if valid, None otherwise
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None


def generate_api_key() -> str:
    """Generate a secure random API key.

    Format: uapk_{32 random hex characters}
    Total length: 37 characters
    """
    return f"uapk_{secrets.token_hex(16)}"


def get_api_key_prefix(api_key: str) -> str:
    """Extract the prefix from an API key for identification.

    Returns first 12 characters (e.g., "uapk_abc123...")
    """
    return api_key[:12]


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage.

    Uses bcrypt like passwords for consistency.
    """
    return pwd_context.hash(api_key)


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return pwd_context.verify(plain_key, hashed_key)


def create_capability_token_jwt(
    token_id: str,
    agent_id: str,
    org_id: str,
    capabilities: list[str],
    expires_at: datetime,
) -> str:
    """Create a JWT for a capability token.

    This JWT is used by agents to authenticate action requests.
    """
    settings = get_settings()

    to_encode: dict[str, Any] = {
        "sub": token_id,
        "agent_id": agent_id,
        "org_id": org_id,
        "capabilities": capabilities,
        "exp": expires_at,
        "iat": datetime.now(UTC),
        "type": "capability_token",
    }

    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_capability_token_jwt(token: str) -> dict[str, Any] | None:
    """Decode and validate a capability token JWT.

    Returns:
        Token payload if valid, None otherwise
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        # Verify it's a capability token
        if payload.get("type") != "capability_token":
            return None
        return payload
    except JWTError:
        return None


def generate_record_id() -> str:
    """Generate a unique record ID for interaction records.

    Format: ir-{20 random hex characters}
    """
    return f"ir-{secrets.token_hex(10)}"


def compute_record_signature(record_data: dict, secret_key: str | None = None) -> str:
    """Compute HMAC signature for an interaction record.

    This provides tamper-evidence for audit logs.
    """
    import hashlib
    import hmac
    import json

    if secret_key is None:
        settings = get_settings()
        secret_key = settings.secret_key

    # Create canonical representation
    canonical = json.dumps(record_data, sort_keys=True, separators=(",", ":"))
    signature = hmac.new(
        secret_key.encode(),
        canonical.encode(),
        hashlib.sha256,
    ).hexdigest()

    return signature
