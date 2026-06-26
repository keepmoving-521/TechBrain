"""Periodic knowledge synchronization scheduler tests."""

from pathlib import Path
from threading import Lock
from uuid import uuid4

from sqlalchemy import select

from techbrain.core.config import Environment, Settings
from techbrain.db.base import Base
from techbrain.db.session import DatabaseManager
from techbrain.knowledge.scheduler import KnowledgeSyncScheduler
from techbrain.models import KnowledgeDocument, KnowledgeSyncFailureRecord, KnowledgeSyncTask


def _settings(root: Path | None) -> Settings:
    return Settings(
        environment=Environment.TEST,
        database_url="sqlite+pysqlite:///:memory:",
        knowledge_root=root.resolve() if root else None,
        knowledge_auto_sync_enabled=False,
        knowledge_auto_sync_interval_seconds=120,
    )


def _root(name: str) -> Path:
    root = Path(".pytest_tmp") / f"{name}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_markdown(root: Path) -> None:
    path = root / "backend/python/sqlalchemy-joinedload.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
schema_version: 1
id: sqlalchemy-joinedload
title: SQLAlchemy joinedload 使用指南
category: backend/python
created_at: 2026-06-25T10:00:00+08:00
updated_at: 2026-06-25T10:30:00+08:00
---

# SQLAlchemy joinedload 使用指南
""",
        encoding="utf-8",
    )


def _scheduler(settings: Settings) -> tuple[KnowledgeSyncScheduler, DatabaseManager]:
    database = DatabaseManager(settings)
    Base.metadata.create_all(database.engine)
    return KnowledgeSyncScheduler(settings, database, Lock()), database


def test_scheduler_run_once_creates_task_and_syncs_document() -> None:
    root = _root("scheduler_success")
    _write_markdown(root)
    scheduler, database = _scheduler(_settings(root))

    task_id = scheduler.run_once()
    state = scheduler.get_state()

    with database.session_factory() as session:
        task = session.get(KnowledgeSyncTask, task_id)
        document = session.scalar(select(KnowledgeDocument))

    assert task_id is not None
    assert task is not None
    assert task.status == "success"
    assert task.scanned_count == 1
    assert document is not None
    assert document.document_id == "sqlalchemy-joinedload"
    assert state.running is False
    assert state.last_task_id == task_id
    assert state.last_error is None


def test_scheduler_run_once_skips_when_sync_lock_is_held() -> None:
    settings = _settings(_root("scheduler_overlap"))
    database = DatabaseManager(settings)
    Base.metadata.create_all(database.engine)
    sync_lock = Lock()
    scheduler = KnowledgeSyncScheduler(settings, database, sync_lock)

    sync_lock.acquire()
    try:
        task_id = scheduler.run_once()
    finally:
        sync_lock.release()

    with database.session_factory() as session:
        tasks = session.scalars(select(KnowledgeSyncTask)).all()

    assert task_id is None
    assert tasks == []
    assert scheduler.get_state().last_error == "知识库同步任务正在执行, 已跳过本次定时同步"


def test_scheduler_records_configuration_failure() -> None:
    scheduler, database = _scheduler(_settings(None))

    task_id = scheduler.run_once()

    with database.session_factory() as session:
        task = session.get(KnowledgeSyncTask, task_id)
        failure = session.scalar(select(KnowledgeSyncFailureRecord))

    assert task_id is not None
    assert task is not None
    assert task.status == "failed"
    assert task.failed_count == 1
    assert failure is not None
    assert failure.stage == "configuration"
    assert failure.code == "KNOWLEDGE_CONFIGURATION_ERROR"


def test_scheduler_can_update_runtime_schedule() -> None:
    scheduler, _database = _scheduler(_settings(_root("scheduler_update")))

    state = scheduler.update(enabled=True, interval_seconds=180)
    try:
        assert state.enabled is True
        assert state.interval_seconds == 180
        assert scheduler.get_state().enabled is True
    finally:
        state = scheduler.update(enabled=False)

    assert state.enabled is False
