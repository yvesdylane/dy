import cloudinary
import cloudinary.uploader

from config import settings

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
)


def upload_to_cloudinary(file_data: bytes, public_id: str = None, folder: str = "dy") -> str:
    result = cloudinary.uploader.upload(file_data, folder=folder, public_id=public_id)
    return result["secure_url"]
