"""Pydantic schemas for approval workflow."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.approval import ApprovalStatus


class ApprovalResponse(BaseModel):
    """Response containing approval task information."""

    id: UUID
    approval_id: str
    org_id: UUID
    interaction_id: str
    uapk_id: str
    agent_id: str
    action: dict[str, Any]
    counterparty: dict[str, Any] | None
    context: dict[str, Any] | None
    reason_codes: list[str]
    status: ApprovalStatus
    created_at: datetime
    expires_at: datetime | None
    decided_at: datetime | None
    decided_by: str | None
    decision_notes: str | None

    model_config = {"from_attributes": True}


class ApprovalList(BaseModel):
    """Response containing list of approvals."""

    items: list[ApprovalResponse]
    total: int
    pending_count: int


class ApproveRequest(BaseModel):
    """Request to approve an action."""

    notes: str | None = Field(None, max_length=1000)
    override_token_expires_in_seconds: int = Field(
        300,
        ge=60,
        le=3600,
        description="How long the override token is valid (1-60 minutes)",
    )


class DenyRequest(BaseModel):
    """Request to deny an action."""

    notes: str | None = Field(None, max_length=1000)
    reason: str | None = Field(None, max_length=255)


class ApprovalDecisionResponse(BaseModel):
    """Response after approving or denying."""

    approval_id: str
    status: ApprovalStatus
    decided_at: datetime
    decided_by: str
    # Only present when approved
    override_token: str | None = Field(
        None,
        description="Override token to use for retrying the action (only on approval)",
    )
    override_token_expires_at: datetime | None = None


class ApprovalStats(BaseModel):
    """Statistics about approvals."""

    pending: int
    approved: int
    denied: int
    expired: int
    total: int
