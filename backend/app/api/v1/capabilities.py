"""API endpoints for capability issuers and token issuance."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DbSession, RequireOrgAdmin, get_current_user, get_db
from app.core.ed25519 import get_gateway_key_manager
from app.models.user import User
from app.schemas.capability_issuer import (
    GatewayPublicKeyResponse,
    IssueTokenRequest,
    IssueTokenResponse,
    IssuerCreate,
    IssuerList,
    IssuerResponse,
)
from app.services import capability_issuer as issuer_service
from app.services.capability_issuer import CapabilityIssuerError

router = APIRouter(tags=["capabilities"])


@router.get("/capabilities/gateway-key", response_model=GatewayPublicKeyResponse)
async def get_gateway_public_key() -> GatewayPublicKeyResponse:
    """Get the gateway's public key for token verification.

    This endpoint is public and can be used by external systems
    to verify tokens signed by the gateway.
    """
    key_manager = get_gateway_key_manager()
    return GatewayPublicKeyResponse(
        issuer_id="gateway",
        public_key=key_manager.public_key_base64,  # FIXED: property, not method
        algorithm="EdDSA",
    )


# Org-scoped routes
org_router = APIRouter(prefix="/orgs/{org_id}/capabilities", tags=["capabilities"])


@org_router.post("/issuers", response_model=IssuerResponse, status_code=status.HTTP_201_CREATED)
async def register_issuer(
    org_id: UUID,
    issuer_data: IssuerCreate,
    _: Annotated[None, Depends(RequireOrgAdmin)],  # RBAC check - admin only
    db: DbSession,
    current_user: CurrentUser,
) -> IssuerResponse:
    """Register a new capability issuer with public key.

    This allows external systems to issue capability tokens that
    the gateway will accept. The public key is used to verify
    token signatures.

    Requires admin role.
    """
    try:
        return await issuer_service.register_issuer(
            db=db,
            org_id=org_id,
            issuer_data=issuer_data,
            user_id=current_user.id,
        )
    except CapabilityIssuerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@org_router.get("/issuers", response_model=IssuerList)
async def list_issuers(
    org_id: UUID,
    _: Annotated[None, Depends(RequireOrgAdmin)],  # RBAC check
    include_revoked: bool = False,
    db: DbSession,
    current_user: CurrentUser,
) -> IssuerList:
    """List capability issuers for the organization.

    Args:
        org_id: Organization ID (from path)
        include_revoked: Include revoked issuers in the list
    """
    issuers = await issuer_service.list_issuers(
        db=db,
        org_id=org_id,
        include_revoked=include_revoked,
    )

    return IssuerList(items=issuers, total=len(issuers))


@org_router.get("/issuers/{issuer_id}", response_model=IssuerResponse)
async def get_issuer(
    org_id: UUID,
    issuer_id: str,
    _: Annotated[None, Depends(RequireOrgAdmin)],  # RBAC check
    db: DbSession,
    current_user: CurrentUser,
) -> IssuerResponse:
    """Get a capability issuer by ID."""
    issuer = await issuer_service.get_issuer(
        db=db,
        org_id=org_id,
        issuer_id=issuer_id,
    )

    if not issuer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issuer '{issuer_id}' not found",
        )

    return issuer


@org_router.post("/issuers/{issuer_id}/revoke", response_model=IssuerResponse)
async def revoke_issuer(
    org_id: UUID,
    issuer_id: str,
    _: Annotated[None, Depends(RequireOrgAdmin)],  # RBAC check - admin only
    db: DbSession,
    current_user: CurrentUser,
) -> IssuerResponse:
    """Revoke a capability issuer.

    Tokens issued by this issuer will no longer be accepted.
    This action cannot be undone.

    Requires admin role.
    """
    try:
        return await issuer_service.revoke_issuer(
            db=db,
            org_id=org_id,
            issuer_id=issuer_id,
        )
    except CapabilityIssuerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@org_router.post("/issue", response_model=IssueTokenResponse, status_code=status.HTTP_201_CREATED)
async def issue_token(
    org_id: UUID,
    request: IssueTokenRequest,
    _: Annotated[None, Depends(RequireOrgAdmin)],  # RBAC check - admin only
    db: DbSession,
    current_user: CurrentUser,
) -> IssueTokenResponse:
    """Issue a capability token for an agent.

    Creates a signed JWT capability token that grants the specified
    agent permissions to perform actions through the gateway.

    The token includes:
    - allowed_action_types: Action types the agent can perform
    - allowed_tools: Specific tools the agent can use
    - constraints: Amount caps, jurisdictions, counterparty rules
    - delegation_depth: How many times the token can be delegated

    Requires admin role.
    """
    try:
        return await issuer_service.issue_capability_token(
            db=db,
            org_id=org_id,
            request=request,
            issuer_id="gateway",  # Gateway is the default issuer
        )
    except CapabilityIssuerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@org_router.get("/issuers/{issuer_id}/public-key")
async def get_issuer_public_key(
    org_id: UUID,
    issuer_id: str,
    _: Annotated[None, Depends(RequireOrgAdmin)],  # RBAC check
    db: DbSession,
    current_user: CurrentUser,
) -> dict:
    """Get the public key for a specific issuer.

    This can be used by external systems to verify tokens
    issued by this issuer.
    """
    issuer = await issuer_service.get_issuer(
        db=db,
        org_id=org_id,
        issuer_id=issuer_id,
    )

    if not issuer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issuer '{issuer_id}' not found",
        )

    return {
        "issuer_id": issuer.issuer_id,
        "public_key": issuer.public_key,
        "algorithm": "EdDSA",
    }


# Include both routers
router.include_router(org_router)
