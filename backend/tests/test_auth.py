import pytest

pytestmark = pytest.mark.asyncio


async def test_signup_and_login(client):
    resp = await client.post(
        "/auth/signup", json={"email": "prof@test.edu", "password": "pass1234", "name": "Prof Test"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]

    resp2 = await client.post("/auth/login", json={"email": "prof@test.edu", "password": "pass1234"})
    assert resp2.status_code == 200
    assert resp2.json()["access_token"]


async def test_signup_duplicate_email_fails(client):
    payload = {"email": "dup@test.edu", "password": "pass1234", "name": "Dup"}
    assert (await client.post("/auth/signup", json=payload)).status_code == 200
    assert (await client.post("/auth/signup", json=payload)).status_code == 400


async def test_login_wrong_password_fails(client):
    await client.post("/auth/signup", json={"email": "wp@test.edu", "password": "correct123", "name": "WP"})
    resp = await client.post("/auth/login", json={"email": "wp@test.edu", "password": "wrong123"})
    assert resp.status_code == 401


async def test_login_unknown_email_fails(client):
    resp = await client.post("/auth/login", json={"email": "nobody@test.edu", "password": "whatever1"})
    assert resp.status_code == 401


async def test_me_requires_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_with_token(client):
    signup = await client.post(
        "/auth/signup", json={"email": "me@test.edu", "password": "pass1234", "name": "Me"}
    )
    token = signup.json()["access_token"]
    resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@test.edu"
