"""Capability token API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, RequireOrgAdmin, RequireOrgOperator
from app.models.uapk_manifest import ManifestStatus
from app.schemas.capability_token import (
    CapabilityTokenCreate,
    CapabilityTokenCreateResponse,
    CapabilityTokenList,
    CapabilityTokenResponse,
    CapabilityTokenRevoke,
)
from app.services.capability_token import CapabilityTokenService
from app.services.manifest import ManifestService

router = APIRouter(prefix="/orgs/{org_id}/tokens", tags=["Capability Tokens"])


@router.post("", response_model=CapabilityTokenCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_capability_token(
    org_id: UUID,
    data: CapabilityTokenCreate,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgOperator],
) -> CapabilityTokenCreateResponse:
    """Issue a new capability token for an agent.

    The token grants the agent permission to perform specific actions.
    Returns both the token metadata and the JWT to use for authentication.

    If a manifest_id is provided, the requested capabilities must be a subset
    of what the manifest declares, and the manifest must be ACTIVE.
    """
    if data.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="org_id in path must match org_id in body",
        )

    # If manifest_id is provided, validate it
    if data.manifest_id:
        manifest_service = ManifestService(db)
        manifest = await manifest_service.get_manifest_by_id(data.manifest_id)

        if manifest is None or manifest.org_id != org_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manifest not found",
            )

        if manifest.status != ManifestStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Manifest is not active (status: {manifest.status.value})",
            )

        # Validate capabilities are subset of manifest's requested capabilities
        manifest_caps = set(manifest.manifest_json.get("capabilities", {}).get("requested", []))
        requested_caps = set(data.capabilities)

        if not requested_caps.issubset(manifest_caps):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested capabilities exceed manifest's declared capabilities",
            )

    token_service = CapabilityTokenService(db)
    token, jwt = await token_service.create_token(
        data=data,
        issued_by=str(user.id),
    )

    return CapabilityTokenCreateResponse(
        token=CapabilityTokenResponse.model_validate(token),
        jwt=jwt,
    )


@router.get("", response_model=CapabilityTokenList)
async def list_capability_tokens(
    org_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgOperator],
    agent_id: str | None = Query(default=None),
    include_revoked: bool = Query(default=False),
    include_expired: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> CapabilityTokenList:
    """List capability tokens for an organization."""
    token_service = CapabilityTokenService(db)
    return await token_service.list_tokens(
        org_id=org_id,
        agent_id=agent_id,
        include_revoked=include_revoked,
        include_expired=include_expired,
        limit=limit,
        offset=offset,
    )


@router.get("/{token_id}", response_model=CapabilityTokenResponse)
async def get_capability_token(
    org_id: UUID,
    token_id: str,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgOperator],
) -> CapabilityTokenResponse:
    """Get a specific capability token."""
    token_service = CapabilityTokenService(db)
    token = await token_service.get_token_by_id(token_id)

    if token is None or token.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )

    return CapabilityTokenResponse.model_validate(token)


@router.post("/{token_id}/revoke", response_model=CapabilityTokenResponse)
async def revoke_capability_token(
    org_id: UUID,
    token_id: str,
    data: CapabilityTokenRevoke,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> CapabilityTokenResponse:
    """Revoke a capability token.

    Revoked tokens can no longer be used for authentication.
    This action cannot be undone.
    """
    token_service = CapabilityTokenService(db)

    existing = await token_service.get_token_by_id(token_id)
    if existing is None or existing.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found",
        )

    if existing.revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token is already revoked",
        )

    token = await token_service.revoke_token(token_id, reason=data.reason)
    return CapabilityTokenResponse.model_validate(token)


@router.post("/revoke-all/{agent_id}", status_code=status.HTTP_200_OK)
async def revoke_all_tokens_for_agent(
    org_id: UUID,
    agent_id: str,
    data: CapabilityTokenRevoke,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, RequireOrgAdmin],
) -> dict:
    """Revoke all tokens for a specific agent.

    Use this to immediately revoke all access for an agent.
    """
    token_service = CapabilityTokenService(db)
    count = await token_service.revoke_all_for_agent(
        org_id=org_id,
        agent_id=agent_id,
        reason=data.reason,
    )

    return {"revoked_count": count}
