"""Wraps InsightFace (buffalo_s: detection + recognition only) for enrollment
and attendance matching. Model choice and the cosine-similarity matching
approach were validated in notebooks/face_accuracy_benchmark.ipynb (98.5-100%
1:N accuracy on LFW at gallery sizes 10-300). Actual matching against a
course's gallery now happens in app.services.matching via a pgvector
HNSW-indexed SQL query -- cosine_similarity below is kept only as the
brute-force comparison baseline for scripts/benchmark_vector_search.py."""

import numpy as np
import cv2
from insightface.app import FaceAnalysis

_face_app: FaceAnalysis | None = None


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


def extract_single_embedding(image_bytes: bytes) -> np.ndarray | None:
    """For enrollment captures: one guided, single-face photo per angle.
    Returns the largest detected face's embedding, or None if no face found."""
    faces = get_face_app().get(_decode_image(image_bytes))
    if not faces:
        return None
    faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)
    return faces[0].embedding


def extract_all_embeddings(image_bytes: bytes) -> list[np.ndarray]:
    """For attendance-taking: one classroom photo with many faces at once."""
    faces = get_face_app().get(_decode_image(image_bytes))
    return [f.embedding for f in faces]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
