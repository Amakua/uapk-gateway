"""Pydantic schemas for capability issuers and token issuance."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.capability_issuer import IssuerStatus


class IssuerCreate(BaseModel):
    """Request body for registering a capability issuer."""

    issuer_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    public_key: str = Field(..., description="Base64-encoded Ed25519 public key")
    description: str | None = Field(None, max_length=1000)


class IssuerResponse(BaseModel):
    """Response containing issuer information."""

    id: UUID
    org_id: UUID
    issuer_id: str
    name: str
    public_key: str
    description: str | None
    status: IssuerStatus
    created_at: datetime
    revoked_at: datetime | None
    created_by_user_id: UUID | None

    model_config = {"from_attributes": True}


class IssuerList(BaseModel):
    """Response containing list of issuers."""

    items: list[IssuerResponse]
    total: int


class TokenConstraintsRequest(BaseModel):
    """Constraints to embed in a capability token."""

    amount_max: float | None = Field(None, ge=0)
    jurisdictions: list[str] | None = Field(None, description="Allowed jurisdictions (ISO codes)")
    counterparty_allowlist: list[str] | None = None
    counterparty_denylist: list[str] | None = None
    expires_at: datetime | None = None


class IssueTokenRequest(BaseModel):
    """Request body for issuing a capability token."""

    agent_id: str = Field(..., min_length=1, max_length=255)
    uapk_id: str = Field(..., min_length=1, max_length=255)
    allowed_action_types: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    constraints: TokenConstraintsRequest | None = None
    delegation_depth: int | None = Field(None, ge=0, le=10)
    expires_in_seconds: int = Field(3600, ge=60, le=86400 * 30)  # 1 min to 30 days


class IssueTokenResponse(BaseModel):
    """Response containing issued capability token."""

    token: str = Field(..., description="The signed JWT capability token")
    token_id: str = Field(..., description="Unique token identifier (jti)")
    issuer_id: str
    agent_id: str
    uapk_id: str
    org_id: str
    issued_at: datetime
    expires_at: datetime
    allowed_action_types: list[str]
    allowed_tools: list[str]
    constraints: dict[str, Any] | None


class GatewayPublicKeyResponse(BaseModel):
    """Response containing gateway's public key."""

    issuer_id: str = "gateway"
    public_key: str = Field(..., description="Base64-encoded Ed25519 public key")
    algorithm: str = "EdDSA"
