"""Alembic migration environment.

Wires Alembic to the application's ORM metadata and connection settings. The
database URL is resolved at runtime from the environment (``DATABASE_URL``)
with a fallback to the typed application config, so credentials are never
stored in ``alembic.ini``.

``target_metadata`` points at :data:`app.models.db_models.Base.metadata` so
``alembic revision --autogenerate`` can diff the ORM models against the live
schema. Both offline (SQL script emission) and online (direct connection)
modes are supported.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.config import ENV_DATABASE_URL, load_config
from app.models.db_models import Base

# Alembic Config object providing access to values in alembic.ini.
config = context.config

# Configure Python logging from the alembic.ini file, when present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata used by --autogenerate to detect schema changes.
target_metadata = Base.metadata


def _resolve_database_url() -> str:
    """Return the database URL from the environment or the typed app config.

    Precedence:
        1. ``DATABASE_URL`` environment variable (explicit, e.g. CI/one-off runs).
        2. The validated application config, which itself supports either
           ``DATABASE_URL`` or the ``DB_*`` component variables.

    Returns:
        A SQLAlchemy-compatible PostgreSQL connection URL.
    """
    explicit_url = os.environ.get(ENV_DATABASE_URL, "").strip()
    if explicit_url:
        return explicit_url

    return load_config().database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL (no live Engine), emitting SQL
    statements to the script output instead of executing them against a
    database. Useful for generating migration SQL for review.
    """
    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live database connection.

    Builds an Engine from the alembic config, overriding the (intentionally
    blank) ``sqlalchemy.url`` with the runtime-resolved connection URL, then
    runs migrations within a transaction.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _resolve_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
