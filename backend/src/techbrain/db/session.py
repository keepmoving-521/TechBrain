"""Database engine, session factory and connectivity checks."""

from dataclasses import dataclass
from functools import cached_property

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from techbrain.core.config import Settings


@dataclass(frozen=True)
class DatabaseCheckResult:
    """Result of a database connectivity check."""

    ok: bool
    message: str | None = None


class DatabaseManager:
    """Manage SQLAlchemy engine and sessions for one application process."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @cached_property
    def engine(self) -> Engine:
        """Return the lazily-created SQLAlchemy engine."""
        url = make_url(self._settings.database_url)
        connect_args: dict[str, object] = {}
        engine_options: dict[str, object] = {
            "future": True,
            "pool_pre_ping": self._settings.database_pool_pre_ping,
        }

        if url.get_backend_name() == "sqlite":
            connect_args["check_same_thread"] = False
            if url.database in (None, "", ":memory:"):
                engine_options["poolclass"] = StaticPool
        else:
            engine_options.update(
                {
                    "pool_size": self._settings.database_pool_size,
                    "max_overflow": self._settings.database_max_overflow,
                    "pool_recycle": self._settings.database_pool_recycle_seconds,
                }
            )

        return create_engine(url, connect_args=connect_args, **engine_options)

    @cached_property
    def session_factory(self) -> sessionmaker[Session]:
        """Return a configured SQLAlchemy session factory."""
        return sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def check_connection(self) -> DatabaseCheckResult:
        """Execute a lightweight query to verify database connectivity."""
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            return DatabaseCheckResult(ok=False, message=str(exc))
        return DatabaseCheckResult(ok=True)

    def dispose(self) -> None:
        """Close all pooled connections."""
        if "engine" in self.__dict__:
            self.engine.dispose()
