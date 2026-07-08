import logging
from io import BytesIO

import cv2
import insightface
import numpy as np
from sqlalchemy.orm import Session

from config import settings
from models.user import FaceEmbedding, User

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


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def find_matching_users(
    db: Session,
    embeddings: list[np.ndarray],
    threshold: float | None = None,
) -> list[dict]:
    if threshold is None:
        threshold = 1.0 - settings.recognition_threshold

    stored = db.query(FaceEmbedding).all()
    if not stored:
        return []

    user_ids = [se.user_id for se in stored]
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    stored_list = [(se.user_id, np.frombuffer(se.embedding, dtype=np.float32)) for se in stored]

    results = []
    for emb in embeddings:
        best_uid = None
        best_sim = 0.0
        for uid, stored_emb in stored_list:
            sim = cosine_similarity(emb, stored_emb)
            if sim > best_sim:
                best_sim = sim
                best_uid = uid
        if best_uid and best_sim >= threshold:
            user = users.get(best_uid)
            if user:
                results.append({"user": user, "similarity": best_sim})

    return results


def detect_faces(image_bytes: bytes) -> list[dict]:
    model = get_face_model()
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return []
    faces = model.get(img)
    return [
        {
            "embedding": f.embedding,
            "bbox": [int(round(f.bbox[0])), int(round(f.bbox[1])), int(round(f.bbox[2])), int(round(f.bbox[3]))],
        }
        for f in faces
    ]


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
