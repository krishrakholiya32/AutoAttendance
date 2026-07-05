from datetime import datetime

from pydantic import BaseModel


class CourseCreate(BaseModel):
    name: str
    code: str


class CourseOut(BaseModel):
    id: int
    name: str
    code: str
    created_at: datetime
    student_count: int = 0

    class Config:
        from_attributes = True
