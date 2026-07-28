"""Telegram & Bale management bots."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from loguru import logger
from pydantic import BaseModel

from app.core.account_manager import account_manager
from app.core.settings_store import load_settings

router = APIRouter()


class NotifyBody(BaseModel):
    text: str
    platform: str = ""
    chat_title: str = ""


async def _telegram_send(token: str, chat_id: str | int, text: str) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json={"chat_id": chat_id, "text": text})
        return resp.json()


async def _bale_send(token: str, chat_id: str | int, text: str) -> dict:
    url = f"https://tapi.bale.ai/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json={"chat_id": chat_id, "text": text})
        return resp.json()


@router.post("/notify")
async def notify_admins(body: NotifyBody):
    s = load_settings().get("bots", {})
    if not s.get("notify_on_new_message"):
        return {"ok": False, "reason": "notifications disabled"}

    text = body.text
    if body.platform or body.chat_title:
        text = f"[{body.platform}] {body.chat_title}\n{body.text}"

    results: list[dict[str, Any]] = []
    admin_ids = s.get("admin_chat_ids") or []

    tg = s.get("telegram_bot_token")
    if tg and admin_ids:
        for cid in admin_ids:
            try:
                results.append({"telegram": await _telegram_send(tg, cid, text)})
            except Exception as exp:
                logger.error(f"TG notify failed: {exp}")
                results.append({"telegram_error": str(exp)})

    bale = s.get("bale_bot_token")
    if bale and admin_ids:
        for cid in admin_ids:
            try:
                results.append({"bale": await _bale_send(bale, cid, text)})
            except Exception as exp:
                logger.error(f"Bale notify failed: {exp}")
                results.append({"bale_error": str(exp)})

    return {"ok": True, "results": results}


@router.get("/status")
async def bots_status():
    s = load_settings().get("bots", {})
    return {
        "telegram_configured": bool(s.get("telegram_bot_token")),
        "bale_configured": bool(s.get("bale_bot_token")),
        "admin_chat_ids": s.get("admin_chat_ids") or [],
        "notify_on_new_message": s.get("notify_on_new_message", True),
    }


def _status_text() -> str:
    lines = ["NetAI Manager — وضعیت"]
    for c in account_manager.all_clients():
        plat = c.platform.value if hasattr(c.platform, "value") else str(c.platform)
        st = "🟢" if c.is_connected else "🔴"
        lines.append(f"{st} {plat}:{c.account_id}")
    if len(lines) == 1:
        lines.append("اکانتی متصل نیست")
    return "\n".join(lines)


@router.post("/telegram/webhook")
async def telegram_webhook(update: dict[str, Any]):
    s = load_settings().get("bots", {})
    token = s.get("telegram_bot_token")
    if not token:
        raise HTTPException(400, "Telegram bot not configured")

    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    admins = [str(x) for x in (s.get("admin_chat_ids") or [])]

    if not chat_id:
        return {"ok": True}

    if admins and str(chat_id) not in admins:
        await _telegram_send(token, chat_id, "دسترسی ندارید.")
        return {"ok": True}

    if text.startswith("/start") or text.startswith("/status"):
        await _telegram_send(token, chat_id, _status_text())
    else:
        await _telegram_send(
            token,
            chat_id,
            "دستورات:\n/status — وضعیت اکانت‌ها\nمدیریت کامل از وب‌اپ NetAI",
        )
    return {"ok": True}


@router.post("/bale/webhook")
async def bale_webhook(update: dict[str, Any]):
    s = load_settings().get("bots", {})
    token = s.get("bale_bot_token")
    if not token:
        raise HTTPException(400, "Bale bot not configured")

    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    if not chat_id:
        return {"ok": True}

    if text.startswith("/status") or text.startswith("/start"):
        await _bale_send(token, chat_id, _status_text())
    return {"ok": True}
