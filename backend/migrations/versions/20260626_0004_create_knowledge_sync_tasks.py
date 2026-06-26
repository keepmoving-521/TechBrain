"""Create knowledge synchronization task tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create synchronization task and failure tables."""
    op.create_table(
        "knowledge_sync_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scanned_count", sa.Integer(), nullable=False),
        sa.Column("success_count", sa.Integer(), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False),
        sa.Column("created_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("restored_count", sa.Integer(), nullable=False),
        sa.Column("unchanged_count", sa.Integer(), nullable=False),
        sa.Column("deleted_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status in ('success', 'partial_success', 'failed')",
            name="ck_knowledge_sync_tasks_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_sync_tasks_started_at", "knowledge_sync_tasks", ["started_at"])
    op.create_index("ix_knowledge_sync_tasks_status", "knowledge_sync_tasks", ["status"])

    op.create_table(
        "knowledge_sync_failures",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("field", sa.String(length=255), nullable=True),
        sa.Column("line", sa.Integer(), nullable=True),
        sa.Column("column", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["knowledge_sync_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_sync_failures_task_id", "knowledge_sync_failures", ["task_id"])
    op.create_index("ix_knowledge_sync_failures_path", "knowledge_sync_failures", ["path"])
    op.create_index("ix_knowledge_sync_failures_stage", "knowledge_sync_failures", ["stage"])
    op.create_index("ix_knowledge_sync_failures_code", "knowledge_sync_failures", ["code"])


def downgrade() -> None:
    """Drop synchronization task and failure tables."""
    op.drop_index("ix_knowledge_sync_failures_code", table_name="knowledge_sync_failures")
    op.drop_index("ix_knowledge_sync_failures_stage", table_name="knowledge_sync_failures")
    op.drop_index("ix_knowledge_sync_failures_path", table_name="knowledge_sync_failures")
    op.drop_index("ix_knowledge_sync_failures_task_id", table_name="knowledge_sync_failures")
    op.drop_table("knowledge_sync_failures")

    op.drop_index("ix_knowledge_sync_tasks_status", table_name="knowledge_sync_tasks")
    op.drop_index("ix_knowledge_sync_tasks_started_at", table_name="knowledge_sync_tasks")
    op.drop_table("knowledge_sync_tasks")
