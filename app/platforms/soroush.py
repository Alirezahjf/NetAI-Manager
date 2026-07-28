"""Soroush Plus adapter powered by the user's own SoroPy library."""

from __future__ import annotations

import asyncio
from typing import Any, List, Optional

from loguru import logger

from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class SoroushPlatform(BasePlatform):
    """
    Wraps SoroPy (https://github.com/Alirezahjf/soropy).

    Preferred backend: websocket (MTProto-like, no Chrome).
    Falls back gracefully if SoroPy is not installed.
    """

    platform = PlatformType.SOROUSH

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)
        self._client = None
        self._backend = "websocket"

    async def connect(self, **credentials: Any) -> bool:
        """
        credentials:
          - phone (required) e.g. "09123456789"
          - backend: "websocket" | "selenium" (default websocket)
          - code_callback: optional callable for SMS code
          - headless: for selenium
        """
        phone = credentials.get("phone") or self.account_id
        self._backend = credentials.get("backend", "websocket")
        headless = credentials.get("headless", True)
        code_callback = credentials.get("code_callback")

        try:
            from soropy import SoroushClient
        except ImportError as exc:
            raise RuntimeError(
                'SoroPy is not installed. Run: pip install "soropy[ws]>=1.3.6"'
            ) from exc

        # SoroPy is mostly sync; run blocking parts in a thread
        def _login() -> Any:
            client = SoroushClient(phone, backend=self._backend, headless=headless)
            if code_callback:
                client.login(code_callback=code_callback)
            else:
                # Interactive fallback – better to supply code_callback in production
                client.login(code_callback=lambda: input("کد سروش: ").strip())
            return client

        try:
            self._client = await asyncio.to_thread(_login)
            self.is_connected = True
            self.account_id = phone
            self.display_name = self.display_name or phone

            # Wire realtime events if backend supports them
            if hasattr(self._client, "on"):

                def on_new_message(event: Any) -> None:
                    data = getattr(event, "data", event) or {}
                    if isinstance(data, dict):
                        msg = MessageInfo(
                            id=str(data.get("message_id", "")),
                            chat_id=str(data.get("chat_id", data.get("chat_name", ""))),
                            text=str(data.get("text", "")),
                            sender_id=str(data.get("sender_id")) if data.get("sender_id") else None,
                            sender_name=data.get("sender_name"),
                            is_outgoing=bool(data.get("is_outgoing", False)),
                            timestamp=str(data.get("timestamp")) if data.get("timestamp") else None,
                            reply_to_id=str(data.get("reply_to_id")) if data.get("reply_to_id") else None,
                            extra=data,
                        )
                        # schedule on running loop if possible
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(self._dispatch_message(msg))
                        except RuntimeError:
                            pass

                self._client.on("new_message", on_new_message)

            logger.info(f"Soroush connected: {phone} (backend={self._backend})")
            return True
        except Exception as exc:
            logger.error(f"Soroush login failed: {exc}")
            self.is_connected = False
            raise

    async def disconnect(self) -> None:
        if self._client is not None:
            try:
                await asyncio.to_thread(self._client.close)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"Soroush close error: {exc}")
            self._client = None
        self.is_connected = False

    async def get_me(self) -> dict:
        self._ensure()
        # SoroPy may expose get_me depending on version
        if hasattr(self._client, "get_me"):
            me = await asyncio.to_thread(self._client.get_me)
            return me if isinstance(me, dict) else {"raw": me}
        return {"phone": self.account_id, "platform": "soroush"}

    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
        self._ensure()

        def _fetch() -> List[ChatInfo]:
            result = self._client.get_chats()
            chats: List[ChatInfo] = []
            # SoroPy returns object with personal / groups / channels or similar
            buckets = []
            if hasattr(result, "personal"):
                buckets.append(("private", getattr(result, "personal", []) or []))
            if hasattr(result, "groups"):
                buckets.append(("group", getattr(result, "groups", []) or []))
            if hasattr(result, "channels"):
                buckets.append(("channel", getattr(result, "channels", []) or []))
            if not buckets and isinstance(result, (list, tuple)):
                buckets.append(("other", list(result)))

            for chat_type, items in buckets:
                for item in items[:limit]:
                    if isinstance(item, dict):
                        chats.append(
                            ChatInfo(
                                id=str(item.get("id") or item.get("chat_id") or item.get("name") or ""),
                                title=str(item.get("title") or item.get("name") or item.get("id") or ""),
                                chat_type=chat_type,
                                username=item.get("username"),
                                extra=item,
                            )
                        )
                    else:
                        name = str(item)
                        chats.append(ChatInfo(id=name, title=name, chat_type=chat_type))
            return chats[:limit]

        return await asyncio.to_thread(_fetch)

    async def get_messages(self, chat_id: str, limit: int = 50) -> List[MessageInfo]:
        self._ensure()
        # SoroPy history API may vary; return empty list as safe default until wired
        logger.warning("get_messages for Soroush is limited in this version – extend via SoroPy API")
        return []

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to: Optional[str] = None,
        **kwargs: Any,
    ) -> MessageInfo:
        self._ensure()

        def _send() -> Any:
            if reply_to and hasattr(self._client, "reply"):
                return self._client.reply(chat_id, message_id=int(reply_to), text=text)
            return self._client.send_message(chat_id, text)

        result = await asyncio.to_thread(_send)
        return MessageInfo(
            id=str(getattr(result, "id", "") or ""),
            chat_id=chat_id,
            text=text,
            is_outgoing=True,
            reply_to_id=reply_to,
            extra={"raw": str(result)},
        )

    async def send_media(
        self,
        chat_id: str,
        file_path: str,
        *,
        caption: str = "",
        **kwargs: Any,
    ) -> MessageInfo:
        self._ensure()
        if not hasattr(self._client, "send_file"):
            raise NotImplementedError("This SoroPy backend does not support send_file")

        def _send() -> Any:
            return self._client.send_file(chat_id, file_path, caption=caption)

        result = await asyncio.to_thread(_send)
        return MessageInfo(
            id=str(getattr(result, "id", "") or ""),
            chat_id=chat_id,
            text=caption or f"[file] {file_path}",
            is_outgoing=True,
            extra={"raw": str(result), "file": file_path},
        )

    def _ensure(self) -> None:
        if not self.is_connected or self._client is None:
            raise RuntimeError("Soroush client is not connected. Call connect() first.")
