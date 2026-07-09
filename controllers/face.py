import logging
from io import BytesIO

import cv2
import numpy as np
from sqlalchemy.orm import Session

from config import settings
from models.user import FaceEmbedding, User

logger = logging.getLogger(__name__)

FACE_RECOGNITION_ENABLED = False


def get_face_model():
    return None


def extract_embedding(image_bytes: bytes) -> np.ndarray | None:
    return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def find_matching_users(
    db: Session,
    embeddings: list[np.ndarray],
    threshold: float | None = None,
) -> list[dict]:
    return []


def detect_faces(image_bytes: bytes) -> list[dict]:
    return []


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
