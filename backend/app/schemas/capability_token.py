"""Pydantic schemas for capability tokens."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TokenConstraints(BaseModel):
    """Constraints for a capability token."""

    max_actions: int | None = Field(None, ge=1)
    max_actions_per_hour: int | None = Field(None, ge=1)
    allowed_parameters: dict[str, Any] | None = None


class CapabilityTokenCreate(BaseModel):
    """Request body for issuing a capability token."""

    org_id: UUID
    agent_id: str = Field(..., min_length=1, max_length=255)
    manifest_id: UUID | None = None
    capabilities: list[str] = Field(..., min_length=1)
    expires_in_seconds: int = Field(3600, ge=60, le=86400 * 30)  # 1 min to 30 days
    constraints: TokenConstraints | None = None


class CapabilityTokenResponse(BaseModel):
    """Response containing capability token information."""

    id: UUID
    token_id: str
    org_id: UUID
    agent_id: str
    manifest_id: UUID | None
    capabilities: list[str]
    issued_at: datetime
    expires_at: datetime
    issued_by: str
    constraints: dict[str, Any] | None
    max_actions: int | None
    actions_used: int
    revoked: bool
    revoked_at: datetime | None
    revoked_reason: str | None

    model_config = {"from_attributes": True}


class CapabilityTokenCreateResponse(BaseModel):
    """Response containing newly created capability token with JWT."""

    token: CapabilityTokenResponse
    jwt: str  # The actual JWT to use for authentication


class CapabilityTokenList(BaseModel):
    """Response containing list of capability tokens."""

    items: list[CapabilityTokenResponse]
    total: int


class CapabilityTokenRevoke(BaseModel):
    """Request body for revoking a capability token."""

    reason: str | None = Field(None, max_length=500)
