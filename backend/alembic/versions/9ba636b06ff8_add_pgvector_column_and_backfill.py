"""add pgvector column and backfill

Revision ID: 9ba636b06ff8
Revises: 0b031d78f6b7
Create Date: 2026-07-06 11:55:29.808719

Step 1 of 2 in the ARRAY(Float) -> pgvector migration. Purely additive and
safe to run against live production data: adds a new nullable vector(512)
column alongside the existing float[] column and backfills it by casting
through text (Postgres has no direct float[] -> vector cast). The old column
is left untouched so this can be verified/soaked before step 2 (see
9a4a156238cb) drops it and adds the HNSW index.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '9ba636b06ff8'
down_revision: Union[str, Sequence[str], None] = '0b031d78f6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("face_embeddings", sa.Column("vector_new", Vector(512), nullable=True))
    op.execute(
        """
        UPDATE face_embeddings
        SET vector_new = ('[' || array_to_string(vector, ',') || ']')::vector
        WHERE vector IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("face_embeddings", "vector_new")
