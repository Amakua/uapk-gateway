"""Tests for authentication endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User) -> None:
    """Test successful login returns JWT token."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_invalid_email(client: AsyncClient) -> None:
    """Test login with non-existent email fails."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, test_user: User) -> None:
    """Test login with wrong password fails."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_inactive_user(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """Test login with inactive user fails."""
    test_user.is_active = False
    await db_session.flush()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(
    client: AsyncClient,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    """Test getting current user info while authenticated."""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["is_active"] is True
    assert "organizations" in data


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient) -> None:
    """Test getting current user info without authentication fails."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient) -> None:
    """Test getting current user info with invalid token fails."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_with_orgs(
    client: AsyncClient,
    test_user_with_org: tuple,
    auth_headers_with_org: dict[str, str],
) -> None:
    """Test getting current user info includes organization memberships."""
    user, org, membership = test_user_with_org

    response = await client.get("/api/v1/auth/me", headers=auth_headers_with_org)
    assert response.status_code == 200
    data = response.json()
    assert len(data["organizations"]) == 1
    assert data["organizations"][0]["org_slug"] == "test-org"
    assert data["organizations"][0]["role"] == "owner"
