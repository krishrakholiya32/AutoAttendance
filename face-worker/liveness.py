"""Passive face-liveness (anti-spoofing) detection -- rejects a printed photo
or screen replay held up to the camera instead of a real face.

Model: MiniFASNetV2-SE, quantized ONNX (~600KB), from
https://github.com/facenox/face-antispoof-onnx (Apache 2.0), ~98% accuracy
on 70k+ real/spoof samples. The crop/preprocess/decision logic below is
ported directly from that repo's src/inference/ (not pulled in as a pip
dependency since we only need inference, not its training pipeline).

Duplicated (not imported) from backend/app/services/liveness_service.py --
this service is deliberately self-contained with no dependency on the
backend package, matching the stateless-microservice split (Phase 4).
"""

import os

import cv2
import numpy as np
import onnxruntime as ort

MODEL_PATH = os.path.join(os.path.dirname(__file__), "assets", "liveness_model.onnx")
MODEL_IMG_SIZE = 128
BBOX_EXPANSION_FACTOR = 1.5  # matches upstream demo.py's default

_session: ort.InferenceSession | None = None
_input_name: str | None = None


def _get_session() -> tuple[ort.InferenceSession, str]:
    global _session, _input_name
    if _session is None:
        _session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
        _input_name = _session.get_inputs()[0].name
    return _session, _input_name


def _crop(img: np.ndarray, bbox: tuple[float, float, float, float], expansion_factor: float) -> np.ndarray:
    """Extract a square face crop from bbox=(x1,y1,x2,y2) with expansion,
    reflection-padding at image edges."""
    original_height, original_width = img.shape[:2]
    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1
    if w <= 0 or h <= 0:
        raise ValueError("Invalid bbox dimensions")

    max_dim = max(w, h)
    center_x = x1 + w / 2
    center_y = y1 + h / 2

    x = int(center_x - max_dim * expansion_factor / 2)
    y = int(center_y - max_dim * expansion_factor / 2)
    crop_size = int(max_dim * expansion_factor)

    crop_x1 = max(0, x)
    crop_y1 = max(0, y)
    crop_x2 = min(original_width, x + crop_size)
    crop_y2 = min(original_height, y + crop_size)

    top_pad = int(max(0, -y))
    left_pad = int(max(0, -x))
    bottom_pad = int(max(0, (y + crop_size) - original_height))
    right_pad = int(max(0, (x + crop_size) - original_width))

    if crop_x2 > crop_x1 and crop_y2 > crop_y1:
        face = img[crop_y1:crop_y2, crop_x1:crop_x2, :]
    else:
        face = np.zeros((0, 0, 3), dtype=img.dtype)

    result = cv2.copyMakeBorder(face, top_pad, bottom_pad, left_pad, right_pad, cv2.BORDER_REFLECT_101)
    if result.shape[0] != crop_size or result.shape[1] != crop_size:
        raise ValueError(f"Crop size mismatch: expected {crop_size}x{crop_size}, got {result.shape[0]}x{result.shape[1]}")
    return result


def _preprocess(img: np.ndarray, model_img_size: int) -> np.ndarray:
    """Resize with letterboxing, normalize to [0,1], convert to CHW."""
    old_size = img.shape[:2]
    ratio = float(model_img_size) / max(old_size)
    scaled_shape = tuple(int(x * ratio) for x in old_size)

    interpolation = cv2.INTER_LANCZOS4 if ratio > 1.0 else cv2.INTER_AREA
    img = cv2.resize(img, (scaled_shape[1], scaled_shape[0]), interpolation=interpolation)

    delta_w = model_img_size - scaled_shape[1]
    delta_h = model_img_size - scaled_shape[0]
    top, bottom = delta_h // 2, delta_h - (delta_h // 2)
    left, right = delta_w // 2, delta_w - (delta_w // 2)
    img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_REFLECT_101)

    return img.transpose(2, 0, 1).astype(np.float32) / 255.0


def check_liveness(image_bgr: np.ndarray, bbox: np.ndarray, threshold: float = 0.5) -> dict:
    """bbox: (x1, y1, x2, y2) as returned by insightface's Face.bbox.
    threshold: probability in (0, 1); default 0.5 matches the model's own
    training decision boundary (real_logit >= spoof_logit)."""
    session, input_name = _get_session()

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    face_crop = _crop(image_rgb, tuple(float(v) for v in bbox), BBOX_EXPANSION_FACTOR)
    model_input = _preprocess(face_crop, MODEL_IMG_SIZE)[np.newaxis, ...]

    logits = session.run([], {input_name: model_input})[0][0]
    real_logit, spoof_logit = float(logits[0]), float(logits[1])

    p = max(1e-6, min(1 - 1e-6, threshold))
    logit_threshold = np.log(p / (1 - p))
    logit_diff = real_logit - spoof_logit
    is_real = logit_diff >= logit_threshold

    return {
        "is_real": bool(is_real),
        "logit_diff": logit_diff,
        "real_logit": real_logit,
        "spoof_logit": spoof_logit,
    }
