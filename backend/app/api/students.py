from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.courses import _get_owned_course
from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_professor
from app.core.logging import get_logger
from app.core.metrics import liveness_reject_total
from app.models.embedding import FaceEmbedding
from app.models.professor import Professor
from app.models.student import Student
from app.schemas.student import EnrollFaceResponse, StudentCreate, StudentOut
from app.services.face_client import extract_single_embedding

router = APIRouter(prefix="/courses/{course_id}/students", tags=["students"])
logger = get_logger(__name__)


async def _get_owned_student(course_id: int, student_id: int, professor: Professor, db: AsyncSession) -> Student:
    await _get_owned_course(course_id, professor, db)
    student = await db.scalar(
        select(Student).where(Student.id == student_id, Student.course_id == course_id)
    )
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.post("", response_model=StudentOut)
async def add_student(
    course_id: int,
    payload: StudentCreate,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_course(course_id, professor, db)
    student = Student(course_id=course_id, name=payload.name, roll_number=payload.roll_number)
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return StudentOut(
        id=student.id, name=student.name, roll_number=student.roll_number,
        created_at=student.created_at, angles_captured=0,
    )


@router.get("", response_model=list[StudentOut])
async def list_students(
    course_id: int,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_course(course_id, professor, db)
    rows = await db.execute(select(Student).where(Student.course_id == course_id))
    students = rows.scalars().all()

    out = []
    for s in students:
        embeddings = (await db.execute(
            select(FaceEmbedding).where(FaceEmbedding.student_id == s.id)
        )).scalars().all()
        out.append(StudentOut(
            id=s.id, name=s.name, roll_number=s.roll_number,
            created_at=s.created_at, angles_captured=len(embeddings),
        ))
    return out


@router.delete("/{student_id}", status_code=204)
async def delete_student(
    course_id: int,
    student_id: int,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    student = await _get_owned_student(course_id, student_id, professor, db)
    await db.delete(student)
    await db.commit()


@router.post("/{student_id}/enroll-face", response_model=EnrollFaceResponse)
async def enroll_face(
    course_id: int,
    student_id: int,
    angle_label: str,
    file: UploadFile = File(...),
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    student = await _get_owned_student(course_id, student_id, professor, db)

    image_bytes = await file.read()
    detected = await extract_single_embedding(image_bytes)
    if detected is None:
        raise HTTPException(status_code=422, detail="No face detected in image")
    if not detected.is_live:
        liveness_reject_total.labels(context="enroll").inc()
        logger.info("liveness_reject", context="enroll", student_id=student.id, score=detected.liveness_score)
        raise HTTPException(status_code=422, detail={"code": "spoof_detected", "message": "This looks like a photo of a photo/screen, not a live camera capture."})

    existing = (await db.execute(
        select(FaceEmbedding).where(
            FaceEmbedding.student_id == student.id, FaceEmbedding.angle_label == angle_label
        )
    )).scalar_one_or_none()
    if existing is not None:
        existing.vector = detected.embedding.tolist()
    else:
        db.add(FaceEmbedding(student_id=student.id, angle_label=angle_label, vector=detected.embedding.tolist()))
    await db.commit()

    all_embeddings = (await db.execute(
        select(FaceEmbedding).where(FaceEmbedding.student_id == student.id)
    )).scalars().all()

    return EnrollFaceResponse(
        angle_label=angle_label,
        angles_captured=len(all_embeddings),
        required_angles=settings.max_embeddings_per_student,
    )
