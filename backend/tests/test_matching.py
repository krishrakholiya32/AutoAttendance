import numpy as np
import pytest

from app.core.database import async_session
from app.models.course import Course
from app.models.embedding import EMBEDDING_DIM, FaceEmbedding
from app.models.professor import Professor
from app.models.student import Student
from app.services.matching import find_best_match

pytestmark = pytest.mark.asyncio


def _unit(vec: list[float]) -> list[float]:
    """Embeds a small 2D test vector into the model's real 512-d space.
    Extra zero dimensions don't affect cosine similarity/distance."""
    padded = np.zeros(EMBEDDING_DIM, dtype="float32")
    padded[: len(vec)] = vec
    return padded.tolist()


async def _seed_course(db, email: str = "matchtest@test.edu") -> Course:
    professor = Professor(email=email, password_hash="x", name="Match Test")
    db.add(professor)
    await db.flush()
    course = Course(professor_id=professor.id, name="C", code="C1")
    db.add(course)
    await db.flush()
    return course


async def test_find_best_match_returns_closest_above_threshold():
    async with async_session() as db:
        course = await _seed_course(db)
        alice = Student(course_id=course.id, name="Alice", roll_number="A1")
        bob = Student(course_id=course.id, name="Bob", roll_number="B1")
        db.add_all([alice, bob])
        await db.flush()

        db.add(FaceEmbedding(student_id=alice.id, angle_label="front", vector=_unit([1, 0])))
        db.add(FaceEmbedding(student_id=bob.id, angle_label="front", vector=_unit([0, 1])))
        await db.commit()

        result = await find_best_match(db, course.id, np.array(_unit([1, 0])))
        assert result is not None
        student_id, similarity = result
        assert student_id == alice.id
        assert similarity > 0.9


async def test_find_best_match_below_threshold_returns_none():
    async with async_session() as db:
        course = await _seed_course(db)
        alice = Student(course_id=course.id, name="Alice", roll_number="A1")
        db.add(alice)
        await db.flush()
        db.add(FaceEmbedding(student_id=alice.id, angle_label="front", vector=_unit([0, 1])))
        await db.commit()

        result = await find_best_match(db, course.id, np.array(_unit([1, 0])))
        assert result is None


async def test_find_best_match_empty_gallery_returns_none():
    async with async_session() as db:
        course = await _seed_course(db)
        result = await find_best_match(db, course.id, np.array(_unit([1, 0])))
        assert result is None


async def test_find_best_match_scoped_to_course():
    async with async_session() as db:
        course_a = await _seed_course(db, email="matchtest-a@test.edu")
        course_b = await _seed_course(db, email="matchtest-b@test.edu")

        stranger = Student(course_id=course_b.id, name="Stranger", roll_number="S1")
        db.add(stranger)
        await db.flush()
        db.add(FaceEmbedding(student_id=stranger.id, angle_label="front", vector=_unit([1, 0])))
        await db.commit()

        # course_a has no enrolled students -- must not find course_b's student
        result = await find_best_match(db, course_a.id, np.array(_unit([1, 0])))
        assert result is None


async def test_find_best_match_picks_best_of_multiple_candidates():
    async with async_session() as db:
        course = await _seed_course(db)
        s1 = Student(course_id=course.id, name="S1", roll_number="R1")
        s2 = Student(course_id=course.id, name="S2", roll_number="R2")
        s3 = Student(course_id=course.id, name="S3", roll_number="R3")
        db.add_all([s1, s2, s3])
        await db.flush()

        db.add(FaceEmbedding(student_id=s1.id, angle_label="front", vector=_unit([0, 1])))
        db.add(FaceEmbedding(student_id=s2.id, angle_label="front", vector=_unit([1, 0])))
        db.add(FaceEmbedding(student_id=s3.id, angle_label="front", vector=_unit([-1, 0])))
        await db.commit()

        result = await find_best_match(db, course.id, np.array(_unit([1, 0.1])))
        assert result is not None
        assert result[0] == s2.id
