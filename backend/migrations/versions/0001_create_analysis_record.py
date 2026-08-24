"""Create the analysis_record table with its six core columns.

Establishes the persistent store for CI/CD log analyses. Rows written here form
the retrieval corpus for RAG: past analyses become context for future ones
(see Requirements 9.2, 11.2). This migration creates only the six core columns
and an index on ``build_number``; the optional pgvector ``embedding`` column is
added separately by migration 0002 so vector mode stays opt-in
(see Requirements 11.4, 11.6).

Migrations are forward-only and sequentially numbered (Requirements 11.1,
11.3, 11.6). The provided ``downgrade`` drops the table to keep the
environment tidy in non-production/test runs; it is not intended to be run
against production data.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Table and index names as named constants to avoid string drift across the
# upgrade/downgrade paths and to stay in sync with the ORM model.
TABLE_NAME = "analysis_record"
BUILD_NUMBER_INDEX = "ix_analysis_record_build_number"


def upgrade() -> None:
    """Create the analysis_record table and the build_number index."""
    op.create_table(
        TABLE_NAME,
        sa.Column(
            "id",
            sa.BigInteger(),
            primary_key=True,
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("build_number", sa.Text(), nullable=False),
        sa.Column("cleaned_log", sa.Text(), nullable=False),
        sa.Column("analysis_result", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # Index supports keyword-mode retrieval and exclusion of the current build.
    op.create_index(BUILD_NUMBER_INDEX, TABLE_NAME, ["build_number"])


def downgrade() -> None:
    """Drop the build_number index and the analysis_record table."""
    op.drop_index(BUILD_NUMBER_INDEX, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
