import pytest

pytestmark = pytest.mark.asyncio


async def test_create_and_list_courses(client, auth_headers):
    resp = await client.post("/courses", json={"name": "Intro to CS", "code": "CS101"}, headers=auth_headers)
    assert resp.status_code == 200
    course = resp.json()
    assert course["student_count"] == 0

    resp2 = await client.get("/courses", headers=auth_headers)
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
    assert resp2.json()[0]["code"] == "CS101"


async def test_get_and_delete_course(client, auth_headers):
    course = (
        await client.post("/courses", json={"name": "C", "code": "C1"}, headers=auth_headers)
    ).json()

    resp = await client.get(f"/courses/{course['id']}", headers=auth_headers)
    assert resp.status_code == 200

    resp2 = await client.delete(f"/courses/{course['id']}", headers=auth_headers)
    assert resp2.status_code == 204

    resp3 = await client.get(f"/courses/{course['id']}", headers=auth_headers)
    assert resp3.status_code == 404


async def test_course_isolation_between_professors(client, auth_headers):
    course = (
        await client.post("/courses", json={"name": "CS101", "code": "CS101"}, headers=auth_headers)
    ).json()

    signup2 = await client.post(
        "/auth/signup", json={"email": "prof2@test.edu", "password": "pass1234", "name": "Prof2"}
    )
    headers2 = {"Authorization": f"Bearer {signup2.json()['access_token']}"}

    resp = await client.get(f"/courses/{course['id']}", headers=headers2)
    assert resp.status_code == 404

    resp2 = await client.get("/courses", headers=headers2)
    assert resp2.json() == []


async def test_courses_require_auth(client):
    resp = await client.get("/courses")
    assert resp.status_code == 401
