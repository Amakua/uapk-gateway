"""Capability Issuer model - registered public keys for token verification."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IssuerStatus(str, enum.Enum):
    """Status of a capability issuer."""

    ACTIVE = "active"
    REVOKED = "revoked"


class CapabilityIssuer(Base):
    """Registered capability token issuer with public key."""

    __tablename__ = "capability_issuers"

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
    # Unique issuer identifier (e.g., "gateway", "external-system-1")
    issuer_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Human-readable name
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Base64-encoded Ed25519 public key
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    # Description
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[IssuerStatus] = mapped_column(
        Enum(IssuerStatus),
        nullable=False,
        default=IssuerStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Unique constraint for org + issuer_id
    __table_args__ = (
        UniqueConstraint("org_id", "issuer_id", name="uq_capability_issuer_org_issuer"),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="capability_issuers",
    )

    def __repr__(self) -> str:
        return f"<CapabilityIssuer(issuer_id={self.issuer_id}, org_id={self.org_id})>"
