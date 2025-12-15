"""Action counter model for budget tracking."""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ActionCounter(Base):
    """Tracks daily action counts per UAPK for budget enforcement."""

    __tablename__ = "action_counters"

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
    uapk_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    counter_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Unique constraint for org + uapk + date
    __table_args__ = (
        UniqueConstraint("org_id", "uapk_id", "counter_date", name="uq_action_counter_org_uapk_date"),
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # noqa: F821
        "Organization",
        back_populates="action_counters",
    )

    def __repr__(self) -> str:
        return f"<ActionCounter(uapk_id={self.uapk_id}, date={self.counter_date}, count={self.count})>"
