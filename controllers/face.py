import logging
from io import BytesIO

import cv2
import insightface
import numpy as np

logger = logging.getLogger(__name__)

_model = None


def get_face_model():
    global _model
    if _model is None:
        try:
            _model = insightface.app.FaceAnalysis(name="buffalo_l")
            _model.prepare(ctx_id=0)
            logger.info("InsightFace model loaded")
        except Exception as e:
            logger.error("Failed to load InsightFace model: %s", e)
            raise
    return _model


def extract_embedding(image_bytes: bytes) -> np.ndarray | None:
    model = get_face_model()
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        logger.warning("Failed to decode image")
        return None
    faces = model.get(img)
    if not faces:
        logger.warning("No face detected in image")
        return None
    emb = faces[0].embedding
    logger.info("Face embedding extracted (dim=%d)", len(emb))
    return emb


def resize_for_cache(image_bytes: bytes, max_dim: int = 256) -> bytes:
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return image_bytes
    h, w = img.shape[:2]
    if max(h, w) <= max_dim:
        return image_bytes
    scale = max_dim / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    small = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    _, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes()
