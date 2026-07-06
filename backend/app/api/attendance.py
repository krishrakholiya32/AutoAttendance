from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.courses import _get_owned_course
from app.core.database import get_db
from app.core.deps import get_current_professor
from app.core.logging import get_logger
from app.core.metrics import liveness_reject_total
from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.professor import Professor
from app.models.student import Student
from app.schemas.attendance import (
    AttendanceRecordOut,
    MarkAttendanceResponse,
    MatchedStudent,
    SessionCreate,
    SessionOut,
)
from app.services.face_service import extract_all_embeddings
from app.services.matching import find_best_match

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


@router.post("/sessions/{session_id}/mark", response_model=MarkAttendanceResponse)
async def mark_attendance(
    course_id: int,
    session_id: int,
    file: UploadFile = File(...),
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_session(course_id, session_id, professor, db)

    image_bytes = await file.read()
    detected_faces = extract_all_embeddings(image_bytes)
    if not detected_faces:
        raise HTTPException(status_code=422, detail="No faces detected in image")

    already_marked = {
        r.student_id for r in (await db.execute(
            select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
        )).scalars().all()
    }

    matched: list[MatchedStudent] = []
    unmatched_count = 0
    spoofed_count = 0
    for detected in detected_faces:
        if not detected.is_live:
            # A spoofed face (photo/screen held up to the camera) is a
            # distinct signal from "a stranger's face doesn't match anyone
            # enrolled" -- don't silently lump it into unmatched_count, and
            # don't reject the whole photo just because one of several faces
            # in a classroom shot is spoofed.
            spoofed_count += 1
            liveness_reject_total.labels(context="mark").inc()
            logger.info("liveness_reject", context="mark", course_id=course_id, session_id=session_id, score=detected.liveness_score)
            continue

        # HNSW-indexed nearest-neighbor query (pgvector) -- replaces the old
        # brute-force Python loop over the whole gallery fetched into memory.
        result = await find_best_match(db, course_id, detected.embedding)
        if result is None:
            unmatched_count += 1
            continue
        student_id, confidence = result
        if student_id in already_marked:
            continue  # same face photographed twice in one session shot, e.g. group re-take
        already_marked.add(student_id)

        student = await db.get(Student, student_id)
        db.add(AttendanceRecord(session_id=session_id, student_id=student_id, confidence=confidence))
        matched.append(MatchedStudent(
            student_id=student_id, name=student.name, roll_number=student.roll_number, confidence=confidence,
        ))

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
    return MarkAttendanceResponse(matched=matched, unmatched_face_count=unmatched_count, spoofed_face_count=spoofed_count)


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
