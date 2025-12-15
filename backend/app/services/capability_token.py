"""Capability token service - token issuance and management."""

import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_capability_token_jwt
from app.models.capability_token import CapabilityToken
from app.schemas.capability_token import (
    CapabilityTokenCreate,
    CapabilityTokenCreateResponse,
    CapabilityTokenList,
    CapabilityTokenResponse,
)


def generate_token_id() -> str:
    """Generate a unique token ID in cap-xxx format."""
    random_part = secrets.token_hex(12)
    return f"cap-{random_part}"


class CapabilityTokenService:
    """Service for managing capability tokens."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_token(
        self,
        data: CapabilityTokenCreate,
        issued_by: str,
    ) -> tuple[CapabilityToken, str]:
        """Create a new capability token.

        Returns the token model and the JWT string.
        """
        token_id = generate_token_id()
        expires_at = datetime.now(UTC) + timedelta(seconds=data.expires_in_seconds)

        token = CapabilityToken(
            token_id=token_id,
            org_id=data.org_id,
            agent_id=data.agent_id,
            manifest_id=data.manifest_id,
            capabilities=data.capabilities,
            expires_at=expires_at,
            issued_by=issued_by,
            constraints=data.constraints.model_dump(mode="json") if data.constraints else None,
            max_actions=data.constraints.max_actions if data.constraints else None,
        )

        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)

        # Generate JWT
        jwt = create_capability_token_jwt(
            token_id=token_id,
            agent_id=data.agent_id,
            org_id=str(data.org_id),
            capabilities=data.capabilities,
            expires_at=expires_at,
        )

        return token, jwt

    async def get_token_by_id(self, token_id: str) -> CapabilityToken | None:
        """Get a token by its token_id."""
        result = await self.db.execute(
            select(CapabilityToken).where(CapabilityToken.token_id == token_id)
        )
        return result.scalar_one_or_none()

    async def get_token_by_uuid(self, uuid: UUID) -> CapabilityToken | None:
        """Get a token by its database UUID."""
        result = await self.db.execute(
            select(CapabilityToken).where(CapabilityToken.id == uuid)
        )
        return result.scalar_one_or_none()

    async def validate_token(self, token_id: str) -> tuple[CapabilityToken | None, str | None]:
        """Validate a capability token.

        Returns (token, error_message). If valid, error_message is None.
        """
        token = await self.get_token_by_id(token_id)

        if token is None:
            return None, "Token not found"

        if token.revoked:
            return None, "Token has been revoked"

        if token.expires_at < datetime.now(UTC):
            return None, "Token has expired"

        if token.max_actions and token.actions_used >= token.max_actions:
            return None, "Token action limit exceeded"

        return token, None

    async def increment_action_count(self, token: CapabilityToken) -> None:
        """Increment the action count for a token."""
        token.actions_used += 1
        await self.db.commit()

    async def list_tokens(
        self,
        org_id: UUID,
        agent_id: str | None = None,
        include_revoked: bool = False,
        include_expired: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> CapabilityTokenList:
        """List capability tokens for an organization."""
        query = select(CapabilityToken).where(CapabilityToken.org_id == org_id)

        if agent_id:
            query = query.where(CapabilityToken.agent_id == agent_id)

        if not include_revoked:
            query = query.where(CapabilityToken.revoked.is_(False))

        if not include_expired:
            query = query.where(CapabilityToken.expires_at > datetime.now(UTC))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get items with pagination
        query = query.order_by(CapabilityToken.issued_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        tokens = result.scalars().all()

        return CapabilityTokenList(
            items=[CapabilityTokenResponse.model_validate(t) for t in tokens],
            total=total,
        )

    async def revoke_token(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> CapabilityToken | None:
        """Revoke a capability token."""
        token = await self.get_token_by_id(token_id)
        if token is None:
            return None

        token.revoked = True
        token.revoked_at = datetime.now(UTC)
        token.revoked_reason = reason

        await self.db.commit()
        await self.db.refresh(token)
        return token

    async def revoke_all_for_agent(
        self,
        org_id: UUID,
        agent_id: str,
        reason: str | None = None,
    ) -> int:
        """Revoke all tokens for an agent. Returns count of revoked tokens."""
        result = await self.db.execute(
            select(CapabilityToken).where(
                CapabilityToken.org_id == org_id,
                CapabilityToken.agent_id == agent_id,
                CapabilityToken.revoked.is_(False),
            )
        )
        tokens = result.scalars().all()

        now = datetime.now(UTC)
        for token in tokens:
            token.revoked = True
            token.revoked_at = now
            token.revoked_reason = reason

        await self.db.commit()
        return len(tokens)
