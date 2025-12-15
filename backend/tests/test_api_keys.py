"""Tests for API key endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership
from app.models.organization import Organization
from app.models.user import User


@pytest.mark.asyncio
async def test_create_api_key_success(
    client: AsyncClient,
    test_user_with_org: tuple[User, Organization, Membership],
    auth_headers_with_org: dict[str, str],
) -> None:
    """Test creating an API key returns the full key once."""
    user, org, _ = test_user_with_org

    response = await client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key", "org_id": str(org.id)},
        headers=auth_headers_with_org,
    )
    assert response.status_code == 201
    data = response.json()

    # Should have the full key
    assert "key" in data
    assert data["key"].startswith("uapk_")
    assert len(data["key"]) == 37  # uapk_ + 32 hex chars

    # Should have key_prefix
    assert "key_prefix" in data
    assert data["key"].startswith(data["key_prefix"])

    # Other fields
    assert data["name"] == "Test Key"
    assert data["status"] == "active"
    assert str(data["org_id"]) == str(org.id)


@pytest.mark.asyncio
async def test_create_api_key_unauthorized(
    client: AsyncClient,
    test_org: Organization,
    auth_headers: dict[str, str],
) -> None:
    """Test creating an API key without org membership fails."""
    response = await client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key", "org_id": str(test_org.id)},
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_api_key_unauthenticated(
    client: AsyncClient,
    test_org: Organization,
) -> None:
    """Test creating an API key without authentication fails."""
    response = await client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key", "org_id": str(test_org.id)},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_api_keys(
    client: AsyncClient,
    test_user_with_org: tuple[User, Organization, Membership],
    auth_headers_with_org: dict[str, str],
) -> None:
    """Test listing API keys returns keys without full key value."""
    user, org, _ = test_user_with_org

    # Create a key first
    create_response = await client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key", "org_id": str(org.id)},
        headers=auth_headers_with_org,
    )
    assert create_response.status_code == 201

    # List keys
    response = await client.get("/api/v1/api-keys", headers=auth_headers_with_org)
    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1

    # The list should NOT contain the full key
    for key in data["items"]:
        assert "key" not in key
        assert "key_prefix" in key


@pytest.mark.asyncio
async def test_list_api_keys_by_org(
    client: AsyncClient,
    test_user_with_org: tuple[User, Organization, Membership],
    auth_headers_with_org: dict[str, str],
) -> None:
    """Test listing API keys filtered by organization."""
    user, org, _ = test_user_with_org

    # Create a key
    await client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key", "org_id": str(org.id)},
        headers=auth_headers_with_org,
    )

    # List keys for specific org
    response = await client.get(
        f"/api/v1/api-keys?org_id={org.id}",
        headers=auth_headers_with_org,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_revoke_api_key(
    client: AsyncClient,
    test_user_with_org: tuple[User, Organization, Membership],
    auth_headers_with_org: dict[str, str],
) -> None:
    """Test revoking an API key."""
    user, org, _ = test_user_with_org

    # Create a key
    create_response = await client.post(
        "/api/v1/api-keys",
        json={"name": "Test Key", "org_id": str(org.id)},
        headers=auth_headers_with_org,
    )
    key_id = create_response.json()["id"]

    # Revoke the key
    response = await client.post(
        f"/api/v1/api-keys/{key_id}/revoke",
        headers=auth_headers_with_org,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "revoked"


@pytest.mark.asyncio
async def test_revoke_api_key_not_found(
    client: AsyncClient,
    auth_headers_with_org: dict[str, str],
) -> None:
    """Test revoking a non-existent API key fails."""
    from uuid import uuid4

    response = await client.post(
        f"/api/v1/api-keys/{uuid4()}/revoke",
        headers=auth_headers_with_org,
    )
    assert response.status_code == 404
