from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.settings_store import load_settings, save_settings
from app.core.woocommerce import WooCommerceClient

router = APIRouter()


class SettingsPatch(BaseModel):
    data: dict[str, Any]


@router.get("/")
async def get_settings():
    s = load_settings()
    # mask secrets partially
    if s.get("ai", {}).get("api_key"):
        k = s["ai"]["api_key"]
        s["ai"]["api_key_masked"] = (k[:4] + "…" + k[-4:]) if len(k) > 8 else "****"
    if s.get("bots", {}).get("telegram_bot_token"):
        t = s["bots"]["telegram_bot_token"]
        s["bots"]["telegram_bot_token_masked"] = t[:8] + "…" if len(t) > 8 else "****"
    if s.get("bots", {}).get("bale_bot_token"):
        t = s["bots"]["bale_bot_token"]
        s["bots"]["bale_bot_token_masked"] = t[:8] + "…" if len(t) > 8 else "****"
    return s


@router.put("/")
async def update_settings(body: SettingsPatch):
    return save_settings(body.data)


@router.post("/woocommerce/test")
async def test_woo():
    client = WooCommerceClient()
    return await client.test_connection()
