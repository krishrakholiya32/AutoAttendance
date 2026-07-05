from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_professor
from app.models.course import Course
from app.models.professor import Professor
from app.models.student import Student
from app.schemas.course import CourseCreate, CourseOut

router = APIRouter(prefix="/courses", tags=["courses"])


async def _get_owned_course(course_id: int, professor: Professor, db: AsyncSession) -> Course:
    course = await db.scalar(
        select(Course).where(Course.id == course_id, Course.professor_id == professor.id)
    )
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


@router.post("", response_model=CourseOut)
async def create_course(
    payload: CourseCreate,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    course = Course(name=payload.name, code=payload.code, professor_id=professor.id)
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return CourseOut(id=course.id, name=course.name, code=course.code, created_at=course.created_at, student_count=0)


@router.get("", response_model=list[CourseOut])
async def list_courses(
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(
        select(Course, func.count(Student.id))
        .outerjoin(Student, Student.course_id == Course.id)
        .where(Course.professor_id == professor.id)
        .group_by(Course.id)
        .order_by(Course.created_at.desc())
    )
    return [
        CourseOut(id=c.id, name=c.name, code=c.code, created_at=c.created_at, student_count=count)
        for c, count in rows.all()
    ]


@router.get("/{course_id}", response_model=CourseOut)
async def get_course(
    course_id: int,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_owned_course(course_id, professor, db)
    count = await db.scalar(select(func.count(Student.id)).where(Student.course_id == course.id))
    return CourseOut(id=course.id, name=course.name, code=course.code, created_at=course.created_at, student_count=count or 0)


@router.delete("/{course_id}", status_code=204)
async def delete_course(
    course_id: int,
    professor: Professor = Depends(get_current_professor),
    db: AsyncSession = Depends(get_db),
):
    course = await _get_owned_course(course_id, professor, db)
    await db.delete(course)
    await db.commit()
