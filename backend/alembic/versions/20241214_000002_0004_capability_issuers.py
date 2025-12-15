"""Add capability_issuers table.

Revision ID: 0004
Revises: 0003
Create Date: 2024-12-14 00:00:02.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create issuer status enum
    issuer_status = postgresql.ENUM(
        "active", "revoked", name="issuerstatus", create_type=False
    )
    issuer_status.create(op.get_bind(), checkfirst=True)

    # Create capability_issuers table
    op.create_table(
        "capability_issuers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("issuer_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active", "revoked",
                name="issuerstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "issuer_id", name="uq_capability_issuer_org_issuer"),
    )
    op.create_index(
        op.f("ix_capability_issuers_org_id"), "capability_issuers", ["org_id"], unique=False
    )
    op.create_index(
        op.f("ix_capability_issuers_issuer_id"), "capability_issuers", ["issuer_id"], unique=False
    )


def downgrade() -> None:
    # Drop capability_issuers
    op.drop_index(op.f("ix_capability_issuers_issuer_id"), table_name="capability_issuers")
    op.drop_index(op.f("ix_capability_issuers_org_id"), table_name="capability_issuers")
    op.drop_table("capability_issuers")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS issuerstatus")
