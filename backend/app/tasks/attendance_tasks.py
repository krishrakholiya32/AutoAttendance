from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import async_session
from app.core.logging import get_logger
from app.core.metrics import liveness_reject_total
from app.models.attendance import AttendanceRecord
from app.models.attendance_job import DONE, FAILED, PROCESSING, AttendanceJob
from app.models.student import Student
from app.services.face_client import extract_all_embeddings
from app.services.matching import find_best_match

logger = get_logger(__name__)


async def process_attendance_photo(
    ctx, job_id: int, course_id: int, session_id: int, image_bytes: bytes
) -> None:
    """arq task: does the actual face-worker call + pgvector matching that
    used to run synchronously inside the mark-attendance request handler.
    Runs in a separate worker process (backend/app/worker.py), never the API
    process, so a slow/large classroom photo never blocks a request thread."""
    async with async_session() as db:
        job = await db.get(AttendanceJob, job_id)
        job.status = PROCESSING
        await db.commit()

        try:
            detected_faces = await extract_all_embeddings(image_bytes)
            if not detected_faces:
                job.status = FAILED
                job.error = "No faces detected in image"
                job.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            already_marked = {
                r.student_id
                for r in (
                    await db.execute(
                        select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
                    )
                ).scalars().all()
            }

            matched = []
            unmatched_count = 0
            spoofed_count = 0
            for detected in detected_faces:
                if not detected.is_live:
                    spoofed_count += 1
                    liveness_reject_total.labels(context="mark").inc()
                    logger.info(
                        "liveness_reject",
                        context="mark",
                        course_id=course_id,
                        session_id=session_id,
                        score=detected.liveness_score,
                    )
                    continue

                result = await find_best_match(db, course_id, detected.embedding)
                if result is None:
                    unmatched_count += 1
                    continue
                student_id, confidence = result
                if student_id in already_marked:
                    continue
                already_marked.add(student_id)

                student = await db.get(Student, student_id)
                db.add(AttendanceRecord(session_id=session_id, student_id=student_id, confidence=confidence))
                matched.append({
                    "student_id": student_id,
                    "name": student.name,
                    "roll_number": student.roll_number,
                    "confidence": confidence,
                })

            job.status = DONE
            job.result = {
                "matched": matched,
                "unmatched_face_count": unmatched_count,
                "spoofed_face_count": spoofed_count,
            }
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            logger.info(
                "attendance_marked",
                course_id=course_id,
                session_id=session_id,
                faces_detected=len(detected_faces),
                matched_count=len(matched),
                unmatched_count=unmatched_count,
                spoofed_count=spoofed_count,
            )
        except Exception as e:
            await db.rollback()
            job.status = FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()
            raise
