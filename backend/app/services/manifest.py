"""Manifest service - CRUD operations for UAPK manifests."""

import hashlib
import json
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.uapk_manifest import ManifestStatus, UapkManifest
from app.schemas.manifest import ManifestCreate, ManifestList, ManifestResponse, ManifestUpdate


class ManifestService:
    """Service for managing UAPK manifests."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _compute_manifest_hash(self, manifest_json: dict) -> str:
        """Compute SHA-256 hash of manifest for integrity verification."""
        canonical = json.dumps(manifest_json, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    async def create_manifest(
        self,
        data: ManifestCreate,
        user_id: UUID | None = None,
    ) -> UapkManifest:
        """Create a new manifest."""
        manifest_json = data.manifest.model_dump(mode="json")
        manifest_hash = self._compute_manifest_hash(manifest_json)

        manifest = UapkManifest(
            org_id=data.org_id,
            uapk_id=data.manifest.agent.id,
            version=data.manifest.agent.version,
            manifest_json=manifest_json,
            manifest_hash=manifest_hash,
            status=ManifestStatus.PENDING,
            description=data.description,
            created_by_user_id=user_id,
        )

        self.db.add(manifest)
        await self.db.commit()
        await self.db.refresh(manifest)
        return manifest

    async def get_manifest_by_id(self, manifest_id: UUID) -> UapkManifest | None:
        """Get a manifest by its ID."""
        result = await self.db.execute(
            select(UapkManifest).where(UapkManifest.id == manifest_id)
        )
        return result.scalar_one_or_none()

    async def get_manifest_by_uapk_id(
        self,
        org_id: UUID,
        uapk_id: str,
        version: str | None = None,
    ) -> UapkManifest | None:
        """Get a manifest by agent ID and optionally version."""
        query = select(UapkManifest).where(
            UapkManifest.org_id == org_id,
            UapkManifest.uapk_id == uapk_id,
        )
        if version:
            query = query.where(UapkManifest.version == version)
        else:
            # Get the most recent version
            query = query.order_by(UapkManifest.created_at.desc())

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_manifests(
        self,
        org_id: UUID,
        status: ManifestStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ManifestList:
        """List manifests for an organization."""
        query = select(UapkManifest).where(UapkManifest.org_id == org_id)

        if status:
            query = query.where(UapkManifest.status == status)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get items with pagination
        query = query.order_by(UapkManifest.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        manifests = result.scalars().all()

        return ManifestList(
            items=[ManifestResponse.model_validate(m) for m in manifests],
            total=total,
        )

    async def update_manifest(
        self,
        manifest_id: UUID,
        data: ManifestUpdate,
    ) -> UapkManifest | None:
        """Update a manifest's status or description."""
        manifest = await self.get_manifest_by_id(manifest_id)
        if manifest is None:
            return None

        if data.status is not None:
            manifest.status = data.status
        if data.description is not None:
            manifest.description = data.description

        await self.db.commit()
        await self.db.refresh(manifest)
        return manifest

    async def activate_manifest(self, manifest_id: UUID) -> UapkManifest | None:
        """Activate a manifest."""
        return await self.update_manifest(
            manifest_id,
            ManifestUpdate(status=ManifestStatus.ACTIVE),
        )

    async def suspend_manifest(self, manifest_id: UUID) -> UapkManifest | None:
        """Suspend a manifest."""
        return await self.update_manifest(
            manifest_id,
            ManifestUpdate(status=ManifestStatus.SUSPENDED),
        )

    async def revoke_manifest(self, manifest_id: UUID) -> UapkManifest | None:
        """Revoke a manifest."""
        return await self.update_manifest(
            manifest_id,
            ManifestUpdate(status=ManifestStatus.REVOKED),
        )

    async def delete_manifest(self, manifest_id: UUID) -> bool:
        """Delete a manifest. Returns True if deleted."""
        manifest = await self.get_manifest_by_id(manifest_id)
        if manifest is None:
            return False

        await self.db.delete(manifest)
        await self.db.commit()
        return True
