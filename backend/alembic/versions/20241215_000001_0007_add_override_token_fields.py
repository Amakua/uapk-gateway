"""Add override token fields to approvals table.

Revision ID: 0007
Revises: 0006
Create Date: 2025-12-15

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add override token fields to approvals table."""
    op.add_column(
        "approvals",
        sa.Column(
            "override_token_hash",
            sa.String(64),
            nullable=True,
            comment="SHA-256 hash of override token",
        ),
    )
    op.add_column(
        "approvals",
        sa.Column(
            "action_hash",
            sa.String(64),
            nullable=True,
            comment="SHA-256 hash of action params (binds token to specific action)",
        ),
    )
    op.add_column(
        "approvals",
        sa.Column(
            "override_token_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Override token expiration timestamp",
        ),
    )
    op.add_column(
        "approvals",
        sa.Column(
            "override_token_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when override token was used",
        ),
    )

    # Add index on override_token_hash for efficient lookups
    op.create_index(
        "ix_approvals_override_token_hash",
        "approvals",
        ["override_token_hash"],
    )


def downgrade() -> None:
    """Remove override token fields from approvals table."""
    op.drop_index("ix_approvals_override_token_hash", table_name="approvals")
    op.drop_column("approvals", "override_token_used_at")
    op.drop_column("approvals", "override_token_expires_at")
    op.drop_column("approvals", "action_hash")
    op.drop_column("approvals", "override_token_hash")
