from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from app.core.database import async_session
from app.models.attendance_job import DONE, FAILED, PENDING, AttendanceJob
from app.services.face_client import DetectedFace
from app.tasks.attendance_tasks import process_attendance_photo

pytestmark = pytest.mark.asyncio

FAKE_LIVE_FACE = DetectedFace(embedding=np.ones(512, dtype="float32"), is_live=True, liveness_score=3.5)
STRANGER_FACE = DetectedFace(embedding=-np.ones(512, dtype="float32"), is_live=True, liveness_score=3.5)
SPOOFED_FACE = DetectedFace(embedding=np.ones(512, dtype="float32"), is_live=False, liveness_score=-3.5)


async def _make_course_with_enrolled_student(client, auth_headers):
    course = (await client.post("/courses", json={"name": "C", "code": "C1"}, headers=auth_headers)).json()
    student = (
        await client.post(
            f"/courses/{course['id']}/students",
            json={"name": "Alice", "roll_number": "R1"},
            headers=auth_headers,
        )
    ).json()
    with patch("app.api.students.extract_single_embedding", return_value=FAKE_LIVE_FACE):
        await client.post(
            f"/courses/{course['id']}/students/{student['id']}/enroll-face?angle_label=front",
            files={"file": ("test.jpg", b"x", "image/jpeg")},
            headers=auth_headers,
        )
    return course, student


# --- API layer: enqueueing + job status endpoint -----------------------------


async def test_mark_attendance_returns_202_and_creates_pending_job(client, auth_headers):
    course, _ = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    fake_redis = AsyncMock()
    with patch("app.api.attendance.get_redis_pool", return_value=fake_redis):
        resp = await client.post(
            f"/courses/{course['id']}/attendance/sessions/{session['id']}/mark",
            files={"file": ("photo.jpg", b"x", "image/jpeg")},
            headers=auth_headers,
        )
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == PENDING
    job_id = body["job_id"]

    status_resp = await client.get(
        f"/courses/{course['id']}/attendance/sessions/{session['id']}/jobs/{job_id}",
        headers=auth_headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == PENDING
    assert status_resp.json()["result"] is None


async def test_job_status_404_for_wrong_session(client, auth_headers):
    course, _ = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()
    resp = await client.get(
        f"/courses/{course['id']}/attendance/sessions/{session['id']}/jobs/99999",
        headers=auth_headers,
    )
    assert resp.status_code == 404


# --- Worker task: the actual matching business logic -------------------------


async def _run_task(session_id: int, course_id: int, detected_faces: list[DetectedFace]) -> AttendanceJob:
    async with async_session() as db:
        job = AttendanceJob(session_id=session_id, status=PENDING)
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job_id = job.id

    with patch("app.tasks.attendance_tasks.extract_all_embeddings", return_value=detected_faces):
        await process_attendance_photo(None, job_id, course_id, session_id, b"x")

    async with async_session() as db:
        return await db.get(AttendanceJob, job_id)


async def test_process_attendance_photo_matches_enrolled_student(client, auth_headers):
    course, student = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    job = await _run_task(session["id"], course["id"], [FAKE_LIVE_FACE])
    assert job.status == DONE
    assert len(job.result["matched"]) == 1
    assert job.result["matched"][0]["student_id"] == student["id"]
    assert job.result["unmatched_face_count"] == 0
    assert job.result["spoofed_face_count"] == 0

    records = (
        await client.get(f"/courses/{course['id']}/attendance/sessions/{session['id']}", headers=auth_headers)
    ).json()
    assert len(records) == 1
    assert records[0]["present"] is True


async def test_process_attendance_photo_no_faces_marks_job_failed(client, auth_headers):
    course = (await client.post("/courses", json={"name": "C", "code": "C1"}, headers=auth_headers)).json()
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    job = await _run_task(session["id"], course["id"], [])
    assert job.status == FAILED
    assert job.error == "No faces detected in image"


async def test_process_attendance_photo_unmatched_face_not_counted_present(client, auth_headers):
    course, _ = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    job = await _run_task(session["id"], course["id"], [STRANGER_FACE])
    assert job.status == DONE
    assert job.result["matched"] == []
    assert job.result["unmatched_face_count"] == 1
    assert job.result["spoofed_face_count"] == 0

    records = (
        await client.get(f"/courses/{course['id']}/attendance/sessions/{session['id']}", headers=auth_headers)
    ).json()
    assert records[0]["present"] is False


async def test_process_attendance_photo_same_face_twice_not_double_counted(client, auth_headers):
    course, student = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    job = await _run_task(session["id"], course["id"], [FAKE_LIVE_FACE, FAKE_LIVE_FACE])
    assert job.status == DONE
    assert len(job.result["matched"]) == 1


async def test_process_attendance_photo_spoofed_face_not_matched_or_unmatched(client, auth_headers):
    course, _ = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    job = await _run_task(session["id"], course["id"], [SPOOFED_FACE])
    assert job.status == DONE
    assert job.result["matched"] == []
    assert job.result["unmatched_face_count"] == 0
    assert job.result["spoofed_face_count"] == 1


async def test_process_attendance_photo_mixed_real_and_spoofed_faces(client, auth_headers):
    course, student = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    job = await _run_task(session["id"], course["id"], [FAKE_LIVE_FACE, SPOOFED_FACE])
    assert job.status == DONE
    assert len(job.result["matched"]) == 1
    assert job.result["matched"][0]["student_id"] == student["id"]
    assert job.result["spoofed_face_count"] == 1
