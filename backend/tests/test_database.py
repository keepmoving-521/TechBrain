"""Database infrastructure tests."""

import sqlite3
import uuid
from pathlib import Path

from techbrain.core.config import get_settings
from techbrain.db.migrate import (
    ALEMBIC_INI_PATH,
    MIGRATIONS_DIR,
    main,
    make_alembic_config,
    upgrade,
)
from techbrain.db.session import DatabaseManager


def test_database_manager_can_check_sqlite_connection(settings) -> None:
    manager = DatabaseManager(settings)

    try:
        result = manager.check_connection()
    finally:
        manager.dispose()

    assert result.ok is True
    assert result.message is None


def test_alembic_config_uses_project_migration_paths() -> None:
    config = make_alembic_config()

    assert Path(config.config_file_name or "") == ALEMBIC_INI_PATH
    assert Path(config.get_main_option("script_location")) == MIGRATIONS_DIR


def test_empty_database_can_be_initialized_with_alembic(monkeypatch) -> None:
    test_dir = Path(".pytest_tmp")
    test_dir.mkdir(exist_ok=True)
    database_path = test_dir / f"techbrain_migration_test_{uuid.uuid4().hex}.db"

    monkeypatch.setenv("TECHBRAIN_DATABASE_URL", f"sqlite+pysqlite:///{database_path.as_posix()}")
    get_settings.cache_clear()

    try:
        upgrade("head")

        with sqlite3.connect(database_path) as connection:
            version = connection.execute("select version_num from alembic_version").fetchone()
            table = connection.execute(
                "select name from sqlite_master "
                "where type = 'table' and name = 'knowledge_documents'"
            ).fetchone()
            body_column = connection.execute(
                "select name from pragma_table_info('knowledge_documents') where name = 'body'"
            ).fetchone()
            task_table = connection.execute(
                "select name from sqlite_master "
                "where type = 'table' and name = 'knowledge_sync_tasks'"
            ).fetchone()
            failure_table = connection.execute(
                "select name from sqlite_master "
                "where type = 'table' and name = 'knowledge_sync_failures'"
            ).fetchone()
            category_table = connection.execute(
                "select name from sqlite_master "
                "where type = 'table' and name = 'knowledge_categories'"
            ).fetchone()
            category_id_column = connection.execute(
                "select name from pragma_table_info('knowledge_documents') "
                "where name = 'category_id'"
            ).fetchone()
    finally:
        get_settings.cache_clear()

    assert version == ("0006",)
    assert table == ("knowledge_documents",)
    assert body_column == ("body",)
    assert task_table == ("knowledge_sync_tasks",)
    assert failure_table == ("knowledge_sync_failures",)
    assert category_table == ("knowledge_categories",)
    assert category_id_column == ("category_id",)


def test_category_link_migration_backfills_existing_documents(monkeypatch) -> None:
    test_dir = Path(".pytest_tmp")
    test_dir.mkdir(exist_ok=True)
    database_path = test_dir / f"techbrain_category_backfill_{uuid.uuid4().hex}.db"

    monkeypatch.setenv("TECHBRAIN_DATABASE_URL", f"sqlite+pysqlite:///{database_path.as_posix()}")
    get_settings.cache_clear()

    try:
        upgrade("0005")
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "insert into knowledge_documents ("
                "document_id, title, category, body, status, visibility, language, "
                "relative_path, absolute_path, path_hash, content_hash, front_matter_hash, "
                "tags, aliases, source, source_created_at, source_updated_at, sync_status, "
                "is_deleted"
                ") values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "existing-document",
                    "Existing document",
                    "backend/python",
                    "# Existing document",
                    "published",
                    "private",
                    "zh-CN",
                    "backend/python/existing.md",
                    "D:/Knowledge/backend/python/existing.md",
                    "a" * 64,
                    "b" * 64,
                    "c" * 64,
                    "[]",
                    "[]",
                    "{}",
                    "2026-06-29 10:00:00",
                    "2026-06-29 10:00:00",
                    "synced",
                    0,
                ),
            )
            connection.commit()

        upgrade("head")

        with sqlite3.connect(database_path) as connection:
            categories = connection.execute(
                "select path, parent_id from knowledge_categories order by path"
            ).fetchall()
            document_link = connection.execute(
                "select c.path from knowledge_documents d "
                "join knowledge_categories c on c.id = d.category_id"
            ).fetchone()
    finally:
        get_settings.cache_clear()

    assert categories[0] == ("backend", None)
    assert categories[1][0] == "backend/python"
    assert categories[1][1] is not None
    assert document_link == ("backend/python",)


def test_migration_cli_dispatches_commands(monkeypatch) -> None:
    calls: list[tuple[str, str | None]] = []

    monkeypatch.setattr(
        "techbrain.db.migrate.upgrade",
        lambda revision="head": calls.append(("upgrade", revision)),
    )
    monkeypatch.setattr(
        "techbrain.db.migrate.downgrade",
        lambda revision: calls.append(("downgrade", revision)),
    )
    monkeypatch.setattr("techbrain.db.migrate.current", lambda: calls.append(("current", None)))
    monkeypatch.setattr("techbrain.db.migrate.history", lambda: calls.append(("history", None)))

    main(["upgrade"])
    main(["upgrade", "0001"])
    main(["downgrade", "base"])
    main(["current"])
    main(["history"])

    assert calls == [
        ("upgrade", "head"),
        ("upgrade", "0001"),
        ("downgrade", "base"),
        ("current", None),
        ("history", None),
    ]
