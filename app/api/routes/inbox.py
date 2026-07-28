"""Unified multi-platform inbox API."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.account_manager import account_manager

router = APIRouter()

PLATFORM_META = {
    "telegram": {"name": "تلگرام", "color": "#229ED9", "icon": "telegram"},
    "bale": {"name": "بله", "color": "#00A884", "icon": "bale"},
    "rubika": {"name": "روبیکا", "color": "#6C2BD9", "icon": "rubika"},
    "rubino": {"name": "روبینو", "color": "#E1306C", "icon": "rubino"},
    "soroush": {"name": "سروش", "color": "#0088CC", "icon": "soroush"},
    "email": {"name": "ایمیل", "color": "#EA4335", "icon": "email"},
    "youtube": {"name": "یوتیوب", "color": "#FF0000", "icon": "youtube"},
}


def _plat_str(p) -> str:
    return p.value if hasattr(p, "value") else str(p).split(".")[-1].lower()


class SendBody(BaseModel):
    platform: str
    account_id: str
    chat_id: str
    text: str = Field(..., min_length=1)
    reply_to: Optional[str] = None


@router.get("/conversations")
async def list_conversations():
    conversations: list[dict[str, Any]] = []
    for client in account_manager.all_clients():
        if not client.is_connected:
            continue
        plat = _plat_str(client.platform)
        meta = PLATFORM_META.get(plat, {"name": plat, "color": "#888", "icon": plat})
        key = f"{plat}:{client.account_id}"
        try:
            chats = await client.get_chats(limit=40)
        except Exception as exp:
            conversations.append(
                {
                    "id": f"{key}:error",
                    "platform": plat,
                    "account_id": client.account_id,
                    "title": "خطا در دریافت چت‌ها",
                    "error": str(exp),
                    "meta": meta,
                }
            )
            continue
        for c in chats:
            conversations.append(
                {
                    "id": f"{key}:{c.id}",
                    "platform": plat,
                    "account_key": key,
                    "account_id": client.account_id,
                    "account_name": client.display_name,
                    "chat_id": c.id,
                    "title": c.title,
                    "chat_type": c.chat_type,
                    "unread": c.unread_count,
                    "last_message": c.last_message,
                    "meta": meta,
                }
            )
    conversations.sort(key=lambda x: (-(x.get("unread") or 0), x.get("title") or ""))
    return {"count": len(conversations), "conversations": conversations}


@router.get("/messages")
async def list_messages(platform: str, account_id: str, chat_id: str, limit: int = 50):
    p = account_manager.get(platform, account_id)
    if not p or not p.is_connected:
        raise HTTPException(404, "Account not connected")
    try:
        msgs = await p.get_messages(chat_id, limit=limit)
    except Exception as exp:
        raise HTTPException(400, detail=str(exp)) from exp
    meta = PLATFORM_META.get(platform, {"name": platform, "color": "#888", "icon": platform})
    return {
        "platform": platform,
        "chat_id": chat_id,
        "meta": meta,
        "messages": [
            {
                "id": m.id,
                "text": m.text,
                "sender_id": m.sender_id,
                "sender_name": m.sender_name,
                "timestamp": m.timestamp,
                "is_outgoing": m.is_outgoing,
                "reply_to": m.reply_to_id,
                "platform": platform,
            }
            for m in msgs
        ],
    }


@router.post("/send")
async def send_message(body: SendBody):
    p = account_manager.get(body.platform, body.account_id)
    if not p or not p.is_connected:
        raise HTTPException(404, "Account not connected")
    try:
        msg = await p.send_message(body.chat_id, body.text, reply_to=body.reply_to)
    except Exception as exp:
        raise HTTPException(400, detail=str(exp)) from exp
    return {
        "ok": True,
        "message": {
            "id": msg.id,
            "text": msg.text,
            "is_outgoing": True,
            "platform": body.platform,
        },
    }
