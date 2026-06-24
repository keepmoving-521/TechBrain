"""Alembic migration command helpers.

Usage:
    python -m techbrain.db.migrate upgrade head
"""

import argparse

from alembic import command
from alembic.config import Config

from techbrain.core.config import BACKEND_DIR

ALEMBIC_INI_PATH = BACKEND_DIR / "alembic.ini"
MIGRATIONS_DIR = BACKEND_DIR / "migrations"


def make_alembic_config() -> Config:
    """Create an Alembic configuration bound to this backend project."""
    config = Config(str(ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    return config


def upgrade(revision: str = "head") -> None:
    """Upgrade database schema to the requested revision."""
    command.upgrade(make_alembic_config(), revision)


def downgrade(revision: str) -> None:
    """Downgrade database schema to the requested revision."""
    command.downgrade(make_alembic_config(), revision)


def current() -> None:
    """Print current database revision."""
    command.current(make_alembic_config())


def history() -> None:
    """Print migration history."""
    command.history(make_alembic_config())


def main(argv: list[str] | None = None) -> None:
    """Run Alembic commands through a stable project entrypoint."""
    parser = argparse.ArgumentParser(description="TechBrain database migrations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database schema")
    upgrade_parser.add_argument("revision", nargs="?", default="head")

    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database schema")
    downgrade_parser.add_argument("revision")

    subparsers.add_parser("current", help="Show current database revision")
    subparsers.add_parser("history", help="Show migration history")

    args = parser.parse_args(argv)

    if args.command == "upgrade":
        upgrade(args.revision)
    elif args.command == "downgrade":
        downgrade(args.revision)
    elif args.command == "current":
        current()
    elif args.command == "history":
        history()


if __name__ == "__main__":
    main()
