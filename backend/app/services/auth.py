"""Authentication service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.membership import Membership
from app.models.user import User
from app.schemas.auth import OrgMembershipInfo, TokenResponse, UserWithOrgsResponse


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def authenticate_user(self, email: str, password: str) -> User | None:
        """Authenticate a user by email and password.

        Returns the user if credentials are valid, None otherwise.
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user is None:
            return None

        if not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            return None

        # Update last login time
        user.last_login_at = datetime.now(UTC)
        await self.db.flush()

        return user

    async def create_token_for_user(self, user: User) -> TokenResponse:
        """Create a JWT token for an authenticated user."""
        settings = get_settings()

        token = create_access_token(
            subject=str(user.id),
            extra_claims={"email": user.email},
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=settings.jwt_expiration_minutes * 60,
        )

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get a user by their ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_with_orgs(self, user_id: UUID) -> UserWithOrgsResponse | None:
        """Get a user with their organization memberships."""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.memberships).selectinload(Membership.organization))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            return None

        orgs = [
            OrgMembershipInfo(
                org_id=m.organization.id,
                org_name=m.organization.name,
                org_slug=m.organization.slug,
                role=m.role.value,
            )
            for m in user.memberships
        ]

        return UserWithOrgsResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            organizations=orgs,
        )

    async def create_user(
        self,
        email: str,
        password: str,
        is_active: bool = True,
    ) -> User:
        """Create a new user."""
        user = User(
            email=email,
            password_hash=hash_password(password),
            is_active=is_active,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user
