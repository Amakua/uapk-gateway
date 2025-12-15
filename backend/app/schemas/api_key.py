"""Pydantic schemas for API keys."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.api_key import ApiKeyStatus


class ApiKeyCreate(BaseModel):
    """Request body for creating an API key."""

    name: str = Field(..., min_length=1, max_length=255)
    org_id: UUID


class ApiKeyCreateResponse(BaseModel):
    """Response containing newly created API key.

    IMPORTANT: The full key is only returned once at creation time.
    """

    id: UUID
    org_id: UUID
    name: str
    key_prefix: str
    key: str  # Full key - only shown once!
    status: ApiKeyStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyResponse(BaseModel):
    """Response containing API key information (without full key)."""

    id: UUID
    org_id: UUID
    name: str
    key_prefix: str
    status: ApiKeyStatus
    created_at: datetime
    last_used_at: datetime | None

    model_config = {"from_attributes": True}


class ApiKeyList(BaseModel):
    """Response containing list of API keys."""

    items: list[ApiKeyResponse]
    total: int
