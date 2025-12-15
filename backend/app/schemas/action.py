"""Pydantic schemas for the gateway action endpoint."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.interaction_record import Decision


class ActionContext(BaseModel):
    """Context for an action request."""

    conversation_id: str | None = None
    reason: str | None = Field(None, max_length=1000)
    metadata: dict[str, Any] | None = None


class ActionRequest(BaseModel):
    """Request body for an agent action.

    This is the core gateway endpoint where agents POST action requests.
    The gateway evaluates policies, enforces capabilities, and logs the interaction.
    """

    action: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9-]*:[a-z][a-z0-9-]*$",
        description="Action to perform (e.g., 'email:send', 'file:read')",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific parameters",
    )
    context: ActionContext | None = Field(
        None,
        description="Optional context for the action",
    )
    idempotency_key: str | None = Field(
        None,
        max_length=64,
        description="Optional key for idempotent requests",
    )


class PolicyEvaluationResult(BaseModel):
    """Result of a single policy evaluation."""

    policy_id: str
    policy_name: str
    result: str  # "pass", "fail", or "skip"
    reason: str | None = None


class ActionResponse(BaseModel):
    """Response from the gateway action endpoint."""

    record_id: str = Field(
        ...,
        description="Unique ID for this interaction record",
    )
    decision: Decision = Field(
        ...,
        description="Policy decision: approved, denied, pending, or timeout",
    )
    decision_reason: str | None = Field(
        None,
        description="Explanation for the decision",
    )
    policy_evaluations: list[PolicyEvaluationResult] | None = Field(
        None,
        description="Results of policy evaluations",
    )
    result: dict[str, Any] | None = Field(
        None,
        description="Action result (if approved and executed)",
    )
    timestamp: datetime = Field(
        ...,
        description="When the request was processed",
    )
    duration_ms: int = Field(
        ...,
        description="Processing time in milliseconds",
    )


class ActionDeniedResponse(BaseModel):
    """Response when an action is denied."""

    record_id: str
    decision: Decision = Decision.DENIED
    decision_reason: str
    policy_evaluations: list[PolicyEvaluationResult] | None = None
    timestamp: datetime
    duration_ms: int


class ActionPendingResponse(BaseModel):
    """Response when an action requires human approval."""

    record_id: str
    decision: Decision = Decision.PENDING
    decision_reason: str = "Human approval required"
    approval_url: str | None = Field(
        None,
        description="URL where the action can be approved",
    )
    timestamp: datetime
    duration_ms: int
