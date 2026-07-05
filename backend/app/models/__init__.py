from app.models.attendance import AttendanceRecord, AttendanceSession
from app.models.course import Course
from app.models.embedding import FaceEmbedding
from app.models.professor import Professor
from app.models.student import Student

__all__ = [
    "Professor",
    "Course",
    "Student",
    "FaceEmbedding",
    "AttendanceSession",
    "AttendanceRecord",
]
