"""Add idempotent event processing receipts."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_processed_events"
down_revision: str | None = "0004_tool_call_audit"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_processed_events_event_id"),
    )
    op.create_index(
        "ix_processed_events_tenant_processed",
        "processed_events",
        ["tenant_id", "processed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_processed_events_tenant_processed", table_name="processed_events")
    op.drop_table("processed_events")
