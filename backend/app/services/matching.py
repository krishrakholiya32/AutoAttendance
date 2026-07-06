import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.embedding import FaceEmbedding
from app.models.student import Student


async def find_best_match(
    db: AsyncSession, course_id: int, probe_embedding: np.ndarray
) -> tuple[int, float] | None:
    """Finds the closest enrolled face embedding (across all students/angles in
    this course) using pgvector's HNSW-indexed cosine distance operator, replacing
    the brute-force Python loop that used to fetch the whole gallery into memory.
    Returns (student_id, similarity) if the closest match clears
    settings.face_match_threshold, else None."""
    probe_list = probe_embedding.tolist()
    distance = FaceEmbedding.vector.cosine_distance(probe_list)

    result = await db.execute(
        select(FaceEmbedding.student_id, distance.label("distance"))
        .join(Student, Student.id == FaceEmbedding.student_id)
        .where(Student.course_id == course_id)
        .order_by(distance)
        .limit(1)
    )
    row = result.first()
    if row is None:
        return None

    student_id, cosine_distance = row
    similarity = 1 - cosine_distance
    if similarity < settings.face_match_threshold:
        return None
    return student_id, similarity
