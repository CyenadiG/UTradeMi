import hashlib
import time

from fastapi import APIRouter

from app.config import settings

router = APIRouter()


@router.get("/image-signature")
async def get_image_signature() -> dict:
    timestamp = int(time.time())

    if not (
        settings.CLOUDINARY_CLOUD_NAME
        and settings.CLOUDINARY_API_KEY
        and settings.CLOUDINARY_API_SECRET
    ):
        return {
            "cloud_name": "",
            "api_key": "",
            "timestamp": timestamp,
            "signature": "",
            "message": "Cloudinary env vars not configured",
        }

    raw = f"timestamp={timestamp}{settings.CLOUDINARY_API_SECRET}"
    signature = hashlib.sha1(raw.encode("utf-8")).hexdigest()

    return {
        "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
        "api_key": settings.CLOUDINARY_API_KEY,
        "timestamp": timestamp,
        "signature": signature,
    }