from datetime import datetime

from pydantic import BaseModel


class StudentCreate(BaseModel):
    name: str
    roll_number: str


class StudentOut(BaseModel):
    id: int
    name: str
    roll_number: str
    created_at: datetime
    angles_captured: int = 0

    class Config:
        from_attributes = True


class EnrollFaceResponse(BaseModel):
    angle_label: str
    angles_captured: int
    required_angles: int
