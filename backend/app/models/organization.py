"""Organization model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Organization(Base):
    """Organization - top-level tenant."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    memberships: Mapped[list["Membership"]] = relationship(  # noqa: F821
        "Membership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    api_keys: Mapped[list["ApiKey"]] = relationship(  # noqa: F821
        "ApiKey",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    manifests: Mapped[list["UapkManifest"]] = relationship(  # noqa: F821
        "UapkManifest",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    capability_tokens: Mapped[list["CapabilityToken"]] = relationship(  # noqa: F821
        "CapabilityToken",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    interaction_records: Mapped[list["InteractionRecord"]] = relationship(  # noqa: F821
        "InteractionRecord",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    policies: Mapped[list["Policy"]] = relationship(  # noqa: F821
        "Policy",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    action_counters: Mapped[list["ActionCounter"]] = relationship(  # noqa: F821
        "ActionCounter",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    secrets: Mapped[list["Secret"]] = relationship(  # noqa: F821
        "Secret",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    approvals: Mapped[list["Approval"]] = relationship(  # noqa: F821
        "Approval",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
    capability_issuers: Mapped[list["CapabilityIssuer"]] = relationship(  # noqa: F821
        "CapabilityIssuer",
        back_populates="organization",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Organization(id={self.id}, slug={self.slug})>"
