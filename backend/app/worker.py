from arq import create_pool
from arq.connections import RedisSettings
from prometheus_client import start_http_server

from app.core.config import settings
from app.core.tracing import configure_tracing
from app.tasks.attendance_tasks import process_attendance_photo

_redis_pool = None


async def get_redis_pool():
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _redis_pool


async def on_startup(ctx) -> None:
    # Deliberately not called at module level: app.worker is also imported by
    # the API process (for get_redis_pool), and configure_tracing() can only
    # set the process-global TracerProvider once -- calling it here instead
    # means it only ever runs inside the actual arq worker process.
    configure_tracing("autoattendance-arq-worker")
    # No FastAPI app in this process to hang an Instrumentator off of, so the
    # arq worker's own /metrics port is just a bare prometheus_client server.
    start_http_server(8002)


class WorkerSettings:
    functions = [process_attendance_photo]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = on_startup
