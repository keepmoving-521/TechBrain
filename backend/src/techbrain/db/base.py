"""SQLAlchemy declarative base."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models.

    V0.1 only establishes the migration mechanism. Business tables are introduced by
    later requirements, while Alembic can already read this metadata object.
    """
