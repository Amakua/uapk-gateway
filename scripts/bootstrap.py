#!/usr/bin/env python3
"""Bootstrap script to create initial admin user and organization.

Usage:
    python scripts/bootstrap.py

Or via docker:
    docker compose exec backend python scripts/bootstrap.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.database import get_session_factory, init_db, close_db
from app.core.security import hash_password
from app.models.membership import Membership, MembershipRole
from app.models.organization import Organization
from app.models.user import User


async def bootstrap() -> None:
    """Create initial admin user and organization."""
    # Get configuration from environment
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "changeme123")
    org_name = os.environ.get("ORG_NAME", "Default Organization")
    org_slug = os.environ.get("ORG_SLUG", "default")

    print("=" * 60)
    print("UAPK Gateway Bootstrap")
    print("=" * 60)
    print()

    # Initialize database
    await init_db()
    session_factory = get_session_factory()

    async with session_factory() as session:
        try:
            # Check if admin user already exists
            from sqlalchemy import select

            result = await session.execute(select(User).where(User.email == admin_email))
            existing_user = result.scalar_one_or_none()

            if existing_user:
                print(f"User '{admin_email}' already exists. Skipping user creation.")
                user = existing_user
            else:
                # Create admin user
                user = User(
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    is_active=True,
                )
                session.add(user)
                await session.flush()
                print(f"Created admin user: {admin_email}")

            # Check if organization already exists
            result = await session.execute(
                select(Organization).where(Organization.slug == org_slug)
            )
            existing_org = result.scalar_one_or_none()

            if existing_org:
                print(f"Organization '{org_slug}' already exists. Skipping org creation.")
                org = existing_org
            else:
                # Create organization
                org = Organization(
                    name=org_name,
                    slug=org_slug,
                )
                session.add(org)
                await session.flush()
                print(f"Created organization: {org_name} ({org_slug})")

            # Check if membership already exists
            result = await session.execute(
                select(Membership).where(
                    Membership.org_id == org.id,
                    Membership.user_id == user.id,
                )
            )
            existing_membership = result.scalar_one_or_none()

            if existing_membership:
                print(f"User already has membership in organization. Skipping.")
            else:
                # Create owner membership
                membership = Membership(
                    org_id=org.id,
                    user_id=user.id,
                    role=MembershipRole.OWNER,
                )
                session.add(membership)
                await session.flush()
                print(f"Created OWNER membership for user in organization")

            await session.commit()

            print()
            print("=" * 60)
            print("Bootstrap Complete!")
            print("=" * 60)
            print()
            print("Admin credentials:")
            print(f"  Email:    {admin_email}")
            print(f"  Password: {admin_password}")
            print()
            print("Organization:")
            print(f"  Name: {org_name}")
            print(f"  Slug: {org_slug}")
            print()
            print("Next steps:")
            print("  1. Login at POST /api/v1/auth/login")
            print("  2. Create an API key at POST /api/v1/api-keys")
            print("  3. Use the API key to authenticate agent requests")
            print()
            print("IMPORTANT: Change the admin password in production!")
            print()

        except Exception as e:
            await session.rollback()
            print(f"Error during bootstrap: {e}")
            raise
        finally:
            await close_db()


def main() -> None:
    """Entry point."""
    asyncio.run(bootstrap())


if __name__ == "__main__":
    main()
