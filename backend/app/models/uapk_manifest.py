"""UAPK Manifest model."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ManifestStatus(str, enum.Enum):
    """Status of a UAPK manifest."""

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class UapkManifest(Base):
    """UAPK Manifest - declares an agent's identity and capabilities."""

    __tablename__ = "uapk_manifests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The agent's declared ID from the manifest
    uapk_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Version string from the manifest
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    # Full manifest JSON
    manifest_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # SHA-256 hash of the manifest for integrity verification
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ManifestStatus] = mapped_column(
        Enum(ManifestStatus),
        nullable=False,
        default=ManifestStatus.PENDING,
    )
    # Optional description/notes
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="manifests",
    )
    capability_tokens: Mapped[list["CapabilityToken"]] = relationship(  # noqa: F821
        "CapabilityToken",
        back_populates="manifest",
    )

    def __repr__(self) -> str:
        return f"<UapkManifest(id={self.id}, uapk_id={self.uapk_id}, version={self.version})>"
