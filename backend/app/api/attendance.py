from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from opentelemetry.propagate import inject
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.courses import _get_owned_course
from app.core.database import get_db
from app.core.deps import get_current_professor
from app.core.logging import get_logger
from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.attendance_job import PENDING, AttendanceJob
from app.models.professor import Professor
from app.models.student import Student
from app.schemas.attendance import (
    AttendanceRecordOut,
    JobStatusResponse,
    MarkJobAccepted,
    SessionCreate,
    SessionOut,
)
from app.worker import get_redis_pool

router = APIRouter(prefix="/courses/{course_id}/attendance", tags=["attendance"])
logger = get_logger(__name__)


async def _get_owned_session(course_id: int, session_id: int, professor: Professor, db: AsyncSession) -> AttendanceSession:
    await _get_owned_course(course_id, professor, db)
    session = await db.scalar(
        select(AttendanceSession).where(
            AttendanceSession.id == session_id, AttendanceSession.course_id == course_id
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions", response_model=SessionOut)
async def create_session(
    course_id: int,
    payload: SessionCreate,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_course(course_id, professor, db)
    session = AttendanceSession(course_id=course_id, session_date=payload.session_date or date.today())
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=list[SessionOut])
async def list_sessions(
    course_id: int,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_course(course_id, professor, db)
    rows = await db.execute(
        select(AttendanceSession)
        .where(AttendanceSession.course_id == course_id)
        .order_by(AttendanceSession.session_date.desc())
    )
    return rows.scalars().all()


@router.post("/sessions/{session_id}/mark", response_model=MarkJobAccepted, status_code=202)
async def mark_attendance(
    course_id: int,
    session_id: int,
    file: UploadFile = File(...),
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    """Enqueues the classroom photo for async processing (app/tasks/attendance_tasks.py)
    instead of blocking the request on face-worker + matching -- a large multi-face
    photo can take a few seconds, which shouldn't tie up the HTTP request thread.
    Poll GET .../jobs/{job_id} for the result."""
    await _get_owned_session(course_id, session_id, professor, db)

    image_bytes = await file.read()
    job = AttendanceJob(session_id=session_id, status=PENDING)
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # arq jobs cross a Redis boundary, so the current trace context doesn't propagate
    # automatically the way an outgoing HTTP header would -- inject it into a plain
    # dict now and re-attach it as the parent span when the worker picks the job up,
    # so one trace can span request -> enqueue -> dequeue -> face-worker -> DB write.
    carrier: dict[str, str] = {}
    inject(carrier)

    redis = await get_redis_pool()
    await redis.enqueue_job(
        "process_attendance_photo", job.id, course_id, session_id, image_bytes, carrier.get("traceparent")
    )

    return MarkJobAccepted(job_id=job.id, status=job.status)


@router.get("/sessions/{session_id}/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    course_id: int,
    session_id: int,
    job_id: int,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_session(course_id, session_id, professor, db)

    job = await db.get(AttendanceJob, job_id)
    if job is None or job.session_id != session_id:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(job_id=job.id, status=job.status, result=job.result, error=job.error)


@router.get("/sessions/{session_id}", response_model=list[AttendanceRecordOut])
async def get_session_records(
    course_id: int,
    session_id: int,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_session(course_id, session_id, professor, db)

    students = (await db.execute(select(Student).where(Student.course_id == course_id))).scalars().all()
    records = {
        r.student_id: r for r in (await db.execute(
            select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
        )).scalars().all()
    }

    return [
        AttendanceRecordOut(
            student_id=s.id,
            name=s.name,
            roll_number=s.roll_number,
            present=s.id in records,
            confidence=records[s.id].confidence if s.id in records else None,
        )
        for s in students
    ]
