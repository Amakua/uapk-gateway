"""Enhance interaction_records for tamper-evident audit logging.

Adds hash chaining, Ed25519 signatures, and structured policy traces.

Revision ID: 0005
Revises: 0004
Create Date: 2024-12-14 00:00:03.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns for hash chaining and structured audit
    op.add_column(
        "interaction_records",
        sa.Column("uapk_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("action_type", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("tool", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("request_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("reasons_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("policy_trace_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("risk_snapshot_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("result_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("previous_record_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("record_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("gateway_signature", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )

    # Migrate data from old columns to new
    op.execute("""
        UPDATE interaction_records
        SET
            uapk_id = COALESCE(request->>'uapk_id', 'unknown'),
            action_type = SPLIT_PART(action, ':', 1),
            tool = COALESCE(SPLIT_PART(action, ':', 2), action),
            request_hash = '',
            reasons_json = '[]',
            policy_trace_json = '{"checks":[]}',
            record_hash = '',
            gateway_signature = COALESCE(signature, ''),
            created_at = "timestamp"
        WHERE uapk_id IS NULL
    """)

    # Make new columns NOT NULL after migration
    op.alter_column("interaction_records", "uapk_id", nullable=False)
    op.alter_column("interaction_records", "action_type", nullable=False)
    op.alter_column("interaction_records", "tool", nullable=False)
    op.alter_column("interaction_records", "request_hash", nullable=False)
    op.alter_column("interaction_records", "reasons_json", nullable=False)
    op.alter_column("interaction_records", "policy_trace_json", nullable=False)
    op.alter_column("interaction_records", "record_hash", nullable=False)
    op.alter_column("interaction_records", "gateway_signature", nullable=False)
    op.alter_column("interaction_records", "created_at", nullable=False)

    # Create new indexes
    op.create_index(
        op.f("ix_interaction_records_uapk_id"),
        "interaction_records",
        ["uapk_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interaction_records_action_type"),
        "interaction_records",
        ["action_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interaction_records_tool"),
        "interaction_records",
        ["tool"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interaction_records_record_hash"),
        "interaction_records",
        ["record_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interaction_records_created_at"),
        "interaction_records",
        ["created_at"],
        unique=False,
    )

    # Create composite indexes for common queries
    op.create_index(
        "ix_interaction_records_org_uapk",
        "interaction_records",
        ["org_id", "uapk_id"],
        unique=False,
    )
    op.create_index(
        "ix_interaction_records_org_uapk_created",
        "interaction_records",
        ["org_id", "uapk_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_interaction_records_org_created",
        "interaction_records",
        ["org_id", "created_at"],
        unique=False,
    )

    # Drop old indexes
    op.drop_index(op.f("ix_interaction_records_action"), table_name="interaction_records")
    op.drop_index(op.f("ix_interaction_records_timestamp"), table_name="interaction_records")

    # Drop old columns (keep action for reference, drop policy_evaluations)
    op.drop_column("interaction_records", "action")
    op.drop_column("interaction_records", "policy_evaluations")
    op.drop_column("interaction_records", "previous_hash")
    op.drop_column("interaction_records", "timestamp")


def downgrade() -> None:
    # Recreate old columns
    op.add_column(
        "interaction_records",
        sa.Column("action", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("policy_evaluations", sa.dialects.postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "interaction_records",
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
    )

    # Migrate data back
    op.execute("""
        UPDATE interaction_records
        SET
            action = action_type || ':' || tool,
            "timestamp" = created_at,
            previous_hash = previous_record_hash
        WHERE action IS NULL
    """)

    op.alter_column("interaction_records", "action", nullable=False)
    op.alter_column("interaction_records", "timestamp", nullable=False)

    # Recreate old indexes
    op.create_index(
        op.f("ix_interaction_records_action"),
        "interaction_records",
        ["action"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interaction_records_timestamp"),
        "interaction_records",
        ["timestamp"],
        unique=False,
    )

    # Drop new composite indexes
    op.drop_index("ix_interaction_records_org_created", table_name="interaction_records")
    op.drop_index("ix_interaction_records_org_uapk_created", table_name="interaction_records")
    op.drop_index("ix_interaction_records_org_uapk", table_name="interaction_records")

    # Drop new indexes
    op.drop_index(op.f("ix_interaction_records_created_at"), table_name="interaction_records")
    op.drop_index(op.f("ix_interaction_records_record_hash"), table_name="interaction_records")
    op.drop_index(op.f("ix_interaction_records_tool"), table_name="interaction_records")
    op.drop_index(op.f("ix_interaction_records_action_type"), table_name="interaction_records")
    op.drop_index(op.f("ix_interaction_records_uapk_id"), table_name="interaction_records")

    # Drop new columns
    op.drop_column("interaction_records", "created_at")
    op.drop_column("interaction_records", "gateway_signature")
    op.drop_column("interaction_records", "record_hash")
    op.drop_column("interaction_records", "previous_record_hash")
    op.drop_column("interaction_records", "result_hash")
    op.drop_column("interaction_records", "risk_snapshot_json")
    op.drop_column("interaction_records", "policy_trace_json")
    op.drop_column("interaction_records", "reasons_json")
    op.drop_column("interaction_records", "request_hash")
    op.drop_column("interaction_records", "tool")
    op.drop_column("interaction_records", "action_type")
    op.drop_column("interaction_records", "uapk_id")
