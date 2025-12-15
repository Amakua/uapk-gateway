"""Add used_override_tokens table for approval override token tracking.

Revision ID: 0006
Revises: 0005
Create Date: 2025-12-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add used_override_tokens table.

    This table tracks used override tokens to prevent replay attacks.
    Override tokens are single-use tokens issued when approvals are granted.
    """
    op.create_table(
        "used_override_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True, nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("approval_id", sa.String(50), nullable=False, index=True),
        sa.Column("action_hash", sa.String(64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),

        # Indexes for efficient lookups
        sa.Index("ix_used_override_tokens_org_id", "org_id"),
        sa.Index("ix_used_override_tokens_approval_id", "approval_id"),
        sa.Index("ix_used_override_tokens_expires_at", "expires_at"),
    )

    # Add comment to table
    op.execute(
        """
        COMMENT ON TABLE used_override_tokens IS
        'Tracks used approval override tokens to prevent replay attacks'
        """
    )

    # Add comments to columns
    op.execute(
        """
        COMMENT ON COLUMN used_override_tokens.token_hash IS
        'SHA-256 hash of the override token (prevents token leakage in logs)'
        """
    )
    op.execute(
        """
        COMMENT ON COLUMN used_override_tokens.action_hash IS
        'SHA-256 hash of the action parameters (binds token to specific action)'
        """
    )


def downgrade() -> None:
    """Remove used_override_tokens table."""
    op.drop_table("used_override_tokens")
