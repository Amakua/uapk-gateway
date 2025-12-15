"""Membership model - links users to organizations with roles."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MembershipRole(str, enum.Enum):
    """Roles for organization membership."""

    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Membership(Base):
    """Membership - links a user to an organization with a specific role."""

    __tablename__ = "memberships"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(MembershipRole),
        nullable=False,
        default=MembershipRole.VIEWER,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="memberships",
    )
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="memberships",
    )

    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_membership_org_user"),
    )

    def __repr__(self) -> str:
        return f"<Membership(org_id={self.org_id}, user_id={self.user_id}, role={self.role})>"
