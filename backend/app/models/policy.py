"""Policy model - rules for evaluating agent action requests."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PolicyType(str, enum.Enum):
    """Type of policy."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PolicyScope(str, enum.Enum):
    """Scope of policy application."""

    GLOBAL = "global"  # Applies to all actions
    ACTION = "action"  # Applies to specific action patterns
    AGENT = "agent"  # Applies to specific agents


class Policy(Base):
    """Policy - rules for evaluating agent action requests."""

    __tablename__ = "policies"

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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Policy type: allow, deny, or require human approval
    policy_type: Mapped[PolicyType] = mapped_column(
        Enum(PolicyType),
        nullable=False,
    )
    # Scope of the policy
    scope: Mapped[PolicyScope] = mapped_column(
        Enum(PolicyScope),
        nullable=False,
        default=PolicyScope.GLOBAL,
    )
    # Priority for evaluation order (higher = evaluated first)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Matching rules (JSON with conditions)
    # e.g., {"action_pattern": "email:*", "agent_ids": ["agent-1"], "parameters": {...}}
    rules: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Whether policy is active
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="policies",
    )

    def __repr__(self) -> str:
        return f"<Policy(id={self.id}, name={self.name}, type={self.policy_type})>"
