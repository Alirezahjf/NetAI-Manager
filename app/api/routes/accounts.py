from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.account_manager import account_manager
from app.platforms import (
    BalePlatform,
    EmailPlatform,
    RubikaPlatform,
    RubinoPlatform,
    SoroushPlatform,
    TelegramPlatform,
    YouTubePlatform,
)
from app.platforms.base import PlatformType

router = APIRouter()

PLATFORM_MAP = {
    PlatformType.TELEGRAM.value: TelegramPlatform,
    PlatformType.BALE.value: BalePlatform,
    PlatformType.RUBIKA.value: RubikaPlatform,
    PlatformType.RUBINO.value: RubinoPlatform,
    PlatformType.SOROUSH.value: SoroushPlatform,
    PlatformType.EMAIL.value: EmailPlatform,
    PlatformType.YOUTUBE.value: YouTubePlatform,
}


class ConnectRequest(BaseModel):
    platform: str = Field(..., description="telegram | bale | rubika | rubino | soroush | email | youtube")
    account_id: str = Field(..., description="Unique id for this account inside NetAI (phone, email, ...)")
    display_name: Optional[str] = None
    credentials: dict[str, Any] = Field(default_factory=dict)


@router.get("/")
async def list_accounts(platform: Optional[str] = None):
    return {"accounts": account_manager.list_accounts(platform)}


@router.post("/connect")
async def connect_account(body: ConnectRequest):
    platform = body.platform.lower().strip()
    if platform not in PLATFORM_MAP:
        raise HTTPException(400, f"Unsupported platform: {platform}")

    existing = account_manager.get(platform, body.account_id)
    if existing and existing.is_connected:
        return {"status": "already_connected", "account": account_manager.list_accounts(platform)}

    cls = PLATFORM_MAP[platform]
    client = cls(account_id=body.account_id, display_name=body.display_name or "")
    try:
        ok = await client.connect(**body.credentials)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, detail=str(exc)) from exc

    if not ok:
        raise HTTPException(400, "Connection failed")

    account_manager.register(client)
    return {
        "status": "connected",
        "platform": platform,
        "account_id": client.account_id,
        "display_name": client.display_name,
    }


@router.post("/{platform}/{account_id}/disconnect")
async def disconnect_account(platform: str, account_id: str):
    client = account_manager.get(platform, account_id)
    if not client:
        raise HTTPException(404, "Account not found")
    await client.disconnect()
    account_manager.unregister(platform, account_id)
    return {"status": "disconnected"}


@router.get("/{platform}/{account_id}/me")
async def account_me(platform: str, account_id: str):
    client = account_manager.get(platform, account_id)
    if not client:
        raise HTTPException(404, "Account not found")
    try:
        return await client.get_me()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, detail=str(exc)) from exc
