from unittest.mock import patch

import numpy as np
import pytest

pytestmark = pytest.mark.asyncio

FAKE_EMBEDDING = np.ones(512, dtype="float32")


async def test_add_and_list_students(client, auth_headers):
    course = (await client.post("/courses", json={"name": "C", "code": "C1"}, headers=auth_headers)).json()

    resp = await client.post(
        f"/courses/{course['id']}/students",
        json={"name": "Alice", "roll_number": "R1"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["angles_captured"] == 0

    resp2 = await client.get(f"/courses/{course['id']}/students", headers=auth_headers)
    assert len(resp2.json()) == 1


async def test_enroll_face_success(client, auth_headers):
    course = (await client.post("/courses", json={"name": "C", "code": "C1"}, headers=auth_headers)).json()
    student = (
        await client.post(
            f"/courses/{course['id']}/students",
            json={"name": "Alice", "roll_number": "R1"},
            headers=auth_headers,
        )
    ).json()

    with patch("app.api.students.extract_single_embedding", return_value=FAKE_EMBEDDING):
        resp = await client.post(
            f"/courses/{course['id']}/students/{student['id']}/enroll-face?angle_label=front",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
            headers=auth_headers,
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["angle_label"] == "front"
    assert body["angles_captured"] == 1
    assert body["required_angles"] == 5

    students = (await client.get(f"/courses/{course['id']}/students", headers=auth_headers)).json()
    assert students[0]["angles_captured"] == 1


async def test_enroll_face_no_face_detected(client, auth_headers):
    course = (await client.post("/courses", json={"name": "C", "code": "C1"}, headers=auth_headers)).json()
    student = (
        await client.post(
            f"/courses/{course['id']}/students",
            json={"name": "Bob", "roll_number": "R2"},
            headers=auth_headers,
        )
    ).json()

    with patch("app.api.students.extract_single_embedding", return_value=None):
        resp = await client.post(
            f"/courses/{course['id']}/students/{student['id']}/enroll-face?angle_label=front",
            files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
            headers=auth_headers,
        )
    assert resp.status_code == 422


async def test_reenroll_same_angle_overwrites_not_duplicates(client, auth_headers):
    course = (await client.post("/courses", json={"name": "C", "code": "C1"}, headers=auth_headers)).json()
    student = (
        await client.post(
            f"/courses/{course['id']}/students",
            json={"name": "Alice", "roll_number": "R1"},
            headers=auth_headers,
        )
    ).json()

    with patch("app.api.students.extract_single_embedding", return_value=FAKE_EMBEDDING):
        for _ in range(2):
            resp = await client.post(
                f"/courses/{course['id']}/students/{student['id']}/enroll-face?angle_label=front",
                files={"file": ("test.jpg", b"fake-image-bytes", "image/jpeg")},
                headers=auth_headers,
            )
    assert resp.json()["angles_captured"] == 1


async def test_delete_student(client, auth_headers):
    course = (await client.post("/courses", json={"name": "C", "code": "C1"}, headers=auth_headers)).json()
    student = (
        await client.post(
            f"/courses/{course['id']}/students",
            json={"name": "Alice", "roll_number": "R1"},
            headers=auth_headers,
        )
    ).json()

    resp = await client.delete(f"/courses/{course['id']}/students/{student['id']}", headers=auth_headers)
    assert resp.status_code == 204

    students = (await client.get(f"/courses/{course['id']}/students", headers=auth_headers)).json()
    assert students == []
