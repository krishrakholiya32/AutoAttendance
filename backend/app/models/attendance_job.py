from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow

# Plain strings, not a DB-level enum -- avoids an Alembic migration every
# time a new status is added, and SQLAlchemy validates the Python-side
# JobStatus values are used consistently anyway.
PENDING = "pending"
PROCESSING = "processing"
DONE = "done"
FAILED = "failed"


class AttendanceJob(Base):
    """A single attendance-marking task, processed asynchronously by the arq
    worker. Kept separate from AttendanceSession (a class meeting) since a
    session can be re-processed (e.g. a second classroom photo) across
    multiple jobs."""

    __tablename__ = "attendance_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("attendance_sessions.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default=PENDING)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session = relationship("AttendanceSession", back_populates="jobs")
