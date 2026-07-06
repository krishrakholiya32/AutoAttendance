from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow


class AttendanceSession(Base):
    """One taken-attendance event for a course (usually one per class meeting)."""

    __tablename__ = "attendance_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    session_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    course = relationship("Course", back_populates="sessions")
    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")
    jobs = relationship("AttendanceJob", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(Base):
    """A single student marked present in a session, via a matched face."""

    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("attendance_sessions.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("Student", back_populates="attendance_records")
