"""Knowledge synchronization task ORM models."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from techbrain.db.base import Base


class KnowledgeSyncTaskStatus(StrEnum):
    """Knowledge synchronization task status."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class KnowledgeSyncTask(Base):
    """A persisted full synchronization task summary."""

    __tablename__ = "knowledge_sync_tasks"
    __table_args__ = (
        CheckConstraint(
            "status in ('success', 'partial_success', 'failed')",
            name="ck_knowledge_sync_tasks_status",
        ),
        Index("ix_knowledge_sync_tasks_started_at", "started_at"),
        Index("ix_knowledge_sync_tasks_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    scanned_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    restored_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unchanged_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    failures: Mapped[list["KnowledgeSyncFailureRecord"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="KnowledgeSyncFailureRecord.id",
    )


class KnowledgeSyncFailureRecord(Base):
    """A persisted failure item for a synchronization task."""

    __tablename__ = "knowledge_sync_failures"
    __table_args__ = (
        Index("ix_knowledge_sync_failures_task_id", "task_id"),
        Index("ix_knowledge_sync_failures_path", "path"),
        Index("ix_knowledge_sync_failures_stage", "stage"),
        Index("ix_knowledge_sync_failures_code", "code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_sync_tasks.id", ondelete="CASCADE"),
        nullable=False,
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    stage: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(128), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    field: Mapped[str | None] = mapped_column(String(255), nullable=True)
    line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    column: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    task: Mapped[KnowledgeSyncTask] = relationship(back_populates="failures")
