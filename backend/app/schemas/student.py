from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentCreate(BaseModel):
    name: str
    roll_number: str


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    roll_number: str
    created_at: datetime
    angles_captured: int = 0


class EnrollFaceResponse(BaseModel):
    angle_label: str
    angles_captured: int
    required_angles: int
