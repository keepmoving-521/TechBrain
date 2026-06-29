"""Create knowledge tags and document-tag associations.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-29 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create normalized tags and their many-to-many document links."""
    op.create_table(
        "knowledge_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
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
            "status in ('active', 'archived')",
            name="ck_knowledge_tags_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_tags_normalized_name",
        "knowledge_tags",
        ["normalized_name"],
        unique=True,
    )
    op.create_index("ix_knowledge_tags_status", "knowledge_tags", ["status"])

    op.create_table(
        "knowledge_document_tags",
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["knowledge_documents.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["tag_id"], ["knowledge_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "tag_id"),
    )
    op.create_index(
        "ix_knowledge_document_tags_tag_id",
        "knowledge_document_tags",
        ["tag_id"],
    )


def downgrade() -> None:
    """Drop document-tag associations and normalized tags."""
    op.drop_index("ix_knowledge_document_tags_tag_id", table_name="knowledge_document_tags")
    op.drop_table("knowledge_document_tags")
    op.drop_index("ix_knowledge_tags_status", table_name="knowledge_tags")
    op.drop_index("ix_knowledge_tags_normalized_name", table_name="knowledge_tags")
    op.drop_table("knowledge_tags")
