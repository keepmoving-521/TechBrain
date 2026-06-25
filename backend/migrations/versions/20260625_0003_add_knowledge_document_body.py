"""Add knowledge document body.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25 00:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add parsed Markdown body column."""
    op.add_column(
        "knowledge_documents",
        sa.Column("body", sa.Text(), nullable=True),
    )
    op.execute("update knowledge_documents set body = '' where body is null")
    with op.batch_alter_table("knowledge_documents") as batch_op:
        batch_op.alter_column("body", existing_type=sa.Text(), nullable=False)


def downgrade() -> None:
    """Drop parsed Markdown body column."""
    op.drop_column("knowledge_documents", "body")
