"""Pydantic schemas for policies."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.policy import PolicyScope, PolicyType


class PolicyRules(BaseModel):
    """Rules for policy matching and evaluation."""

    action_pattern: str | None = Field(
        None,
        description="Glob pattern to match actions (e.g., 'email:*', 'file:read')",
    )
    agent_ids: list[str] | None = Field(
        None,
        description="Specific agent IDs this policy applies to",
    )
    parameters: dict[str, Any] | None = Field(
        None,
        description="Parameter constraints for matching",
    )
    time_range: dict[str, Any] | None = Field(
        None,
        description="Time-based constraints",
    )


class PolicyCreate(BaseModel):
    """Request body for creating a policy."""

    org_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    policy_type: PolicyType
    scope: PolicyScope = PolicyScope.GLOBAL
    priority: int = Field(0, ge=-1000, le=1000)
    rules: PolicyRules
    enabled: bool = True


class PolicyUpdate(BaseModel):
    """Request body for updating a policy."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    policy_type: PolicyType | None = None
    scope: PolicyScope | None = None
    priority: int | None = Field(None, ge=-1000, le=1000)
    rules: PolicyRules | None = None
    enabled: bool | None = None


class PolicyResponse(BaseModel):
    """Response containing policy information."""

    id: UUID
    org_id: UUID
    name: str
    description: str | None
    policy_type: PolicyType
    scope: PolicyScope
    priority: int
    rules: dict[str, Any]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by_user_id: UUID | None

    model_config = {"from_attributes": True}


class PolicyList(BaseModel):
    """Response containing list of policies."""

    items: list[PolicyResponse]
    total: int
