"""Pydantic schemas for organizations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    """Request body for creating an organization."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class OrganizationResponse(BaseModel):
    """Response containing organization information."""

    id: UUID
    name: str
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}


class OrganizationList(BaseModel):
    """Response containing list of organizations."""

    items: list[OrganizationResponse]
    total: int
