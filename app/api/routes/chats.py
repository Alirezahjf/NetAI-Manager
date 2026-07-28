from fastapi import APIRouter, HTTPException, Query

from app.core.account_manager import account_manager

router = APIRouter()


@router.get("/{platform}/{account_id}")
async def list_chats(
    platform: str,
    account_id: str,
    limit: int = Query(50, ge=1, le=200),
):
    client = account_manager.get(platform, account_id)
    if not client:
        raise HTTPException(404, "Account not found. Connect it first via /api/accounts/connect")
    try:
        chats = await client.get_chats(limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, detail=str(exc)) from exc

    return {
        "platform": platform,
        "account_id": account_id,
        "count": len(chats),
        "chats": [
            {
                "id": c.id,
                "title": c.title,
                "type": c.chat_type,
                "username": c.username,
                "unread_count": c.unread_count,
            }
            for c in chats
        ],
    }
