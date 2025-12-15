"""Pydantic schemas for the Agent Interaction Gateway."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class GatewayDecision(str, Enum):
    """Decision from the gateway policy engine."""

    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"


class ReasonCode(str, Enum):
    """Reason codes for gateway decisions."""

    # Allow reasons
    POLICY_PASSED = "policy_passed"
    ALL_CHECKS_PASSED = "all_checks_passed"

    # Deny reasons
    MANIFEST_NOT_FOUND = "manifest_not_found"
    MANIFEST_NOT_ACTIVE = "manifest_not_active"
    ACTION_TYPE_NOT_ALLOWED = "action_type_not_allowed"
    TOOL_NOT_ALLOWED = "tool_not_allowed"
    AMOUNT_EXCEEDS_CAP = "amount_exceeds_cap"
    JURISDICTION_NOT_ALLOWED = "jurisdiction_not_allowed"
    COUNTERPARTY_DENIED = "counterparty_denied"
    COUNTERPARTY_NOT_IN_ALLOWLIST = "counterparty_not_in_allowlist"
    BUDGET_EXCEEDED = "budget_exceeded"
    CAPABILITY_NOT_GRANTED = "capability_not_granted"
    INVALID_REQUEST = "invalid_request"

    # Capability token deny reasons
    CAPABILITY_TOKEN_INVALID = "capability_token_invalid"
    CAPABILITY_TOKEN_EXPIRED = "capability_token_expired"
    TOKEN_ISSUER_REVOKED = "token_issuer_revoked"
    TOKEN_AGENT_MISMATCH = "token_agent_mismatch"
    TOKEN_ORG_MISMATCH = "token_org_mismatch"
    TOKEN_UAPK_MISMATCH = "token_uapk_mismatch"
    TOKEN_ACTION_TYPE_NOT_ALLOWED = "token_action_type_not_allowed"
    TOKEN_TOOL_NOT_ALLOWED = "token_tool_not_allowed"
    TOKEN_AMOUNT_EXCEEDS_CAP = "token_amount_exceeds_cap"
    TOKEN_JURISDICTION_NOT_ALLOWED = "token_jurisdiction_not_allowed"
    TOKEN_COUNTERPARTY_NOT_ALLOWED = "token_counterparty_not_allowed"

    # Escalate reasons
    REQUIRES_HUMAN_APPROVAL = "requires_human_approval"
    AMOUNT_REQUIRES_APPROVAL = "amount_requires_approval"
    BUDGET_THRESHOLD_REACHED = "budget_threshold_reached"


class ActionInfo(BaseModel):
    """Action being requested by the agent."""

    type: str = Field(
        ...,
        description="Action type (e.g., 'payment', 'data_access', 'notification')",
    )
    tool: str = Field(
        ...,
        description="Tool to execute (e.g., 'stripe_transfer', 'email_send')",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the tool",
    )


class CounterpartyInfo(BaseModel):
    """Information about the counterparty in the action."""

    id: str | None = Field(None, description="Counterparty identifier")
    type: str | None = Field(None, description="Counterparty type (e.g., 'user', 'merchant')")
    jurisdiction: str | None = Field(None, description="ISO country code")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class GatewayActionRequest(BaseModel):
    """Request to the gateway for action evaluation or execution."""

    uapk_id: str = Field(
        ...,
        description="UAPK manifest ID identifying the agent",
    )
    agent_id: str = Field(
        ...,
        description="Specific agent instance ID",
    )
    action: ActionInfo = Field(
        ...,
        description="The action to evaluate/execute",
    )
    capability_token: str | None = Field(
        None,
        description="Optional capability token for additional authorization",
    )
    counterparty: CounterpartyInfo | None = Field(
        None,
        description="Optional counterparty information",
    )
    context: dict[str, Any] | None = Field(
        None,
        description="Optional context (conversation_id, reason, etc.)",
    )
    idempotency_key: str | None = Field(
        None,
        max_length=64,
        description="Optional key for idempotent requests",
    )


class ReasonDetail(BaseModel):
    """Detailed reason for a decision."""

    code: ReasonCode
    message: str
    details: dict[str, Any] | None = None


class GatewayDecisionResponse(BaseModel):
    """Response from the gateway evaluate endpoint."""

    interaction_id: str = Field(
        ...,
        description="Unique ID for this interaction",
    )
    decision: GatewayDecision = Field(
        ...,
        description="The policy decision",
    )
    reasons: list[ReasonDetail] = Field(
        default_factory=list,
        description="Reasons for the decision",
    )
    approval_id: str | None = Field(
        None,
        description="Approval task ID if decision is ESCALATE",
    )
    timestamp: datetime = Field(
        ...,
        description="When the decision was made",
    )
    policy_version: str | None = Field(
        None,
        description="Version of the policy that was applied",
    )


class ToolResult(BaseModel):
    """Result from executing a tool."""

    success: bool
    data: dict[str, Any] | None = None
    error: dict[str, str] | None = None
    result_hash: str | None = Field(
        None,
        description="SHA-256 hash of the result for audit purposes",
    )
    duration_ms: int | None = None


class GatewayExecuteResponse(BaseModel):
    """Response from the gateway execute endpoint."""

    interaction_id: str
    decision: GatewayDecision
    reasons: list[ReasonDetail] = Field(default_factory=list)
    approval_id: str | None = None
    timestamp: datetime
    policy_version: str | None = None
    # Execute-specific fields
    executed: bool = Field(
        False,
        description="Whether the tool was actually executed",
    )
    result: ToolResult | None = Field(
        None,
        description="Result from tool execution (only if executed)",
    )


class ApprovalStatus(str, Enum):
    """Status of an approval task."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class ApprovalTaskResponse(BaseModel):
    """Response containing approval task information."""

    id: UUID
    approval_id: str
    org_id: UUID
    uapk_id: str
    agent_id: str
    action: dict[str, Any]
    counterparty: dict[str, Any] | None
    status: ApprovalStatus
    reason_codes: list[str]
    created_at: datetime
    expires_at: datetime | None
    decided_at: datetime | None
    decided_by: str | None
    decision_notes: str | None

    model_config = {"from_attributes": True}
