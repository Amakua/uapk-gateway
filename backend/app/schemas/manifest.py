"""Pydantic schemas for UAPK manifests."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.uapk_manifest import ManifestStatus


class AgentInfo(BaseModel):
    """Agent identification from manifest."""

    id: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]{2,62}$")
    name: str = Field(..., min_length=1, max_length=100)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+")
    description: str | None = Field(None, max_length=500)
    organization: str | None = Field(None, pattern=r"^org-[a-z0-9-]+$")
    team: str | None = Field(None, pattern=r"^team-[a-z0-9-]+$")


class CapabilityDeclaration(BaseModel):
    """Capability declarations from manifest."""

    requested: list[str] = Field(..., min_length=1)


class ManifestConstraints(BaseModel):
    """Self-imposed constraints from manifest."""

    max_actions_per_hour: int | None = Field(None, ge=1)
    max_actions_per_day: int | None = Field(None, ge=1)
    require_human_approval: list[str] | None = None
    allowed_hours: dict[str, Any] | None = None


class ManifestMetadata(BaseModel):
    """Additional manifest metadata."""

    contact: str | None = None
    documentation: str | None = None
    source: str | None = None


class ManifestContent(BaseModel):
    """The actual UAPK manifest content."""

    version: str = Field("1.0", pattern=r"^1\.0$")
    agent: AgentInfo
    capabilities: CapabilityDeclaration
    constraints: ManifestConstraints | None = None
    metadata: ManifestMetadata | None = None


class ManifestCreate(BaseModel):
    """Request body for registering a manifest."""

    org_id: UUID
    manifest: ManifestContent
    description: str | None = Field(None, max_length=500)


class ManifestUpdate(BaseModel):
    """Request body for updating a manifest status."""

    status: ManifestStatus | None = None
    description: str | None = Field(None, max_length=500)


class ManifestResponse(BaseModel):
    """Response containing manifest information."""

    id: UUID
    org_id: UUID
    uapk_id: str
    version: str
    manifest_json: dict[str, Any]
    manifest_hash: str
    status: ManifestStatus
    description: str | None
    created_at: datetime
    created_by_user_id: UUID | None

    model_config = {"from_attributes": True}


class ManifestList(BaseModel):
    """Response containing list of manifests."""

    items: list[ManifestResponse]
    total: int
