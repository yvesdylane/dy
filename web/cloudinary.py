import re
from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader
import cloudinary.utils

from config import settings

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
)


def upload_to_cloudinary(file_data: bytes, public_id: str = None, folder: str = "dy") -> str:
    result = cloudinary.uploader.upload(file_data, folder=folder, public_id=public_id)
    return sign_url(result["secure_url"])


def sign_url(url: str) -> str:
    if not url or "cloudinary" not in url:
        return url
    parsed = urlparse(url)
    if "/s--" in parsed.path:
        return url
    m = re.search(r"/v\d+/(.+)", parsed.path)
    if not m:
        return url
    public_id = m.group(1)
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"):
        if public_id.endswith(ext):
            public_id = public_id[: -len(ext)]
            break
    signed, _ = cloudinary.utils.cloudinary_url(
        public_id, sign_url=True, secure=True, resource_type="image"
    )
    return signed
