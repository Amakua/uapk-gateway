"""Organization service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.membership import Membership, MembershipRole
from app.models.organization import Organization
from app.schemas.organization import OrganizationCreate, OrganizationList, OrganizationResponse


class OrganizationService:
    """Service for organization operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_organization(
        self,
        data: OrganizationCreate,
        owner_user_id: UUID | None = None,
    ) -> Organization:
        """Create a new organization.

        If owner_user_id is provided, creates an OWNER membership for that user.
        """
        org = Organization(
            name=data.name,
            slug=data.slug,
        )
        self.db.add(org)
        await self.db.flush()

        # Create owner membership if user ID provided
        if owner_user_id:
            membership = Membership(
                org_id=org.id,
                user_id=owner_user_id,
                role=MembershipRole.OWNER,
            )
            self.db.add(membership)
            await self.db.flush()

        await self.db.refresh(org)
        return org

    async def get_organization_by_id(self, org_id: UUID) -> Organization | None:
        """Get an organization by ID."""
        result = await self.db.execute(select(Organization).where(Organization.id == org_id))
        return result.scalar_one_or_none()

    async def get_organization_by_slug(self, slug: str) -> Organization | None:
        """Get an organization by slug."""
        result = await self.db.execute(select(Organization).where(Organization.slug == slug))
        return result.scalar_one_or_none()

    async def list_organizations(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> OrganizationList:
        """List all organizations."""
        # Get total count
        count_result = await self.db.execute(select(func.count(Organization.id)))
        total = count_result.scalar_one()

        # Get paginated results
        result = await self.db.execute(
            select(Organization)
            .order_by(Organization.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        orgs = result.scalars().all()

        return OrganizationList(
            items=[OrganizationResponse.model_validate(org) for org in orgs],
            total=total,
        )

    async def list_user_organizations(
        self,
        user_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> OrganizationList:
        """List organizations a user is a member of."""
        # Get total count
        count_result = await self.db.execute(
            select(func.count(Organization.id))
            .join(Membership)
            .where(Membership.user_id == user_id)
        )
        total = count_result.scalar_one()

        # Get paginated results
        result = await self.db.execute(
            select(Organization)
            .join(Membership)
            .where(Membership.user_id == user_id)
            .order_by(Organization.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        orgs = result.scalars().all()

        return OrganizationList(
            items=[OrganizationResponse.model_validate(org) for org in orgs],
            total=total,
        )

    async def slug_exists(self, slug: str) -> bool:
        """Check if an organization slug already exists."""
        result = await self.db.execute(
            select(func.count(Organization.id)).where(Organization.slug == slug)
        )
        return result.scalar_one() > 0
