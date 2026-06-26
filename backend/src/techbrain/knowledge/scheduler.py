"""Periodic knowledge synchronization scheduler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Event, Lock, RLock, Thread

from techbrain.core.config import Settings
from techbrain.core.logging import get_logger
from techbrain.db.session import DatabaseManager
from techbrain.knowledge.config import (
    KnowledgeConfigurationError,
    build_knowledge_repository_config,
)
from techbrain.knowledge.task import (
    KnowledgeFullSyncResult,
    KnowledgeSyncFailure,
    record_full_sync_result,
    run_full_knowledge_sync,
)

logger = get_logger(__name__)


@dataclass(frozen=True)
class KnowledgeSyncScheduleState:
    """Runtime state of periodic knowledge synchronization."""

    enabled: bool
    interval_seconds: int
    running: bool
    last_started_at: datetime | None = None
    last_finished_at: datetime | None = None
    last_task_id: int | None = None
    last_error: str | None = None


class KnowledgeSyncScheduler:
    """Run full knowledge synchronization periodically in a background thread."""

    def __init__(
        self,
        settings: Settings,
        database: DatabaseManager,
        sync_lock: Lock,
    ) -> None:
        self._settings = settings
        self._database = database
        self._sync_lock = sync_lock
        self._state_lock = RLock()
        self._stop_event = Event()
        self._thread: Thread | None = None
        self._enabled = settings.knowledge_auto_sync_enabled
        self._interval_seconds = settings.knowledge_auto_sync_interval_seconds
        self._running = False
        self._last_started_at: datetime | None = None
        self._last_finished_at: datetime | None = None
        self._last_task_id: int | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        """Start the background scheduler when periodic sync is enabled."""
        with self._state_lock:
            if not self._enabled or self._is_thread_alive():
                return
            self._stop_event.clear()
            self._thread = Thread(
                target=self._run_loop,
                name="techbrain-knowledge-sync-scheduler",
                daemon=True,
            )
            self._thread.start()
            logger.info(
                "knowledge.sync.scheduler.started",
                extra={"interval_seconds": self._interval_seconds},
            )

    def stop(self) -> None:
        """Stop the background scheduler if it is running."""
        with self._state_lock:
            thread = self._thread
            self._thread = None
            self._stop_event.set()
        if thread and thread.is_alive():
            thread.join(timeout=5)
            logger.info("knowledge.sync.scheduler.stopped")

    def get_state(self) -> KnowledgeSyncScheduleState:
        """Return a snapshot of scheduler configuration and runtime state."""
        with self._state_lock:
            return KnowledgeSyncScheduleState(
                enabled=self._enabled,
                interval_seconds=self._interval_seconds,
                running=self._running,
                last_started_at=self._last_started_at,
                last_finished_at=self._last_finished_at,
                last_task_id=self._last_task_id,
                last_error=self._last_error,
            )

    def update(
        self,
        *,
        enabled: bool | None = None,
        interval_seconds: int | None = None,
    ) -> KnowledgeSyncScheduleState:
        """Update periodic sync runtime configuration."""
        if interval_seconds is not None and interval_seconds < 60:
            raise ValueError("定时同步周期不能小于 60 秒")

        should_start = False
        should_stop = False
        with self._state_lock:
            if interval_seconds is not None:
                self._interval_seconds = interval_seconds
                self._stop_event.set()
                should_start = self._enabled
            if enabled is not None:
                self._enabled = enabled
                should_start = enabled
                should_stop = not enabled
            state = self.get_state()

        if should_stop:
            self.stop()
        elif should_start:
            self.stop()
            self.start()
        return state

    def run_once(self) -> int | None:
        """Run one full synchronization if no other sync task is currently running."""
        if not self._sync_lock.acquire(blocking=False):
            self._record_skipped_overlap()
            return None

        started_at = datetime.now(UTC)
        self._mark_started(started_at)
        try:
            task_id = self._execute_sync(started_at)
            self._mark_finished(task_id=task_id, error=None)
            return task_id
        except Exception as exc:
            logger.exception("knowledge.sync.scheduler.failed")
            self._mark_finished(task_id=None, error=str(exc))
            raise
        finally:
            self._sync_lock.release()

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self._current_interval()):
            with self._state_lock:
                if not self._enabled:
                    continue
            try:
                self.run_once()
            except Exception:
                continue

    def _execute_sync(self, started_at: datetime) -> int:
        try:
            config = build_knowledge_repository_config(self._settings)
        except KnowledgeConfigurationError as exc:
            return self._record_configuration_error(started_at, exc)

        with self._database.session_factory() as session:
            result = run_full_knowledge_sync(session, config, started_at=started_at)
            return result.task_id or 0

    def _record_configuration_error(
        self,
        started_at: datetime,
        exc: KnowledgeConfigurationError,
    ) -> int:
        result = KnowledgeFullSyncResult(
            started_at=started_at,
            finished_at=datetime.now(UTC),
            scanned_count=0,
            failed_count=1,
            failures=(
                KnowledgeSyncFailure(
                    path="-",
                    stage="configuration",
                    code="KNOWLEDGE_CONFIGURATION_ERROR",
                    message=str(exc),
                ),
            ),
        )
        with self._database.session_factory() as session:
            task = record_full_sync_result(session, result)
            session.commit()
            return task.id

    def _mark_started(self, started_at: datetime) -> None:
        with self._state_lock:
            self._running = True
            self._last_started_at = started_at
            self._last_error = None

    def _mark_finished(self, *, task_id: int | None, error: str | None) -> None:
        with self._state_lock:
            self._running = False
            self._last_finished_at = datetime.now(UTC)
            self._last_task_id = task_id
            self._last_error = error

    def _record_skipped_overlap(self) -> None:
        with self._state_lock:
            self._last_error = "知识库同步任务正在执行, 已跳过本次定时同步"
        logger.info("knowledge.sync.scheduler.skipped_overlap")

    def _current_interval(self) -> int:
        with self._state_lock:
            return self._interval_seconds

    def _is_thread_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
