"""API Key service."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import generate_api_key, get_api_key_prefix, hash_api_key, verify_api_key
from app.models.api_key import ApiKey, ApiKeyStatus
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreateResponse, ApiKeyList, ApiKeyResponse


class ApiKeyService:
    """Service for API key operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_api_key(
        self,
        data: ApiKeyCreate,
        created_by_user_id: UUID | None = None,
    ) -> ApiKeyCreateResponse:
        """Create a new API key.

        Returns the full key only at creation time.
        """
        # Generate a new key
        full_key = generate_api_key()
        key_prefix = get_api_key_prefix(full_key)
        key_hash = hash_api_key(full_key)

        api_key = ApiKey(
            org_id=data.org_id,
            name=data.name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            status=ApiKeyStatus.ACTIVE,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(api_key)
        await self.db.flush()
        await self.db.refresh(api_key)

        return ApiKeyCreateResponse(
            id=api_key.id,
            org_id=api_key.org_id,
            name=api_key.name,
            key_prefix=api_key.key_prefix,
            key=full_key,  # Only time the full key is returned
            status=api_key.status,
            created_at=api_key.created_at,
        )

    async def get_api_key_by_id(self, api_key_id: UUID) -> ApiKey | None:
        """Get an API key by ID."""
        result = await self.db.execute(select(ApiKey).where(ApiKey.id == api_key_id))
        return result.scalar_one_or_none()

    async def authenticate_api_key(self, key: str) -> ApiKey | None:
        """Authenticate an API key and return the associated ApiKey if valid.

        Also updates the last_used_at timestamp.
        """
        # Get the prefix to narrow down candidates
        prefix = get_api_key_prefix(key)

        # Find all active keys with matching prefix
        result = await self.db.execute(
            select(ApiKey).where(
                ApiKey.key_prefix == prefix,
                ApiKey.status == ApiKeyStatus.ACTIVE,
            )
        )
        candidates = result.scalars().all()

        # Verify against each candidate (should typically be just one)
        for api_key in candidates:
            if verify_api_key(key, api_key.key_hash):
                # Update last used timestamp
                api_key.last_used_at = datetime.now(UTC)
                await self.db.flush()
                return api_key

        return None

    async def list_org_api_keys(
        self,
        org_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> ApiKeyList:
        """List API keys for an organization."""
        # Get total count
        count_result = await self.db.execute(
            select(func.count(ApiKey.id)).where(ApiKey.org_id == org_id)
        )
        total = count_result.scalar_one()

        # Get paginated results
        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.org_id == org_id)
            .order_by(ApiKey.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        keys = result.scalars().all()

        return ApiKeyList(
            items=[ApiKeyResponse.model_validate(key) for key in keys],
            total=total,
        )

    async def list_user_api_keys(
        self,
        user_id: UUID,
        org_ids: list[UUID],
        limit: int = 100,
        offset: int = 0,
    ) -> ApiKeyList:
        """List API keys for organizations a user has access to."""
        if not org_ids:
            return ApiKeyList(items=[], total=0)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(ApiKey.id)).where(ApiKey.org_id.in_(org_ids))
        )
        total = count_result.scalar_one()

        # Get paginated results
        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.org_id.in_(org_ids))
            .order_by(ApiKey.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        keys = result.scalars().all()

        return ApiKeyList(
            items=[ApiKeyResponse.model_validate(key) for key in keys],
            total=total,
        )

    async def revoke_api_key(self, api_key_id: UUID) -> ApiKey | None:
        """Revoke an API key."""
        api_key = await self.get_api_key_by_id(api_key_id)
        if api_key is None:
            return None

        api_key.status = ApiKeyStatus.REVOKED
        await self.db.flush()
        await self.db.refresh(api_key)
        return api_key
