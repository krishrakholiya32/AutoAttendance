"""Stateless face analysis microservice: detection + embedding (insightface
buffalo_s) + liveness (MiniFASNetV2-SE), co-located in one /analyze endpoint
so a request only transfers/decodes the image once and liveness+embedding
are evaluated on the exact same frame (avoiding a TOCTOU gap between the
two checks). No DB access, no state -- horizontally scalable independent
of the main API, mirroring CompreFace's API-server/embedding-server split.
"""

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile
from insightface.app import FaceAnalysis
from pydantic import BaseModel

from liveness import check_liveness

app = FastAPI(title="AutoAttendance Face Worker")

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


class FaceResult(BaseModel):
    bbox: list[float]
    embedding: list[float]
    is_live: bool
    liveness_score: float


class AnalyzeResponse(BaseModel):
    faces: list[FaceResult]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(file: UploadFile = File(...)):
    """Returns every detected face in the image, largest-first, each with
    its embedding and liveness verdict. Callers decide how to use the list:
    enrollment takes the first (largest) face, attendance-marking uses all."""
    image_bytes = await file.read()
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return AnalyzeResponse(faces=[])

    faces = get_face_app().get(img_bgr)
    faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)

    results = []
    for f in faces:
        liveness = check_liveness(img_bgr, f.bbox)
        results.append(FaceResult(
            bbox=[float(v) for v in f.bbox],
            embedding=f.embedding.tolist(),
            is_live=liveness["is_real"],
            liveness_score=liveness["logit_diff"],
        ))
    return AnalyzeResponse(faces=results)
