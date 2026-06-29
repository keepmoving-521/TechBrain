"""Create knowledge category table.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create hierarchical knowledge category table."""
    op.create_table(
        "knowledge_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("path", sa.String(length=512), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('active', 'hidden', 'archived')",
            name="ck_knowledge_categories_status",
        ),
        sa.CheckConstraint("id != parent_id", name="ck_knowledge_categories_not_self_parent"),
        sa.CheckConstraint("sort_order >= 0", name="ck_knowledge_categories_sort_order"),
        sa.ForeignKeyConstraint(["parent_id"], ["knowledge_categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_categories_parent_id", "knowledge_categories", ["parent_id"])
    op.create_index("ix_knowledge_categories_path", "knowledge_categories", ["path"], unique=True)
    op.create_index("ix_knowledge_categories_status", "knowledge_categories", ["status"])
    op.create_index(
        "ix_knowledge_categories_parent_sort",
        "knowledge_categories",
        ["parent_id", "sort_order"],
    )
    op.create_index(
        "ix_knowledge_categories_parent_slug",
        "knowledge_categories",
        ["parent_id", "slug"],
        unique=True,
    )


def downgrade() -> None:
    """Drop hierarchical knowledge category table."""
    op.drop_index("ix_knowledge_categories_parent_slug", table_name="knowledge_categories")
    op.drop_index("ix_knowledge_categories_parent_sort", table_name="knowledge_categories")
    op.drop_index("ix_knowledge_categories_status", table_name="knowledge_categories")
    op.drop_index("ix_knowledge_categories_path", table_name="knowledge_categories")
    op.drop_index("ix_knowledge_categories_parent_id", table_name="knowledge_categories")
    op.drop_table("knowledge_categories")
