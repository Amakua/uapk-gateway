"""Secret storage model with Fernet encryption."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Secret(Base):
    """Encrypted secrets for tool connectors."""

    __tablename__ = "secrets"

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
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Encrypted value stored as bytes
    encrypted_value: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Unique constraint for org + name
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_secret_org_name"),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="secrets",
    )

    def __repr__(self) -> str:
        return f"<Secret(name={self.name}, org_id={self.org_id})>"
