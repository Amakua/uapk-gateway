"""Membership service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.membership import Membership, MembershipRole
from app.schemas.membership import (
    MembershipCreate,
    MembershipList,
    MembershipResponse,
    MembershipUpdate,
)


class MembershipService:
    """Service for membership operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_membership(
        self,
        org_id: UUID,
        data: MembershipCreate,
    ) -> Membership:
        """Create a new membership."""
        membership = Membership(
            org_id=org_id,
            user_id=data.user_id,
            role=data.role,
        )
        self.db.add(membership)
        await self.db.flush()
        await self.db.refresh(membership)
        return membership

    async def get_membership(
        self,
        org_id: UUID,
        user_id: UUID,
    ) -> Membership | None:
        """Get a membership by org and user ID."""
        result = await self.db.execute(
            select(Membership)
            .options(selectinload(Membership.user))
            .where(Membership.org_id == org_id, Membership.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_membership_by_id(self, membership_id: UUID) -> Membership | None:
        """Get a membership by ID."""
        result = await self.db.execute(
            select(Membership)
            .options(selectinload(Membership.user))
            .where(Membership.id == membership_id)
        )
        return result.scalar_one_or_none()

    async def list_org_memberships(
        self,
        org_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> MembershipList:
        """List memberships for an organization."""
        # Get total count
        count_result = await self.db.execute(
            select(func.count(Membership.id)).where(Membership.org_id == org_id)
        )
        total = count_result.scalar_one()

        # Get paginated results with user info
        result = await self.db.execute(
            select(Membership)
            .options(selectinload(Membership.user))
            .where(Membership.org_id == org_id)
            .order_by(Membership.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        memberships = result.scalars().all()

        items = [
            MembershipResponse(
                id=m.id,
                org_id=m.org_id,
                user_id=m.user_id,
                role=m.role,
                created_at=m.created_at,
                user_email=m.user.email if m.user else None,
            )
            for m in memberships
        ]

        return MembershipList(items=items, total=total)

    async def update_membership(
        self,
        membership_id: UUID,
        data: MembershipUpdate,
    ) -> Membership | None:
        """Update a membership."""
        membership = await self.get_membership_by_id(membership_id)
        if membership is None:
            return None

        membership.role = data.role
        await self.db.flush()
        await self.db.refresh(membership)
        return membership

    async def delete_membership(self, membership_id: UUID) -> bool:
        """Delete a membership."""
        membership = await self.get_membership_by_id(membership_id)
        if membership is None:
            return False

        await self.db.delete(membership)
        await self.db.flush()
        return True

    async def user_has_role(
        self,
        org_id: UUID,
        user_id: UUID,
        roles: list[MembershipRole],
    ) -> bool:
        """Check if a user has one of the specified roles in an organization."""
        result = await self.db.execute(
            select(func.count(Membership.id)).where(
                Membership.org_id == org_id,
                Membership.user_id == user_id,
                Membership.role.in_(roles),
            )
        )
        return result.scalar_one() > 0

    async def membership_exists(self, org_id: UUID, user_id: UUID) -> bool:
        """Check if a membership already exists."""
        result = await self.db.execute(
            select(func.count(Membership.id)).where(
                Membership.org_id == org_id,
                Membership.user_id == user_id,
            )
        )
        return result.scalar_one() > 0
