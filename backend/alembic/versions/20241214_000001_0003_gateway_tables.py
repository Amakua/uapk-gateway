"""Add gateway tables: action_counters, secrets, approvals.

Revision ID: 0003
Revises: 0002
Create Date: 2024-12-14 00:00:01.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create action_counters table
    op.create_table(
        "action_counters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("uapk_id", sa.String(length=255), nullable=False),
        sa.Column("counter_date", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, default=0),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "uapk_id", "counter_date", name="uq_action_counter_org_uapk_date"),
    )
    op.create_index(
        op.f("ix_action_counters_org_id"), "action_counters", ["org_id"], unique=False
    )
    op.create_index(
        op.f("ix_action_counters_uapk_id"), "action_counters", ["uapk_id"], unique=False
    )
    op.create_index(
        op.f("ix_action_counters_counter_date"),
        "action_counters",
        ["counter_date"],
        unique=False,
    )

    # Create secrets table
    op.create_table(
        "secrets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("encrypted_value", sa.LargeBinary(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "name", name="uq_secret_org_name"),
    )
    op.create_index(op.f("ix_secrets_org_id"), "secrets", ["org_id"], unique=False)
    op.create_index(op.f("ix_secrets_name"), "secrets", ["name"], unique=False)

    # Create approval status enum
    approval_status = postgresql.ENUM(
        "pending", "approved", "denied", "expired", name="approvalstatus", create_type=False
    )
    approval_status.create(op.get_bind(), checkfirst=True)

    # Create approvals table
    op.create_table(
        "approvals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("approval_id", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("interaction_id", sa.String(length=64), nullable=False),
        sa.Column("uapk_id", sa.String(length=255), nullable=False),
        sa.Column("agent_id", sa.String(length=255), nullable=False),
        sa.Column("action", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("counterparty", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason_codes", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "approved", "denied", "expired",
                name="approvalstatus",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.String(length=255), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("approval_id"),
    )
    op.create_index(
        op.f("ix_approvals_approval_id"), "approvals", ["approval_id"], unique=True
    )
    op.create_index(op.f("ix_approvals_org_id"), "approvals", ["org_id"], unique=False)
    op.create_index(
        op.f("ix_approvals_interaction_id"), "approvals", ["interaction_id"], unique=False
    )
    op.create_index(op.f("ix_approvals_uapk_id"), "approvals", ["uapk_id"], unique=False)
    op.create_index(op.f("ix_approvals_status"), "approvals", ["status"], unique=False)


def downgrade() -> None:
    # Drop approvals
    op.drop_index(op.f("ix_approvals_status"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_uapk_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_interaction_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_org_id"), table_name="approvals")
    op.drop_index(op.f("ix_approvals_approval_id"), table_name="approvals")
    op.drop_table("approvals")

    # Drop secrets
    op.drop_index(op.f("ix_secrets_name"), table_name="secrets")
    op.drop_index(op.f("ix_secrets_org_id"), table_name="secrets")
    op.drop_table("secrets")

    # Drop action_counters
    op.drop_index(op.f("ix_action_counters_counter_date"), table_name="action_counters")
    op.drop_index(op.f("ix_action_counters_uapk_id"), table_name="action_counters")
    op.drop_index(op.f("ix_action_counters_org_id"), table_name="action_counters")
    op.drop_table("action_counters")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS approvalstatus")
