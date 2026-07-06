from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def get_db():
    async with async_session() as session:
        yield session


async def init_db():
    # Best-effort, in its own transaction: works for local/CI Postgres
    # (POSTGRES_USER is a superuser there). On the production VM the app's
    # DB role is intentionally not a superuser, so this fails with
    # InsufficientPrivilege even when the extension already exists (created
    # out-of-band via `sudo -u postgres psql`) -- expected, not fatal, and
    # kept in its own transaction so a failure here can't abort create_all.
    try:
        async with engine.begin() as conn:
            await conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    except sa.exc.DBAPIError:
        pass

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
