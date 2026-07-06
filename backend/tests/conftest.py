import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://autoattendance:autoattendance@localhost:5432/autoattendance_test",
)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app.models  # noqa: F401 -- registers all models on Base.metadata
from app.core.database import Base, engine, get_db, async_session
from app.main import app as fastapi_app


async def _override_get_db():
    async with async_session() as session:
        yield session


fastapi_app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture(autouse=True)
async def _reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client):
    resp = await client.post(
        "/auth/signup",
        json={"email": "fixture-prof@test.edu", "password": "pass1234", "name": "Fixture Prof"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
