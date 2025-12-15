"""User service."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserList, UserResponse, UserUpdate


class UserService:
    """Service for user operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_user(self, data: UserCreate) -> User:
        """Create a new user."""
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        """Get a user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        """Get a user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> UserList:
        """List all users."""
        # Get total count
        count_result = await self.db.execute(select(func.count(User.id)))
        total = count_result.scalar_one()

        # Get paginated results
        result = await self.db.execute(
            select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
        )
        users = result.scalars().all()

        return UserList(
            items=[UserResponse.model_validate(user) for user in users],
            total=total,
        )

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User | None:
        """Update a user."""
        user = await self.get_user_by_id(user_id)
        if user is None:
            return None

        if data.email is not None:
            user.email = data.email
        if data.password is not None:
            user.password_hash = hash_password(data.password)
        if data.is_active is not None:
            user.is_active = data.is_active

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def email_exists(self, email: str) -> bool:
        """Check if an email already exists."""
        result = await self.db.execute(select(func.count(User.id)).where(User.email == email))
        return result.scalar_one() > 0
