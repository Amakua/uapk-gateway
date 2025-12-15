"""Pydantic schemas for interaction records."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.interaction_record import Decision


class PolicyCheck(BaseModel):
    """Result of a single policy check."""

    check: str = Field(..., description="Name of the check performed")
    result: str = Field(..., pattern=r"^(pass|fail|skip|escalate)$")
    details: dict[str, Any] = Field(default_factory=dict)


class PolicyTrace(BaseModel):
    """Structured trace of policy evaluation."""

    checks: list[PolicyCheck] = Field(default_factory=list)
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: int | None = None


class ReasonDetail(BaseModel):
    """Detailed reason for a decision."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class RiskSnapshot(BaseModel):
    """Risk indicators at evaluation time."""

    budget_current: int | None = None
    budget_limit: int | None = None
    budget_percent: float | None = None
    request_amount: float | None = None
    max_amount: float | None = None


class ActionResult(BaseModel):
    """Result of executing an action."""

    success: bool
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    result_hash: str | None = None
    duration_ms: int | None = None


class InteractionRecordResponse(BaseModel):
    """Response containing interaction record information."""

    id: UUID
    record_id: str
    org_id: UUID
    uapk_id: str
    agent_id: str
    capability_token_id: UUID | None = None
    action_type: str
    tool: str
    request: dict[str, Any]
    request_hash: str
    decision: Decision
    decision_reason: str | None = None
    reasons_json: str
    policy_trace_json: str
    risk_snapshot_json: str | None = None
    result: dict[str, Any] | None = None
    result_hash: str | None = None
    duration_ms: int | None = None
    previous_record_hash: str | None = None
    record_hash: str
    gateway_signature: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @property
    def action(self) -> str:
        """Get combined action string."""
        return f"{self.action_type}:{self.tool}"


class InteractionRecordSummary(BaseModel):
    """Summarized view of an interaction record for lists."""

    record_id: str
    uapk_id: str
    agent_id: str
    action_type: str
    tool: str
    decision: Decision
    decision_reason: str | None = None
    record_hash: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InteractionRecordList(BaseModel):
    """Response containing list of interaction records."""

    items: list[InteractionRecordSummary]
    total: int
    has_more: bool = False


class InteractionRecordQuery(BaseModel):
    """Query parameters for filtering interaction records."""

    uapk_id: str | None = None
    agent_id: str | None = None
    action_type: str | None = None
    tool: str | None = None
    decision: Decision | None = None
    start_time: datetime | None = Field(None, alias="from")
    end_time: datetime | None = Field(None, alias="to")
    limit: int = Field(50, ge=1, le=1000)
    offset: int = Field(0, ge=0)


class LogExportRequest(BaseModel):
    """Request to export logs."""

    uapk_id: str = Field(..., description="UAPK ID to export logs for")
    start_time: datetime | None = Field(None, alias="from", description="Start of time range")
    end_time: datetime | None = Field(None, alias="to", description="End of time range")
    include_manifest: bool = Field(True, description="Include manifest snapshot in export")
    format: str = Field("json", pattern=r"^(json|jsonl)$")


class LogExportResponse(BaseModel):
    """Response containing export information."""

    export_id: str
    uapk_id: str
    record_count: int
    start_time: datetime | None
    end_time: datetime | None
    first_record_hash: str | None
    last_record_hash: str | None
    chain_valid: bool
    download_url: str | None = None


class ChainVerificationResult(BaseModel):
    """Result of verifying a log chain."""

    is_valid: bool
    record_count: int
    first_record_id: str | None = None
    last_record_id: str | None = None
    first_record_hash: str | None = None
    last_record_hash: str | None = None
    errors: list[str] = Field(default_factory=list)
    verified_at: datetime


class LogExportBundle(BaseModel):
    """Complete export bundle structure."""

    version: str = "1.0"
    export_id: str
    exported_at: datetime
    uapk_id: str
    org_id: str
    record_count: int
    time_range: dict[str, datetime | None]
    chain_verification: ChainVerificationResult
    manifest_snapshot: dict[str, Any] | None = None
    records: list[dict[str, Any]] = Field(default_factory=list)
