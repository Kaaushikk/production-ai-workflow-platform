"""Add tenant-scoped query history."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_query_history"
down_revision: str | None = "0002_chunk_embeddings"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "queries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=False),
        sa.Column("abstained", sa.Boolean(), nullable=False),
        sa.Column("provider_name", sa.String(length=100), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_queries_tenant_created", "queries", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_queries_tenant_created", table_name="queries")
    op.drop_table("queries")

