import os

import cv2
import numpy as np

from liveness import check_liveness

TEST_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "test_faces", "lena.jpg")


def _load_test_image() -> np.ndarray:
    with open(TEST_IMAGE_PATH, "rb") as f:
        arr = np.frombuffer(f.read(), dtype=np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _detect_bbox(img_bgr: np.ndarray):
    from app import get_face_app

    faces = get_face_app().get(img_bgr)
    assert len(faces) == 1
    return faces[0].bbox


def test_liveness_accepts_a_clean_real_photo():
    img_bgr = _load_test_image()
    bbox = _detect_bbox(img_bgr)

    result = check_liveness(img_bgr, bbox)
    assert result["is_real"] is True


def test_liveness_rejects_a_simulated_screen_replay():
    """Downscale+upscale (loses detail like a re-captured screen) plus a
    moire-like periodic pattern -- a synthetic stand-in for a real spoof
    photo, proving the pipeline is genuinely sensitive to image content
    rather than always returning "real"."""
    img_bgr = _load_test_image()
    bbox = _detect_bbox(img_bgr)

    h, w = img_bgr.shape[:2]
    degraded = cv2.resize(img_bgr, (w // 4, h // 4), interpolation=cv2.INTER_LINEAR)
    degraded = cv2.resize(degraded, (w, h), interpolation=cv2.INTER_LINEAR)
    yy, xx = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
    moire = (np.sin(xx / 2.0) * 15 + np.sin(yy / 2.0) * 15).astype(np.int16)
    degraded = np.clip(degraded.astype(np.int16) + moire[:, :, None], 0, 255).astype(np.uint8)

    clean_result = check_liveness(img_bgr, bbox)
    degraded_result = check_liveness(degraded, bbox)

    assert degraded_result["logit_diff"] < clean_result["logit_diff"]
    assert degraded_result["is_real"] is False
