from datetime import date, datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    session_date: date | None = None


class SessionOut(BaseModel):
    id: int
    session_date: date
    created_at: datetime

    class Config:
        from_attributes = True


class MatchedStudent(BaseModel):
    student_id: int
    name: str
    roll_number: str
    confidence: float


class MarkAttendanceResponse(BaseModel):
    matched: list[MatchedStudent]
    unmatched_face_count: int


class AttendanceRecordOut(BaseModel):
    student_id: int
    name: str
    roll_number: str
    present: bool
    confidence: float | None = None
