"""Interaction Record model - tamper-evident audit log entries."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Decision(str, enum.Enum):
    """Policy decision for an action request."""

    APPROVED = "approved"
    DENIED = "denied"
    PENDING = "pending"
    TIMEOUT = "timeout"


class InteractionRecord(Base):
    """Interaction Record - tamper-evident audit log entry for agent actions.

    Each record is:
    - Hash-chained to the previous record for the same UAPK
    - Signed by the gateway's Ed25519 key
    - Contains a full policy trace for audit

    Hash chain: record_hash = sha256(canonical_subset + previous_record_hash)
    Signature: Ed25519 signature over record_hash
    """

    __tablename__ = "interaction_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # External record ID (int-xxx format)
    record_id: Mapped[str] = mapped_column(
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
    # UAPK manifest ID - for hash chain grouping
    uapk_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Agent that made the request
    agent_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Capability token ID used (optional)
    capability_token_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("capability_tokens.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Action details (split for indexing)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tool: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Original request parameters and context (stored for reference)
    request: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # SHA-256 hash of canonicalized request
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Policy decision
    decision: Mapped[Decision] = mapped_column(
        Enum(Decision),
        nullable=False,
        index=True,
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Reasons as JSON array (canonical form)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured policy trace (which checks ran, results)
    policy_trace_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Risk snapshot at evaluation time
    risk_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Execution result (if approved and executed)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # SHA-256 hash of canonicalized result (null if no result)
    result_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Processing duration
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Hash chain fields
    # Hash of previous record in this UAPK's chain (null for first record)
    previous_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Hash of this record (computed from canonical subset + previous_record_hash)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Ed25519 signature over record_hash (base64 encoded)
    gateway_signature: Mapped[str] = mapped_column(String(128), nullable=False)

    # Legacy field for backwards compatibility
    signature: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Composite indexes for common queries
    __table_args__ = (
        Index("ix_interaction_records_org_uapk", "org_id", "uapk_id"),
        Index("ix_interaction_records_org_uapk_created", "org_id", "uapk_id", "created_at"),
        Index("ix_interaction_records_org_created", "org_id", "created_at"),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="interaction_records",
    )
    capability_token: Mapped["CapabilityToken | None"] = relationship(  # noqa: F821
        "CapabilityToken",
        back_populates="interaction_records",
    )

    def __repr__(self) -> str:
        return f"<InteractionRecord(record_id={self.record_id}, action={self.action_type}:{self.tool}, decision={self.decision})>"

    @property
    def action(self) -> str:
        """Get combined action string (for backwards compatibility)."""
        return f"{self.action_type}:{self.tool}"
