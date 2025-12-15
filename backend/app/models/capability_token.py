"""Capability Token model - scoped authorization tokens for agents."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CapabilityToken(Base):
    """Capability Token - scoped authorization token for agent actions."""

    __tablename__ = "capability_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # External token ID (cap-xxx format)
    token_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Agent this token is issued to
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Manifest this token was issued against
    manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("uapk_manifests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Granted capabilities (e.g., ["email:send", "file:read"])
    capabilities: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
    )
    # Token timestamps
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    # Who issued the token (user ID or "system")
    issued_by: Mapped[str] = mapped_column(String(255), nullable=False)
    # Token-specific constraints
    constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Usage tracking
    max_actions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actions_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Revocation
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="capability_tokens",
    )
    manifest: Mapped["UapkManifest | None"] = relationship(  # noqa: F821
        "UapkManifest",
        back_populates="capability_tokens",
    )
    interaction_records: Mapped[list["InteractionRecord"]] = relationship(  # noqa: F821
        "InteractionRecord",
        back_populates="capability_token",
    )

    def __repr__(self) -> str:
        return f"<CapabilityToken(token_id={self.token_id}, agent_id={self.agent_id})>"
