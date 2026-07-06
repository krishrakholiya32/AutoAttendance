from unittest.mock import patch

import numpy as np
import pytest

from app.services.face_client import DetectedFace

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


async def test_mark_attendance_matches_enrolled_student(client, auth_headers):
    course, student = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    with patch("app.api.attendance.extract_all_embeddings", return_value=[FAKE_LIVE_FACE]):
        resp = await client.post(
            f"/courses/{course['id']}/attendance/sessions/{session['id']}/mark",
            files={"file": ("photo.jpg", b"x", "image/jpeg")},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["matched"]) == 1
    assert body["matched"][0]["student_id"] == student["id"]
    assert body["unmatched_face_count"] == 0
    assert body["spoofed_face_count"] == 0

    records = (
        await client.get(f"/courses/{course['id']}/attendance/sessions/{session['id']}", headers=auth_headers)
    ).json()
    assert len(records) == 1
    assert records[0]["present"] is True


async def test_mark_attendance_no_faces_detected(client, auth_headers):
    course = (await client.post("/courses", json={"name": "C", "code": "C1"}, headers=auth_headers)).json()
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    with patch("app.api.attendance.extract_all_embeddings", return_value=[]):
        resp = await client.post(
            f"/courses/{course['id']}/attendance/sessions/{session['id']}/mark",
            files={"file": ("photo.jpg", b"x", "image/jpeg")},
            headers=auth_headers,
        )
    assert resp.status_code == 422


async def test_mark_attendance_unmatched_face_not_counted_present(client, auth_headers):
    course, _ = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    with patch("app.api.attendance.extract_all_embeddings", return_value=[STRANGER_FACE]):
        resp = await client.post(
            f"/courses/{course['id']}/attendance/sessions/{session['id']}/mark",
            files={"file": ("photo.jpg", b"x", "image/jpeg")},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched"] == []
    assert body["unmatched_face_count"] == 1
    assert body["spoofed_face_count"] == 0

    records = (
        await client.get(f"/courses/{course['id']}/attendance/sessions/{session['id']}", headers=auth_headers)
    ).json()
    assert records[0]["present"] is False


async def test_mark_attendance_same_face_twice_not_double_counted(client, auth_headers):
    course, student = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    with patch(
        "app.api.attendance.extract_all_embeddings",
        return_value=[FAKE_LIVE_FACE, FAKE_LIVE_FACE],
    ):
        resp = await client.post(
            f"/courses/{course['id']}/attendance/sessions/{session['id']}/mark",
            files={"file": ("photo.jpg", b"x", "image/jpeg")},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    assert len(resp.json()["matched"]) == 1


async def test_mark_attendance_spoofed_face_not_matched_or_counted_unmatched(client, auth_headers):
    course, _ = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    with patch("app.api.attendance.extract_all_embeddings", return_value=[SPOOFED_FACE]):
        resp = await client.post(
            f"/courses/{course['id']}/attendance/sessions/{session['id']}/mark",
            files={"file": ("photo.jpg", b"x", "image/jpeg")},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["matched"] == []
    assert body["unmatched_face_count"] == 0
    assert body["spoofed_face_count"] == 1


async def test_mark_attendance_mixed_real_and_spoofed_faces(client, auth_headers):
    course, student = await _make_course_with_enrolled_student(client, auth_headers)
    session = (
        await client.post(f"/courses/{course['id']}/attendance/sessions", json={}, headers=auth_headers)
    ).json()

    with patch(
        "app.api.attendance.extract_all_embeddings",
        return_value=[FAKE_LIVE_FACE, SPOOFED_FACE],
    ):
        resp = await client.post(
            f"/courses/{course['id']}/attendance/sessions/{session['id']}/mark",
            files={"file": ("photo.jpg", b"x", "image/jpeg")},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["matched"]) == 1
    assert body["matched"][0]["student_id"] == student["id"]
    assert body["spoofed_face_count"] == 1
