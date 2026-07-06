from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "postgresql+asyncpg://autoattendance:autoattendance@postgres:5432/autoattendance"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    # Plain string, not list[str]: pydantic-settings JSON-decodes list-typed env
    # vars before any field_validator runs, so a comma-separated CORS_ORIGINS
    # value would 400 at startup on a list[str] field.
    cors_origins: str = "http://localhost:5173,http://localhost:80"
    # Cosine similarity floor for a face match to count, tuned against the
    # buffalo_s LFW benchmark (genuine pairs cluster well above this, impostors
    # well below) -- keeps an unenrolled visitor's face from being force-matched
    # onto the closest enrolled student.
    face_match_threshold: float = 0.32
    max_embeddings_per_student: int = 5
    face_worker_url: str = "http://face-worker:8001"
    redis_url: str = "redis://redis:6379/0"
    # Empty disables tracing entirely -- see app/core/tracing.py's docstring.
    otel_exporter_otlp_endpoint: str = ""
    # Empty falls back to main.py's relative-path default. See main.py's comment.
    frontend_dist_path: str = ""

    @field_validator("database_url", mode="before")
    @classmethod
    def fix_db_url(cls, v: str) -> str:
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        if v.startswith("postgresql://") and "+asyncpg" not in v:
            return "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
