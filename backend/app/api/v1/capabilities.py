"""API endpoints for capability issuers and token issuance."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
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

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


@router.get("/gateway-key", response_model=GatewayPublicKeyResponse)
async def get_gateway_public_key() -> GatewayPublicKeyResponse:
    """Get the gateway's public key for token verification.

    This endpoint is public and can be used by external systems
    to verify tokens signed by the gateway.
    """
    key_manager = get_gateway_key_manager()
    return GatewayPublicKeyResponse(
        issuer_id="gateway",
        public_key=key_manager.get_public_key_base64(),
        algorithm="EdDSA",
    )


@router.post("/issuers", response_model=IssuerResponse, status_code=status.HTTP_201_CREATED)
async def register_issuer(
    issuer_data: IssuerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IssuerResponse:
    """Register a new capability issuer with public key.

    This allows external systems to issue capability tokens that
    the gateway will accept. The public key is used to verify
    token signatures.

    Requires admin role.
    """
    # TODO: Add admin role check when role system is implemented
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        return await issuer_service.register_issuer(
            db=db,
            org_id=current_user.default_org_id,
            issuer_data=issuer_data,
            user_id=current_user.id,
        )
    except CapabilityIssuerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/issuers", response_model=IssuerList)
async def list_issuers(
    include_revoked: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IssuerList:
    """List capability issuers for the organization.

    Args:
        include_revoked: Include revoked issuers in the list
    """
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    issuers = await issuer_service.list_issuers(
        db=db,
        org_id=current_user.default_org_id,
        include_revoked=include_revoked,
    )

    return IssuerList(items=issuers, total=len(issuers))


@router.get("/issuers/{issuer_id}", response_model=IssuerResponse)
async def get_issuer(
    issuer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IssuerResponse:
    """Get a capability issuer by ID."""
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    issuer = await issuer_service.get_issuer(
        db=db,
        org_id=current_user.default_org_id,
        issuer_id=issuer_id,
    )

    if not issuer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issuer '{issuer_id}' not found",
        )

    return issuer


@router.post("/issuers/{issuer_id}/revoke", response_model=IssuerResponse)
async def revoke_issuer(
    issuer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IssuerResponse:
    """Revoke a capability issuer.

    Tokens issued by this issuer will no longer be accepted.
    This action cannot be undone.

    Requires admin role.
    """
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        return await issuer_service.revoke_issuer(
            db=db,
            org_id=current_user.default_org_id,
            issuer_id=issuer_id,
        )
    except CapabilityIssuerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/issue", response_model=IssueTokenResponse, status_code=status.HTTP_201_CREATED)
async def issue_token(
    request: IssueTokenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    try:
        return await issuer_service.issue_capability_token(
            db=db,
            org_id=current_user.default_org_id,
            request=request,
            issuer_id="gateway",  # Gateway is the default issuer
        )
    except CapabilityIssuerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/issuers/{issuer_id}/public-key")
async def get_issuer_public_key(
    issuer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get the public key for a specific issuer.

    This can be used by external systems to verify tokens
    issued by this issuer.
    """
    if not current_user.default_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to an organization",
        )

    issuer = await issuer_service.get_issuer(
        db=db,
        org_id=current_user.default_org_id,
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
