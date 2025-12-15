"""Organization API endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.organization import OrganizationCreate, OrganizationList, OrganizationResponse
from app.services.organization import OrganizationService

router = APIRouter(prefix="/orgs", tags=["Organizations"])


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    user: CurrentUser,
    db: DbSession,
) -> OrganizationResponse:
    """Create a new organization.

    The authenticated user becomes the OWNER of the new organization.
    """
    org_service = OrganizationService(db)

    # Check if slug already exists
    if await org_service.slug_exists(data.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with slug '{data.slug}' already exists",
        )

    org = await org_service.create_organization(data, owner_user_id=user.id)
    return OrganizationResponse.model_validate(org)


@router.get("", response_model=OrganizationList)
async def list_organizations(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> OrganizationList:
    """List organizations the current user is a member of."""
    org_service = OrganizationService(db)
    return await org_service.list_user_organizations(user.id, limit=limit, offset=offset)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> OrganizationResponse:
    """Get organization details.

    User must be a member of the organization.
    """
    org_service = OrganizationService(db)
    org = await org_service.get_organization_by_id(org_id)

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Check user is a member (list_user_organizations already filters)
    user_orgs = await org_service.list_user_organizations(user.id)
    if not any(o.id == org_id for o in user_orgs.items):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )

    return OrganizationResponse.model_validate(org)
