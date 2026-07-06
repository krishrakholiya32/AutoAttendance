"""Wraps InsightFace (buffalo_s: detection + recognition only) for enrollment
and attendance matching. Model choice and the cosine-similarity matching
approach were validated in notebooks/face_accuracy_benchmark.ipynb (98.5-100%
1:N accuracy on LFW at gallery sizes 10-300). Actual matching against a
course's gallery now happens in app.services.matching via a pgvector
HNSW-indexed SQL query -- cosine_similarity below is kept only as the
brute-force comparison baseline for scripts/benchmark_vector_search.py.

Each detected face also gets a liveness check (app.services.liveness_service)
run in the same pass, since it needs the same decoded image + bbox -- this
mirrors how Phase 4's face-worker microservice will co-locate the two later."""

from dataclasses import dataclass

import numpy as np
import cv2
from insightface.app import FaceAnalysis

from app.services.liveness_service import check_liveness

_face_app: FaceAnalysis | None = None


@dataclass
class DetectedFace:
    embedding: np.ndarray
    is_live: bool
    liveness_score: float


def get_face_app() -> FaceAnalysis:
    global _face_app
    if _face_app is None:
        _face_app = FaceAnalysis(
            name="buffalo_s",
            providers=["CPUExecutionProvider"],
            allowed_modules=["detection", "recognition"],
        )
        _face_app.prepare(ctx_id=0, det_size=(320, 320))
    return _face_app


def _decode_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise ValueError("Could not decode image")
    return img_bgr


def extract_single_embedding(image_bytes: bytes) -> DetectedFace | None:
    """For enrollment captures: one guided, single-face photo per angle.
    Returns the largest detected face (with a liveness verdict), or None if
    no face was found at all."""
    img_bgr = _decode_image(image_bytes)
    faces = get_face_app().get(img_bgr)
    if not faces:
        return None
    faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
    face = faces[0]
    liveness = check_liveness(img_bgr, face.bbox)
    return DetectedFace(embedding=face.embedding, is_live=liveness["is_real"], liveness_score=liveness["logit_diff"])


def extract_all_embeddings(image_bytes: bytes) -> list[DetectedFace]:
    """For attendance-taking: one classroom photo with many faces at once."""
    img_bgr = _decode_image(image_bytes)
    faces = get_face_app().get(img_bgr)
    results = []
    for f in faces:
        liveness = check_liveness(img_bgr, f.bbox)
        results.append(DetectedFace(embedding=f.embedding, is_live=liveness["is_real"], liveness_score=liveness["logit_diff"]))
    return results


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
