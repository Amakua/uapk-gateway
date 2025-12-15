"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.membership import Membership, MembershipRole
from app.models.organization import Organization
from app.models.user import User

# Use a separate test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://uapk:uapk@localhost:5432/uapk_test"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with transaction rollback."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        # Rollback any changes made during the test
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client with database session override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def test_org(db_session: AsyncSession) -> Organization:
    """Create a test organization."""
    org = Organization(
        id=uuid4(),
        name="Test Organization",
        slug="test-org",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def test_user_with_org(
    db_session: AsyncSession,
    test_user: User,
    test_org: Organization,
) -> tuple[User, Organization, Membership]:
    """Create a test user with organization membership."""
    membership = Membership(
        id=uuid4(),
        org_id=test_org.id,
        user_id=test_user.id,
        role=MembershipRole.OWNER,
    )
    db_session.add(membership)
    await db_session.flush()
    return test_user, test_org, membership


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict[str, str]:
    """Create authentication headers for a test user."""
    from app.core.security import create_access_token

    token = create_access_token(subject=str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def auth_headers_with_org(test_user_with_org: tuple[User, Organization, Membership]) -> dict[str, str]:
    """Create authentication headers for a user with organization membership."""
    from app.core.security import create_access_token

    user, _, _ = test_user_with_org
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}
