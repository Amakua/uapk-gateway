"""API Key endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, require_org_role
from app.models.membership import Membership, MembershipRole
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyList, ApiKeyResponse
from app.services.api_key import ApiKeyService
from app.services.organization import OrganizationService

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


async def get_user_org_ids(db: AsyncSession, user_id: UUID) -> list[UUID]:
    """Get list of org IDs the user has access to."""
    from sqlalchemy import select

    from app.models.user import User

    result = await db.execute(
        select(User).options(selectinload(User.memberships)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        return []
    return [m.org_id for m in user.memberships]


@router.post("", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    user: CurrentUser,
    db: DbSession,
) -> ApiKeyCreateResponse:
    """Create a new API key for an organization.

    Requires OWNER or ADMIN role in the organization.
    The full key is returned ONLY ONCE at creation time.
    """
    # Verify user has admin access to the org
    from app.services.membership import MembershipService

    membership_service = MembershipService(db)
    has_access = await membership_service.user_has_role(
        data.org_id, user.id, [MembershipRole.OWNER, MembershipRole.ADMIN]
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires OWNER or ADMIN role in the organization",
        )

    # Verify org exists
    org_service = OrganizationService(db)
    org = await org_service.get_organization_by_id(data.org_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    api_key_service = ApiKeyService(db)
    return await api_key_service.create_api_key(data, created_by_user_id=user.id)


@router.get("", response_model=ApiKeyList)
async def list_api_keys(
    user: CurrentUser,
    db: DbSession,
    org_id: UUID | None = Query(default=None, description="Filter by organization"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> ApiKeyList:
    """List API keys.

    If org_id is provided, lists keys for that org (requires membership).
    Otherwise, lists keys for all orgs the user has access to.
    """
    api_key_service = ApiKeyService(db)

    if org_id is not None:
        # Verify user has access to the org
        from app.services.membership import MembershipService

        membership_service = MembershipService(db)
        has_access = await membership_service.user_has_role(
            org_id,
            user.id,
            [
                MembershipRole.OWNER,
                MembershipRole.ADMIN,
                MembershipRole.OPERATOR,
                MembershipRole.VIEWER,
            ],
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )
        return await api_key_service.list_org_api_keys(org_id, limit=limit, offset=offset)
    else:
        # List keys for all orgs user has access to
        org_ids = await get_user_org_ids(db, user.id)
        return await api_key_service.list_user_api_keys(user.id, org_ids, limit=limit, offset=offset)


@router.post("/{api_key_id}/revoke", response_model=ApiKeyResponse)
async def revoke_api_key(
    api_key_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> ApiKeyResponse:
    """Revoke an API key.

    Requires OWNER or ADMIN role in the organization the key belongs to.
    """
    api_key_service = ApiKeyService(db)

    # Get the key first to check org membership
    api_key = await api_key_service.get_api_key_by_id(api_key_id)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Verify user has admin access to the org
    from app.services.membership import MembershipService

    membership_service = MembershipService(db)
    has_access = await membership_service.user_has_role(
        api_key.org_id, user.id, [MembershipRole.OWNER, MembershipRole.ADMIN]
    )
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires OWNER or ADMIN role in the organization",
        )

    revoked_key = await api_key_service.revoke_api_key(api_key_id)
    if revoked_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    return ApiKeyResponse.model_validate(revoked_key)
