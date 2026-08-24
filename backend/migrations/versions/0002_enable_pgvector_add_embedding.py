"""Enable pgvector and add the optional ``embedding`` column (vector mode).

Opt-in follow-up to migration 0001 that turns on similarity search in
``vector`` mode (see Requirements 10.3, 11.4). It performs three forward-only
steps against the existing ``analysis_record`` table:

1. ``CREATE EXTENSION IF NOT EXISTS vector`` so the pgvector type/operators are
   available in the target database.
2. Add a nullable ``embedding`` column of type ``vector(N)`` where ``N`` matches
   the ORM's ``EMBEDDING_DIMENSIONS`` constant.
3. Create an approximate-nearest-neighbor (ANN) index using the HNSW method with
   ``vector_cosine_ops`` to support cosine-distance lookups (operator ``<=>``).

This migration is kept separate from 0001 so that keyword-only deployments never
require the pgvector extension. Migrations are forward-only and sequentially
numbered (Requirements 11.6); an already-applied migration is never edited — new
changes become new files. The ``downgrade`` drops the index and column but
intentionally leaves the ``vector`` extension in place, since other objects in
the database may depend on it.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Dimensionality of the stored Vector_Embedding. Kept as a named constant to
# avoid a magic number and to stay in sync with the ORM model
# (``app.models.db_models.EMBEDDING_DIMENSIONS``). If a different embedding model
# is adopted, update both locations together.
EMBEDDING_DIMENSIONS = 1536

# Object names as named constants to avoid string drift between the
# upgrade/downgrade paths and to stay in sync with migration 0001 and the ORM.
TABLE_NAME = "analysis_record"
EMBEDDING_COLUMN = "embedding"
EMBEDDING_ANN_INDEX = "ix_analysis_record_embedding_hnsw"

# Guarded import: prefer pgvector's native column type, but keep this module
# importable when the optional ``pgvector`` dependency is absent (the extension
# is still created via raw SQL at upgrade time regardless of the Python import).
try:
    from pgvector.sqlalchemy import Vector

    _EMBEDDING_COLUMN_TYPE: sa.types.TypeEngine = Vector(EMBEDDING_DIMENSIONS)
except ImportError:  # pragma: no cover - depends on optional dependency
    # Fallback lets the migration module load without pgvector installed. The
    # column is created with an explicit ``vector(N)`` type via the type's SQL
    # compilation only when pgvector is present; this placeholder exists solely
    # so Alembic can import the module during discovery.
    _EMBEDDING_COLUMN_TYPE = sa.Text()


def upgrade() -> None:
    """Enable pgvector, add the embedding column, and build the ANN index."""
    # Enable the extension first so the ``vector`` type resolves. IF NOT EXISTS
    # keeps this idempotent when the extension is already installed.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.add_column(
        TABLE_NAME,
        sa.Column(EMBEDDING_COLUMN, _EMBEDDING_COLUMN_TYPE, nullable=True),
    )

    # HNSW index with cosine-distance operator class supports ANN queries using
    # the ``<=>`` operator. HNSW is chosen over IVFFlat because it does not
    # require the table to be pre-populated to build a usable index.
    op.execute(
        f"CREATE INDEX {EMBEDDING_ANN_INDEX} "
        f"ON {TABLE_NAME} "
        f"USING hnsw ({EMBEDDING_COLUMN} vector_cosine_ops);"
    )


def downgrade() -> None:
    """Drop the ANN index and embedding column; keep the vector extension.

    The extension is deliberately left installed because dropping it could
    break unrelated objects that also depend on pgvector.
    """
    op.drop_index(EMBEDDING_ANN_INDEX, table_name=TABLE_NAME)
    op.drop_column(TABLE_NAME, EMBEDDING_COLUMN)
