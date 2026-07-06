"""swap to pgvector column and add hnsw index

Revision ID: 9a4a156238cb
Revises: 9ba636b06ff8
Create Date: 2026-07-06 11:55:30.714183

Step 2 of 2 -- run only after 9ba636b06ff8 has soaked and been verified (row
counts / cosine-similarity parity between the old and new columns match).
Drops the old float[] column, renames vector_new -> vector, and builds the
HNSW index CONCURRENTLY so it doesn't lock the table (standard practice even
though this project's row count is tiny today).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a4a156238cb'
down_revision: Union[str, Sequence[str], None] = '9ba636b06ff8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("face_embeddings", "vector")
    op.alter_column("face_embeddings", "vector_new", new_column_name="vector")
    # Every FaceEmbedding row is created with a real embedding (the app never
    # inserts one without a vector), so this is safe -- fails loudly if that
    # invariant was ever violated, which is the correct behavior here.
    op.alter_column("face_embeddings", "vector", nullable=False)

    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_face_embeddings_vector_hnsw "
            "ON face_embeddings USING hnsw (vector vector_cosine_ops)"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_face_embeddings_vector_hnsw")
    op.alter_column("face_embeddings", "vector", nullable=True)
    op.alter_column("face_embeddings", "vector", new_column_name="vector_new")
    op.add_column("face_embeddings", sa.Column("vector", sa.ARRAY(sa.Float), nullable=True))
