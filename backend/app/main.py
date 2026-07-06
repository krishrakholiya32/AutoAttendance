import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import attendance, auth, courses, students
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("app_startup")
    yield
    logger.info("app_shutdown")


app = FastAPI(title="AutoAttendance API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(students.router)
app.include_router(attendance.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# Serve React frontend — must come last (catch-all)
_FRONTEND = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.exists(_FRONTEND):
    app.mount("/assets", StaticFiles(directory=os.path.join(_FRONTEND, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        return FileResponse(os.path.join(_FRONTEND, "index.html"))
