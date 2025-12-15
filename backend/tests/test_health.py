"""Tests for health check endpoints."""

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    """Test the health check endpoint."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz(client: TestClient) -> None:
    """Test the readiness check endpoint."""
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_api_v1_healthz(client: TestClient) -> None:
    """Test the versioned health check endpoint."""
    response = client.get("/api/v1/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_api_v1_readyz(client: TestClient) -> None:
    """Test the versioned readiness check endpoint."""
    response = client.get("/api/v1/readyz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data


def test_openapi_docs(client: TestClient) -> None:
    """Test that OpenAPI docs are available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert data["info"]["title"] == "UAPK Gateway"
