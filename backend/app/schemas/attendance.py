from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    session_date: date | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_date: date
    created_at: datetime


class MatchedStudent(BaseModel):
    student_id: int
    name: str
    roll_number: str
    confidence: float


class MarkAttendanceResponse(BaseModel):
    matched: list[MatchedStudent]
    unmatched_face_count: int
    spoofed_face_count: int = 0


class AttendanceRecordOut(BaseModel):
    student_id: int
    name: str
    roll_number: str
    present: bool
    confidence: float | None = None
