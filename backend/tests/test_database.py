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
    finally:
        get_settings.cache_clear()

    assert version == ("0003",)
    assert table == ("knowledge_documents",)
    assert body_column == ("body",)


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
