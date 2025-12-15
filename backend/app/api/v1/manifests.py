"""Manifest API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, RequireOrgAdmin, RequireOrgOperator
from app.models.uapk_manifest import ManifestStatus
from app.schemas.manifest import (
    ManifestCreate,
    ManifestList,
    ManifestResponse,
    ManifestUpdate,
)
from app.services.manifest import ManifestService

router = APIRouter(prefix="/orgs/{org_id}/manifests", tags=["Manifests"])


@router.post("", response_model=ManifestResponse, status_code=status.HTTP_201_CREATED)
async def create_manifest(
    org_id: UUID,
    data: ManifestCreate,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgOperator],
) -> ManifestResponse:
    """Register a new UAPK manifest for an agent.

    Creates a new manifest in PENDING status. The manifest must be activated
    before the agent can request capability tokens.
    """
    # Ensure org_id matches
    if data.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="org_id in path must match org_id in body",
        )

    manifest_service = ManifestService(db)
    manifest = await manifest_service.create_manifest(data, user_id=user.id)
    return ManifestResponse.model_validate(manifest)


@router.get("", response_model=ManifestList)
async def list_manifests(
    org_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgOperator],
    manifest_status: ManifestStatus | None = Query(None, alias="status"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ManifestList:
    """List manifests for an organization."""
    manifest_service = ManifestService(db)
    return await manifest_service.list_manifests(
        org_id=org_id,
        status=manifest_status,
        limit=limit,
        offset=offset,
    )


@router.get("/{manifest_id}", response_model=ManifestResponse)
async def get_manifest(
    org_id: UUID,
    manifest_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgOperator],
) -> ManifestResponse:
    """Get a specific manifest."""
    manifest_service = ManifestService(db)
    manifest = await manifest_service.get_manifest_by_id(manifest_id)

    if manifest is None or manifest.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found",
        )

    return ManifestResponse.model_validate(manifest)


@router.patch("/{manifest_id}", response_model=ManifestResponse)
async def update_manifest(
    org_id: UUID,
    manifest_id: UUID,
    data: ManifestUpdate,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> ManifestResponse:
    """Update a manifest's status or description.

    Requires ADMIN role to change status.
    """
    manifest_service = ManifestService(db)

    # Check manifest exists and belongs to org
    existing = await manifest_service.get_manifest_by_id(manifest_id)
    if existing is None or existing.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found",
        )

    manifest = await manifest_service.update_manifest(manifest_id, data)
    return ManifestResponse.model_validate(manifest)


@router.post("/{manifest_id}/activate", response_model=ManifestResponse)
async def activate_manifest(
    org_id: UUID,
    manifest_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> ManifestResponse:
    """Activate a manifest, allowing the agent to request capability tokens."""
    manifest_service = ManifestService(db)

    # Check manifest exists and belongs to org
    existing = await manifest_service.get_manifest_by_id(manifest_id)
    if existing is None or existing.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found",
        )

    manifest = await manifest_service.activate_manifest(manifest_id)
    return ManifestResponse.model_validate(manifest)


@router.post("/{manifest_id}/suspend", response_model=ManifestResponse)
async def suspend_manifest(
    org_id: UUID,
    manifest_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> ManifestResponse:
    """Suspend a manifest, temporarily preventing capability token requests."""
    manifest_service = ManifestService(db)

    # Check manifest exists and belongs to org
    existing = await manifest_service.get_manifest_by_id(manifest_id)
    if existing is None or existing.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found",
        )

    manifest = await manifest_service.suspend_manifest(manifest_id)
    return ManifestResponse.model_validate(manifest)


@router.post("/{manifest_id}/revoke", response_model=ManifestResponse)
async def revoke_manifest(
    org_id: UUID,
    manifest_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> ManifestResponse:
    """Revoke a manifest. This is permanent and cannot be undone."""
    manifest_service = ManifestService(db)

    # Check manifest exists and belongs to org
    existing = await manifest_service.get_manifest_by_id(manifest_id)
    if existing is None or existing.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found",
        )

    manifest = await manifest_service.revoke_manifest(manifest_id)
    return ManifestResponse.model_validate(manifest)


@router.delete("/{manifest_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manifest(
    org_id: UUID,
    manifest_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> None:
    """Delete a manifest. Only pending manifests can be deleted."""
    manifest_service = ManifestService(db)

    # Check manifest exists and belongs to org
    existing = await manifest_service.get_manifest_by_id(manifest_id)
    if existing is None or existing.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Manifest not found",
        )

    # Only allow deleting pending manifests
    if existing.status != ManifestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending manifests can be deleted",
        )

    await manifest_service.delete_manifest(manifest_id)
