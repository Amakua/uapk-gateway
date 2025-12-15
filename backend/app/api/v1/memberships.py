"""Membership API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession, require_org_role
from app.models.membership import MembershipRole
from app.schemas.membership import MembershipCreate, MembershipList, MembershipResponse
from app.services.membership import MembershipService
from app.services.organization import OrganizationService
from app.services.user import UserService

router = APIRouter(tags=["Memberships"])


@router.post(
    "/orgs/{org_id}/memberships",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_membership(
    org_id: UUID,
    data: MembershipCreate,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, Depends(require_org_role([MembershipRole.OWNER, MembershipRole.ADMIN]))],
) -> MembershipResponse:
    """Add a user to an organization with a specified role.

    Requires OWNER or ADMIN role in the organization.
    """
    org_service = OrganizationService(db)
    user_service = UserService(db)
    membership_service = MembershipService(db)

    # Verify org exists
    org = await org_service.get_organization_by_id(org_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Verify target user exists
    target_user = await user_service.get_user_by_id(data.user_id)
    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check if membership already exists
    if await membership_service.membership_exists(org_id, data.user_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization",
        )

    # Only OWNER can create OWNER memberships
    if data.role == MembershipRole.OWNER:
        current_membership = await membership_service.get_membership(org_id, user.id)
        if current_membership is None or current_membership.role != MembershipRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only owners can add other owners",
            )

    membership = await membership_service.create_membership(org_id, data)

    return MembershipResponse(
        id=membership.id,
        org_id=membership.org_id,
        user_id=membership.user_id,
        role=membership.role,
        created_at=membership.created_at,
        user_email=target_user.email,
    )


@router.get("/orgs/{org_id}/memberships", response_model=MembershipList)
async def list_memberships(
    org_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[
        None,
        Depends(
            require_org_role(
                [
                    MembershipRole.OWNER,
                    MembershipRole.ADMIN,
                    MembershipRole.OPERATOR,
                    MembershipRole.VIEWER,
                ]
            )
        ),
    ],
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> MembershipList:
    """List memberships for an organization.

    Requires membership in the organization.
    """
    membership_service = MembershipService(db)
    return await membership_service.list_org_memberships(org_id, limit=limit, offset=offset)


@router.delete(
    "/orgs/{org_id}/memberships/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_membership(
    org_id: UUID,
    membership_id: UUID,
    user: CurrentUser,
    db: DbSession,
    _: Annotated[None, Depends(require_org_role([MembershipRole.OWNER, MembershipRole.ADMIN]))],
) -> None:
    """Remove a membership from an organization.

    Requires OWNER or ADMIN role in the organization.
    Cannot remove the last OWNER.
    """
    membership_service = MembershipService(db)

    membership = await membership_service.get_membership_by_id(membership_id)
    if membership is None or membership.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found",
        )

    # Prevent removing yourself if you're the only owner
    if membership.role == MembershipRole.OWNER:
        org_memberships = await membership_service.list_org_memberships(org_id)
        owner_count = sum(1 for m in org_memberships.items if m.role == MembershipRole.OWNER)
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner of an organization",
            )

    await membership_service.delete_membership(membership_id)
