"""Telegram adapter using Telethon (MTProto)."""

from __future__ import annotations

from typing import Any, List, Optional

from loguru import logger

from app.config import get_settings
from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class TelegramPlatform(BasePlatform):
    platform = PlatformType.TELEGRAM

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)
        self._client = None

    async def connect(self, **credentials: Any) -> bool:
        """
        credentials:
          - api_id, api_hash (or use env)
          - session_name
          - phone (optional interactive)
        """
        settings = get_settings()
        api_id = credentials.get("api_id") or settings.telegram_api_id
        api_hash = credentials.get("api_hash") or settings.telegram_api_hash
        session = credentials.get("session_name") or settings.telegram_session_name

        if not api_id or not api_hash:
            raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")

        try:
            from telethon import TelegramClient
            from telethon import events
        except ImportError as exc:
            raise RuntimeError("Install telethon: pip install telethon") from exc

        self._client = TelegramClient(session, int(api_id), api_hash)
        await self._client.connect()

        if not await self._client.is_user_authorized():
            phone = credentials.get("phone") or self.account_id
            await self._client.send_code_request(phone)
            code = credentials.get("code") or input("کد تلگرام: ").strip()
            await self._client.sign_in(phone, code)

        me = await self._client.get_me()
        self.account_id = str(me.id)
        self.display_name = me.username or me.first_name or self.account_id
        self.is_connected = True

        @self._client.on(events.NewMessage)
        async def handler(event):  # type: ignore[no-untyped-def]
            msg = MessageInfo(
                id=str(event.message.id),
                chat_id=str(event.chat_id),
                text=event.message.message or "",
                sender_id=str(event.sender_id) if event.sender_id else None,
                is_outgoing=bool(event.out),
                timestamp=event.message.date.isoformat() if event.message.date else None,
                reply_to_id=str(event.message.reply_to_msg_id) if event.message.reply_to_msg_id else None,
            )
            await self._dispatch_message(msg)

        logger.info(f"Telegram connected: {self.display_name}")
        return True

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None
        self.is_connected = False

    async def get_me(self) -> dict:
        self._ensure()
        me = await self._client.get_me()
        return {
            "id": me.id,
            "username": me.username,
            "first_name": me.first_name,
            "last_name": me.last_name,
            "phone": me.phone,
        }

    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
        self._ensure()
        dialogs = await self._client.get_dialogs(limit=limit)
        result: List[ChatInfo] = []
        for d in dialogs:
            entity = d.entity
            chat_type = "private"
            if getattr(entity, "megagroup", False) or getattr(entity, "gigagroup", False):
                chat_type = "group"
            elif getattr(entity, "broadcast", False):
                chat_type = "channel"
            elif getattr(entity, "title", None) and not getattr(entity, "first_name", None):
                chat_type = "group"

            result.append(
                ChatInfo(
                    id=str(d.id),
                    title=d.name or str(d.id),
                    chat_type=chat_type,
                    username=getattr(entity, "username", None),
                    unread_count=d.unread_count or 0,
                )
            )
        return result

    async def get_messages(self, chat_id: str, limit: int = 50) -> List[MessageInfo]:
        self._ensure()
        messages = await self._client.get_messages(int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id, limit=limit)
        out: List[MessageInfo] = []
        for m in messages:
            out.append(
                MessageInfo(
                    id=str(m.id),
                    chat_id=str(chat_id),
                    text=m.message or "",
                    sender_id=str(m.sender_id) if m.sender_id else None,
                    is_outgoing=bool(m.out),
                    timestamp=m.date.isoformat() if m.date else None,
                    reply_to_id=str(m.reply_to_msg_id) if m.reply_to_msg_id else None,
                )
            )
        return out

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to: Optional[str] = None,
        **kwargs: Any,
    ) -> MessageInfo:
        self._ensure()
        target = int(chat_id) if str(chat_id).lstrip("-").isdigit() else chat_id
        kwargs_send: dict[str, Any] = {}
        if reply_to:
            kwargs_send["reply_to"] = int(reply_to)
        msg = await self._client.send_message(target, text, **kwargs_send)
        return MessageInfo(
            id=str(msg.id),
            chat_id=str(chat_id),
            text=text,
            is_outgoing=True,
            reply_to_id=reply_to,
        )

    def _ensure(self) -> None:
        if not self.is_connected or self._client is None:
            raise RuntimeError("Telegram client is not connected")
