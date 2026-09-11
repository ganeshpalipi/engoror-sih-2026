"""
SQLAlchemy database setup for RootVerse.

Phase 1: engine + session factory + declarative Base + connection check.
Phase 3 adds the ORM models (users, settings, classroom_phrases, lessons,
flashcards, worksheets, translation_history, sync_metadata, model_metadata)
and seed data.
"""

import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# SQLite must allow cross-thread connections (FastAPI serves sync endpoints in
# a threadpool). Not needed for other database engines.
_IS_SQLITE = settings.DATABASE_URL.lower().startswith("sqlite")
_CONNECT_ARGS = {"check_same_thread": False} if _IS_SQLITE else {}


def _build_engine():
    """
    Create the SQLAlchemy engine.

    A malformed DATABASE_URL (typo in .env, stray shell variable) must never
    crash the whole server at import time - it falls back to local SQLite and
    logs the problem loudly (SIH rule #17: degrade, never crash).
    """
    try:
        return create_engine(
            settings.DATABASE_URL,
            connect_args=_CONNECT_ARGS,
            echo=False,  # set True only when debugging raw SQL
        )
    except Exception as exc:  # noqa: BLE001 - startup must survive bad config
        logger.error(
            "Invalid DATABASE_URL %r (%s). Falling back to sqlite:///./rootverse.db",
            settings.DATABASE_URL,
            exc,
        )
        return create_engine(
            "sqlite:///./rootverse.db",
            connect_args={"check_same_thread": False},
            echo=False,
        )


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for every ORM model in app/models/."""


def get_db():
    """FastAPI dependency: one session per request, always closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Return True if the database answers a trivial query.

    Used by the /health endpoint. Never raises - a failed database must
    degrade the health status, not crash the server.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - health check must never raise
        logger.error("Database connection failed: %s", exc)
        return False
