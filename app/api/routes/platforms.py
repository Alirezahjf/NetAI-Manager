from fastapi import APIRouter

from app.platforms.base import PlatformType

router = APIRouter()


@router.get("/")
async def list_supported_platforms():
    """List all platform types this system is designed to support."""
    return {
        "platforms": [
            {
                "id": p.value,
                "name": p.name.title(),
                "status": "ready" if p in (PlatformType.TELEGRAM, PlatformType.SOROUSH, PlatformType.EMAIL, PlatformType.YOUTUBE) else "skeleton",
            }
            for p in PlatformType
        ]
    }
