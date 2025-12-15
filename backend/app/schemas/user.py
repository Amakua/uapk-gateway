"""Pydantic schemas for users."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Request body for creating a user."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """Request body for updating a user."""

    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Response containing user information."""

    id: UUID
    email: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None

    model_config = {"from_attributes": True}


class UserList(BaseModel):
    """Response containing list of users."""

    items: list[UserResponse]
    total: int
