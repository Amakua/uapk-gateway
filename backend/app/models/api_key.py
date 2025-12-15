"""API Key model."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApiKeyStatus(str, enum.Enum):
    """Status of an API key."""

    ACTIVE = "active"
    REVOKED = "revoked"


class ApiKey(Base):
    """API Key for machine clients (agents)."""

    __tablename__ = "api_keys"

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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Store only a prefix for identification (e.g., "uapk_abc12...")
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    # Store only the hash of the full key
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ApiKeyStatus] = mapped_column(
        Enum(ApiKeyStatus),
        nullable=False,
        default=ApiKeyStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="api_keys",
    )

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name={self.name}, prefix={self.key_prefix})>"
