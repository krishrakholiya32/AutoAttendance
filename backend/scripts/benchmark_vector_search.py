"""Proves the HNSW index matters at a scale this project's real deployment
hasn't reached yet: seeds a course with 10k+ synthetic face embeddings and
times the old brute-force Python loop against the new pgvector HNSW-indexed
SQL query (app.services.matching.find_best_match).

Run against a disposable/scratch database -- set BENCHMARK_DATABASE_URL, or
it defaults to a local scratch db that must already exist and have the
`vector` extension available (any pgvector/pgvector:pg16 Postgres instance).
Not run as part of the test suite or CI -- this is a one-off proof artifact.

Usage:
    BENCHMARK_DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db \
        python scripts/benchmark_vector_search.py [--n 10000] [--trials 200]
"""

import argparse
import asyncio
import os
import statistics
import time

import numpy as np
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.course import Course
from app.models.embedding import EMBEDDING_DIM, FaceEmbedding
from app.models.professor import Professor
from app.models.student import Student
from app.services.face_service import cosine_similarity
from app.services.matching import find_best_match

DEFAULT_URL = "postgresql+asyncpg://autoattendance:autoattendance@localhost:5432/autoattendance_benchmark"


async def seed(session_factory, n: int) -> tuple[int, np.ndarray]:
    rng = np.random.default_rng(42)
    async with session_factory() as db:
        professor = Professor(email="benchmark@test.edu", password_hash="x", name="Benchmark")
        db.add(professor)
        await db.flush()
        course = Course(professor_id=professor.id, name="Benchmark Course", code="BENCH")
        db.add(course)
        await db.flush()
        course_id = course.id

        print(f"Seeding {n} synthetic embeddings...")
        batch = []
        for i in range(n):
            student = Student(course_id=course_id, name=f"Synthetic {i}", roll_number=str(i))
            db.add(student)
            await db.flush()
            vec = rng.normal(size=EMBEDDING_DIM).astype("float32")
            batch.append(FaceEmbedding(student_id=student.id, angle_label="front", vector=vec.tolist()))
            if len(batch) >= 500:
                db.add_all(batch)
                await db.flush()
                batch = []
        if batch:
            db.add_all(batch)
        await db.commit()

    probe = rng.normal(size=EMBEDDING_DIM).astype("float32")
    return course_id, probe


async def brute_force_python(session_factory, course_id: int, probe: np.ndarray) -> float:
    """Simulates the OLD approach: fetch the whole gallery into memory, loop in Python."""
    async with session_factory() as db:
        rows = (
            await db.execute(
                sa.select(FaceEmbedding.student_id, FaceEmbedding.vector)
                .join(Student, Student.id == FaceEmbedding.student_id)
                .where(Student.course_id == course_id)
            )
        ).all()

    t0 = time.perf_counter()
    best_score = -1.0
    for _student_id, vector in rows:
        score = cosine_similarity(probe, np.array(vector, dtype="float32"))
        if score > best_score:
            best_score = score
    return time.perf_counter() - t0


async def hnsw_sql(session_factory, course_id: int, probe: np.ndarray) -> float:
    """The new approach: a single HNSW-indexed nearest-neighbor SQL query."""
    async with session_factory() as db:
        t0 = time.perf_counter()
        await find_best_match(db, course_id, probe)
        return time.perf_counter() - t0


def percentile(values: list[float], p: float) -> float:
    return statistics.quantiles(values, n=100)[int(p) - 1] if len(values) > 1 else values[0]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10000, help="number of synthetic embeddings to seed")
    parser.add_argument("--trials", type=int, default=200, help="number of query trials per approach")
    args = parser.parse_args()

    url = os.environ.get("BENCHMARK_DATABASE_URL", DEFAULT_URL)
    engine = create_async_engine(url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
        from app.core.database import Base
        import app.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)

    course_id, probe = await seed(session_factory, args.n)

    print(f"\nRunning {args.trials} trials per approach against a {args.n}-embedding gallery...\n")

    brute_times = [await brute_force_python(session_factory, course_id, probe) for _ in range(args.trials)]
    hnsw_times = [await hnsw_sql(session_factory, course_id, probe) for _ in range(args.trials)]

    print(f"{'approach':<25} {'p50 (ms)':>10} {'p95 (ms)':>10} {'mean (ms)':>10}")
    for name, times in [("brute-force (Python)", brute_times), ("pgvector HNSW (SQL)", hnsw_times)]:
        p50 = percentile(times, 50) * 1000
        p95 = percentile(times, 95) * 1000
        mean = statistics.mean(times) * 1000
        print(f"{name:<25} {p50:>10.2f} {p95:>10.2f} {mean:>10.2f}")

    speedup = statistics.mean(brute_times) / statistics.mean(hnsw_times)
    print(f"\nHNSW is {speedup:.1f}x faster (mean) at n={args.n}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
