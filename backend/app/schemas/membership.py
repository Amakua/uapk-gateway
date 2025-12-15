"""Pydantic schemas for memberships."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.membership import MembershipRole


class MembershipCreate(BaseModel):
    """Request body for creating a membership."""

    user_id: UUID
    role: MembershipRole = MembershipRole.VIEWER


class MembershipUpdate(BaseModel):
    """Request body for updating a membership."""

    role: MembershipRole


class MembershipResponse(BaseModel):
    """Response containing membership information."""

    id: UUID
    org_id: UUID
    user_id: UUID
    role: MembershipRole
    created_at: datetime
    user_email: str | None = None  # Populated when joining with user

    model_config = {"from_attributes": True}


class MembershipList(BaseModel):
    """Response containing list of memberships."""

    items: list[MembershipResponse]
    total: int
