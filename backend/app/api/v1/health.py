"""Health check endpoints."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: Literal["ok", "degraded", "unhealthy"]
    version: str


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    status: Literal["ready", "not_ready"]
    checks: dict[str, bool]


@router.get("/healthz", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns the current health status of the service.
    Used by load balancers and orchestrators for liveness probes.
    """
    from app import __version__

    return HealthResponse(status="ok", version=__version__)


@router.get("/readyz", response_model=ReadinessResponse)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check endpoint.

    Returns whether the service is ready to accept traffic.
    Checks database connectivity and other dependencies.
    """
    checks: dict[str, bool] = {}

    # TODO: Add actual database connectivity check
    checks["database"] = True

    all_ready = all(checks.values())

    return ReadinessResponse(
        status="ready" if all_ready else "not_ready",
        checks=checks,
    )
