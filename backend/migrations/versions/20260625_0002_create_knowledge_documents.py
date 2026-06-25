"""Create knowledge documents table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-25 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create knowledge document metadata table."""
    op.create_table(
        "knowledge_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("visibility", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("relative_path", sa.String(length=1024), nullable=False),
        sa.Column("absolute_path", sa.String(length=2048), nullable=False),
        sa.Column("path_hash", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("front_matter_hash", sa.String(length=64), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("source", sa.JSON(), nullable=False),
        sa.Column("source_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sync_status", sa.String(length=32), nullable=False),
        sa.Column("sync_error", sa.Text(), nullable=True),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
            "status in ('published', 'draft', 'archived', 'deprecated')",
            name="ck_knowledge_documents_status",
        ),
        sa.CheckConstraint(
            "visibility in ('private', 'shared')",
            name="ck_knowledge_documents_visibility",
        ),
        sa.CheckConstraint(
            "sync_status in ('pending', 'synced', 'failed', 'deleted')",
            name="ck_knowledge_documents_sync_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_knowledge_documents_document_id",
        "knowledge_documents",
        ["document_id"],
        unique=True,
    )
    op.create_index(
        "ix_knowledge_documents_relative_path",
        "knowledge_documents",
        ["relative_path"],
        unique=True,
    )
    op.create_index(
        "ix_knowledge_documents_path_hash",
        "knowledge_documents",
        ["path_hash"],
    )
    op.create_index(
        "ix_knowledge_documents_content_hash",
        "knowledge_documents",
        ["content_hash"],
    )
    op.create_index(
        "ix_knowledge_documents_status",
        "knowledge_documents",
        ["status"],
    )
    op.create_index(
        "ix_knowledge_documents_sync_status",
        "knowledge_documents",
        ["sync_status"],
    )
    op.create_index(
        "ix_knowledge_documents_is_deleted",
        "knowledge_documents",
        ["is_deleted"],
    )


def downgrade() -> None:
    """Drop knowledge document metadata table."""
    op.drop_index("ix_knowledge_documents_is_deleted", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_sync_status", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_status", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_content_hash", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_path_hash", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_relative_path", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_document_id", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")
