from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow

EMBEDDING_DIM = 512


class FaceEmbedding(Base):
    """One row per enrollment capture (a student has several: front/left/right/etc)."""

    __tablename__ = "face_embeddings"
    __table_args__ = (
        # Declared here so Alembic's autogenerate knows about it and doesn't
        # flag it as drift to remove on every future migration -- the index
        # itself is created CONCURRENTLY in a hand-written migration since
        # autogenerate can't produce HNSW DDL.
        Index(
            "ix_face_embeddings_vector_hnsw",
            "vector",
            postgresql_using="hnsw",
            postgresql_ops={"vector": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    angle_label: Mapped[str] = mapped_column(String(50))
    vector: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    student = relationship("Student", back_populates="embeddings")
