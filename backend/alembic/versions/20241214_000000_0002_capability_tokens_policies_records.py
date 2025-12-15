"""Add capability tokens, policies, and interaction records.

Revision ID: 0002
Revises: 0001
Create Date: 2024-12-14 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create policy type enum
    policy_type = postgresql.ENUM(
        "allow", "deny", "require_approval", name="policytype", create_type=False
    )
    policy_type.create(op.get_bind(), checkfirst=True)

    # Create policy scope enum
    policy_scope = postgresql.ENUM(
        "global", "action", "agent", name="policyscope", create_type=False
    )
    policy_scope.create(op.get_bind(), checkfirst=True)

    # Create policies table
    op.create_table(
        "policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "policy_type",
            postgresql.ENUM(
                "allow", "deny", "require_approval", name="policytype", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "scope",
            postgresql.ENUM(
                "global", "action", "agent", name="policyscope", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), nullable=False, default=0),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, default=True),
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
    )
    op.create_index(op.f("ix_policies_org_id"), "policies", ["org_id"], unique=False)

    # Create capability_tokens table
    op.create_table(
        "capability_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("token_id", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(length=255), nullable=False),
        sa.Column("manifest_id", sa.UUID(), nullable=True),
        sa.Column("capabilities", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issued_by", sa.String(length=255), nullable=False),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("max_actions", sa.Integer(), nullable=True),
        sa.Column("actions_used", sa.Integer(), nullable=False, default=0),
        sa.Column("revoked", sa.Boolean(), nullable=False, default=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manifest_id"], ["uapk_manifests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_id"),
    )
    op.create_index(
        op.f("ix_capability_tokens_token_id"), "capability_tokens", ["token_id"], unique=True
    )
    op.create_index(
        op.f("ix_capability_tokens_org_id"), "capability_tokens", ["org_id"], unique=False
    )
    op.create_index(
        op.f("ix_capability_tokens_agent_id"), "capability_tokens", ["agent_id"], unique=False
    )
    op.create_index(
        op.f("ix_capability_tokens_manifest_id"), "capability_tokens", ["manifest_id"], unique=False
    )
    op.create_index(
        op.f("ix_capability_tokens_expires_at"), "capability_tokens", ["expires_at"], unique=False
    )

    # Create decision enum
    decision_enum = postgresql.ENUM(
        "approved", "denied", "pending", "timeout", name="decision", create_type=False
    )
    decision_enum.create(op.get_bind(), checkfirst=True)

    # Create interaction_records table
    op.create_table(
        "interaction_records",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("record_id", sa.String(length=64), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.String(length=255), nullable=False),
        sa.Column("capability_token_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("request", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "decision",
            postgresql.ENUM(
                "approved", "denied", "pending", "timeout", name="decision", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("policy_evaluations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("signature", sa.String(length=128), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["capability_token_id"], ["capability_tokens.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_id"),
    )
    op.create_index(
        op.f("ix_interaction_records_record_id"),
        "interaction_records",
        ["record_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_interaction_records_org_id"), "interaction_records", ["org_id"], unique=False
    )
    op.create_index(
        op.f("ix_interaction_records_agent_id"), "interaction_records", ["agent_id"], unique=False
    )
    op.create_index(
        op.f("ix_interaction_records_action"), "interaction_records", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_interaction_records_decision"), "interaction_records", ["decision"], unique=False
    )
    op.create_index(
        op.f("ix_interaction_records_timestamp"),
        "interaction_records",
        ["timestamp"],
        unique=False,
    )
    op.create_index(
        op.f("ix_interaction_records_capability_token_id"),
        "interaction_records",
        ["capability_token_id"],
        unique=False,
    )


def downgrade() -> None:
    # Drop interaction_records
    op.drop_index(
        op.f("ix_interaction_records_capability_token_id"), table_name="interaction_records"
    )
    op.drop_index(op.f("ix_interaction_records_timestamp"), table_name="interaction_records")
    op.drop_index(op.f("ix_interaction_records_decision"), table_name="interaction_records")
    op.drop_index(op.f("ix_interaction_records_action"), table_name="interaction_records")
    op.drop_index(op.f("ix_interaction_records_agent_id"), table_name="interaction_records")
    op.drop_index(op.f("ix_interaction_records_org_id"), table_name="interaction_records")
    op.drop_index(op.f("ix_interaction_records_record_id"), table_name="interaction_records")
    op.drop_table("interaction_records")

    # Drop capability_tokens
    op.drop_index(op.f("ix_capability_tokens_expires_at"), table_name="capability_tokens")
    op.drop_index(op.f("ix_capability_tokens_manifest_id"), table_name="capability_tokens")
    op.drop_index(op.f("ix_capability_tokens_agent_id"), table_name="capability_tokens")
    op.drop_index(op.f("ix_capability_tokens_org_id"), table_name="capability_tokens")
    op.drop_index(op.f("ix_capability_tokens_token_id"), table_name="capability_tokens")
    op.drop_table("capability_tokens")

    # Drop policies
    op.drop_index(op.f("ix_policies_org_id"), table_name="policies")
    op.drop_table("policies")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS decision")
    op.execute("DROP TYPE IF EXISTS policyscope")
    op.execute("DROP TYPE IF EXISTS policytype")
