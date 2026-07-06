"""Thin async HTTP client for the face-worker microservice (Phase 4) --
replaces direct insightface calls that used to live in this package.
Face-worker does detection + embedding + liveness in one round trip per
image; this client just calls it and reshapes the response."""

from dataclasses import dataclass

import httpx
import numpy as np

from app.core.config import settings


@dataclass
class DetectedFace:
    embedding: np.ndarray
    is_live: bool
    liveness_score: float


async def _analyze(image_bytes: bytes) -> list[DetectedFace]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.face_worker_url}/analyze",
            files={"file": ("image.jpg", image_bytes, "image/jpeg")},
        )
        resp.raise_for_status()
    data = resp.json()
    return [
        DetectedFace(
            embedding=np.array(f["embedding"], dtype="float32"),
            is_live=f["is_live"],
            liveness_score=f["liveness_score"],
        )
        for f in data["faces"]
    ]


async def extract_single_embedding(image_bytes: bytes) -> DetectedFace | None:
    """For enrollment captures: one guided, single-face photo per angle.
    face-worker returns faces largest-first, so the first result is the one
    we want; returns None if no face was found at all."""
    faces = await _analyze(image_bytes)
    return faces[0] if faces else None


async def extract_all_embeddings(image_bytes: bytes) -> list[DetectedFace]:
    """For attendance-taking: one classroom photo with many faces at once."""
    return await _analyze(image_bytes)
