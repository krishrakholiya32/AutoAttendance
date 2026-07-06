import os

from fastapi.testclient import TestClient

from app import app

TEST_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "test_faces", "lena.jpg")

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_analyze_detects_a_real_face():
    with open(TEST_IMAGE_PATH, "rb") as f:
        resp = client.post("/analyze", files={"file": ("lena.jpg", f, "image/jpeg")})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["faces"]) == 1
    face = body["faces"][0]
    assert len(face["embedding"]) == 512
    assert len(face["bbox"]) == 4
    assert face["is_live"] is True


def test_analyze_no_face_in_blank_image():
    import cv2
    import numpy as np

    blank = np.zeros((200, 200, 3), dtype="uint8")
    ok, buf = cv2.imencode(".jpg", blank)
    assert ok
    resp = client.post("/analyze", files={"file": ("blank.jpg", buf.tobytes(), "image/jpeg")})
    assert resp.status_code == 200
    assert resp.json()["faces"] == []
