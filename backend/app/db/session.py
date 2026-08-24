"""Database engine, connection pool and session factory.

Single place that owns the SQLAlchemy engine and its connection pool for the
backend service. The engine is created lazily from the typed application
configuration so connection details come solely from the environment — no
``os.environ`` reads happen here.

Design notes:
- Connection pooling is enabled via SQLAlchemy's default :class:`QueuePool`
  with ``pool_pre_ping`` to drop stale connections before use.
- A hard statement timeout is applied to every database session so no query can
  hang a request longer than ``db_query_timeout_seconds`` (default 5s). For
  PostgreSQL/psycopg this is passed as a libpq ``options`` connect argument
  (``-c statement_timeout=<milliseconds>``).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.config import AppConfig, get_config

DEFAULT_POOL_SIZE = 5
DEFAULT_MAX_OVERFLOW = 10
DEFAULT_POOL_TIMEOUT_SECONDS = 30
DEFAULT_POOL_RECYCLE_SECONDS = 1800  # Recycle after 30 min — shorter than typical cloud
                                    # DB idle timeouts to avoid stale connection errors.

_MILLISECONDS_PER_SECOND = 1000


def _build_connect_args(config: AppConfig) -> dict[str, str]:
    """Build psycopg connect arguments enforcing the query statement timeout.

    Args:
        config: The validated application configuration.

    Returns:
        A mapping suitable for SQLAlchemy's ``connect_args`` that instructs
        PostgreSQL to abort any statement exceeding the configured timeout.
    """
    timeout_ms = config.db_query_timeout_seconds * _MILLISECONDS_PER_SECOND
    return {"options": f"-c statement_timeout={timeout_ms}"}


def create_db_engine(config: AppConfig | None = None) -> Engine:
    """Create a pooled SQLAlchemy engine from the application configuration.

    Args:
        config: Optional configuration override; defaults to :func:`get_config`.

    Returns:
        A configured :class:`~sqlalchemy.engine.Engine` with connection pooling
        and a per-statement timeout applied to every connection.
    """
    resolved = config if config is not None else get_config()
    return create_engine(
        resolved.database_url,
        pool_size=DEFAULT_POOL_SIZE,
        max_overflow=DEFAULT_MAX_OVERFLOW,
        pool_timeout=DEFAULT_POOL_TIMEOUT_SECONDS,
        pool_recycle=DEFAULT_POOL_RECYCLE_SECONDS,
        pool_pre_ping=True,
        connect_args=_build_connect_args(resolved),
        future=True,
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return the process-wide database engine, creating it once on first use.

    Returns:
        The shared :class:`~sqlalchemy.engine.Engine`.
    """
    return create_db_engine()


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide session factory bound to the shared engine.

    Returns:
        A :class:`~sqlalchemy.orm.sessionmaker` producing new ORM sessions.
    """
    return sessionmaker(
        bind=get_engine(),
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session scope as a context manager.

    Commits on success, rolls back on any exception, and always closes the
    session (returning its connection to the pool).

    Yields:
        An active :class:`~sqlalchemy.orm.Session`.
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Iterator[Session]:
    """Yield a database session for use as a FastAPI dependency.

    Wraps :func:`session_scope` as a generator so FastAPI's ``Depends``
    mechanism can call ``next()`` to enter the context and generator cleanup
    to exit it. For non-FastAPI callers (tests, scripts), use
    ``session_scope()`` directly as a context manager.

    Yields:
        An active :class:`~sqlalchemy.orm.Session`.
    """
    with session_scope() as session:
        yield session
