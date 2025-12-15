"""Pydantic schemas for authentication."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Request body for login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response containing JWT token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserResponse(BaseModel):
    """Response containing user information."""

    id: UUID
    email: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class UserWithOrgsResponse(BaseModel):
    """User response with organization memberships."""

    id: UUID
    email: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    organizations: list["OrgMembershipInfo"]

    model_config = {"from_attributes": True}


class OrgMembershipInfo(BaseModel):
    """Organization membership info for user response."""

    org_id: UUID
    org_name: str
    org_slug: str
    role: str

    model_config = {"from_attributes": True}
