"""Tests for security utilities."""

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_api_key,
    get_api_key_prefix,
    hash_api_key,
    hash_password,
    verify_api_key,
    verify_password,
)


def test_hash_password() -> None:
    """Test password hashing."""
    password = "testpassword123"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2b$")  # bcrypt prefix


def test_verify_password_correct() -> None:
    """Test password verification with correct password."""
    password = "testpassword123"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_incorrect() -> None:
    """Test password verification with incorrect password."""
    password = "testpassword123"
    hashed = hash_password(password)

    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token() -> None:
    """Test JWT token creation."""
    token = create_access_token(subject="user-123")

    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token_valid() -> None:
    """Test decoding a valid JWT token."""
    token = create_access_token(subject="user-123", extra_claims={"email": "test@example.com"})
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["email"] == "test@example.com"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_access_token_invalid() -> None:
    """Test decoding an invalid JWT token."""
    payload = decode_access_token("invalid-token")

    assert payload is None


def test_generate_api_key() -> None:
    """Test API key generation."""
    key = generate_api_key()

    assert key.startswith("uapk_")
    assert len(key) == 37  # uapk_ + 32 hex chars


def test_generate_api_key_uniqueness() -> None:
    """Test that generated API keys are unique."""
    keys = [generate_api_key() for _ in range(100)]

    assert len(set(keys)) == 100  # All unique


def test_get_api_key_prefix() -> None:
    """Test extracting API key prefix."""
    key = "uapk_abcd1234efgh5678"
    prefix = get_api_key_prefix(key)

    assert prefix == "uapk_abcd123"
    assert len(prefix) == 12


def test_hash_api_key() -> None:
    """Test API key hashing."""
    key = generate_api_key()
    hashed = hash_api_key(key)

    assert hashed != key
    assert hashed.startswith("$2b$")  # bcrypt prefix


def test_verify_api_key_correct() -> None:
    """Test API key verification with correct key."""
    key = generate_api_key()
    hashed = hash_api_key(key)

    assert verify_api_key(key, hashed) is True


def test_verify_api_key_incorrect() -> None:
    """Test API key verification with incorrect key."""
    key = generate_api_key()
    hashed = hash_api_key(key)
    other_key = generate_api_key()

    assert verify_api_key(other_key, hashed) is False
