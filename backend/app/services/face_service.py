"""cosine_similarity is kept here only as the brute-force comparison
baseline for scripts/benchmark_vector_search.py -- actual face detection,
embedding, and liveness now live entirely in the face-worker microservice
(see face-worker/app.py), called via app.services.face_client. Real
matching against a course's gallery happens in app.services.matching via a
pgvector HNSW-indexed SQL query. Model choice and the matching approach
were validated in notebooks/face_accuracy_benchmark.ipynb (98.5-100% 1:N
accuracy on LFW at gallery sizes 10-300)."""

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
