from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.account_manager import account_manager

router = APIRouter()


class SendMessageRequest(BaseModel):
    platform: str
    account_id: str
    chat_id: str
    text: str = Field(..., min_length=1)
    reply_to: Optional[str] = None
    extra: dict = Field(default_factory=dict)


@router.get("/{platform}/{account_id}/{chat_id}")
async def get_messages(
    platform: str,
    account_id: str,
    chat_id: str,
    limit: int = Query(50, ge=1, le=200),
):
    client = account_manager.get(platform, account_id)
    if not client:
        raise HTTPException(404, "Account not found")
    try:
        messages = await client.get_messages(chat_id, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, detail=str(exc)) from exc

    return {
        "count": len(messages),
        "messages": [
            {
                "id": m.id,
                "chat_id": m.chat_id,
                "text": m.text,
                "sender_id": m.sender_id,
                "sender_name": m.sender_name,
                "is_outgoing": m.is_outgoing,
                "timestamp": m.timestamp,
                "reply_to_id": m.reply_to_id,
            }
            for m in messages
        ],
    }


@router.post("/send")
async def send_message(body: SendMessageRequest):
    client = account_manager.get(body.platform, body.account_id)
    if not client:
        raise HTTPException(404, "Account not found")
    try:
        msg = await client.send_message(
            body.chat_id,
            body.text,
            reply_to=body.reply_to,
            **body.extra,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, detail=str(exc)) from exc

    return {
        "status": "sent",
        "message": {
            "id": msg.id,
            "chat_id": msg.chat_id,
            "text": msg.text,
            "is_outgoing": msg.is_outgoing,
        },
    }
