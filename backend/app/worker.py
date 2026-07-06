from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings
from app.tasks.attendance_tasks import process_attendance_photo

_redis_pool = None


async def get_redis_pool():
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _redis_pool


class WorkerSettings:
    functions = [process_attendance_photo]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
