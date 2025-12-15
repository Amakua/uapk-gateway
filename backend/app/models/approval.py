"""Approval task model for escalated actions."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApprovalStatus(str, enum.Enum):
    """Status of an approval task."""

    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class Approval(Base):
    """Approval task for escalated actions requiring human review."""

    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # External approval ID (appr-xxx format)
    approval_id: Mapped[str] = mapped_column(
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
    # Reference to the interaction record
    interaction_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Agent info
    uapk_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # Action details (stored for review)
    action: Mapped[dict] = mapped_column(JSONB, nullable=False)
    counterparty: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Reason codes that triggered escalation
    reason_codes: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    # Status
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus),
        nullable=False,
        default=ApprovalStatus.PENDING,
        index=True,
    )
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    # Decision info
    decided_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    decision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Override token fields (for approved actions)
    override_token_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="SHA-256 hash of override token",
    )
    action_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="SHA-256 hash of action params (binds token to specific action)",
    )
    override_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Override token expiration timestamp",
    )
    override_token_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when override token was used",
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="approvals",
    )

    def __repr__(self) -> str:
        return f"<Approval(approval_id={self.approval_id}, status={self.status})>"
