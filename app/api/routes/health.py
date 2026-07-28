from fastapi import APIRouter

from app import __version__
from app.config import get_settings
from app.core.account_manager import account_manager

router = APIRouter()


@router.get("/api/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": __version__,
        "connected_accounts": len(account_manager.list_accounts()),
    }
