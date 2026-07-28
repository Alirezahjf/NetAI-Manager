"""Bale (بله) platform adapter – skeleton ready for Balethon or official bot API."""

from __future__ import annotations

from typing import Any, List, Optional

from loguru import logger

from app.config import get_settings
from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class BalePlatform(BasePlatform):
    """
    Bale adapter.

    Recommended path:
    - Bot mode: official Bot API + token (similar to Telegram bots)
    - User mode: libraries such as Balethon (see ozv_grams project)

    This file provides a clean interface; flesh out the transport of your choice.
    """

    platform = PlatformType.BALE

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)
        self._token: Optional[str] = None
        self._base_url = "https://tapi.bale.ai"

    async def connect(self, **credentials: Any) -> bool:
        settings = get_settings()
        self._token = credentials.get("token") or settings.bale_bot_token
        if not self._token:
            raise RuntimeError("BALE_BOT_TOKEN is required for bot mode")

        # TODO: verify token with getMe
        self.is_connected = True
        self.display_name = self.display_name or f"bale:{self.account_id}"
        logger.info(f"Bale connected (bot mode skeleton): {self.display_name}")
        logger.warning(
            "Bale adapter is a professional skeleton. "
            "Complete HTTP calls or integrate Balethon from ozv_grams for full features."
        )
        return True

    async def disconnect(self) -> None:
        self.is_connected = False
        self._token = None

    async def get_me(self) -> dict:
        return {"platform": "bale", "account_id": self.account_id, "mode": "bot-skeleton"}

    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
        # Bot API does not list arbitrary user chats the same way; implement via updates storage
        return []

    async def get_messages(self, chat_id: str, limit: int = 50) -> List[MessageInfo]:
        return []

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to: Optional[str] = None,
        **kwargs: Any,
    ) -> MessageInfo:
        if not self.is_connected or not self._token:
            raise RuntimeError("Bale is not connected")

        # Placeholder – replace with real HTTP call to Bale Bot API
        # POST {base}/bot{token}/sendMessage
        logger.info(f"[Bale skeleton] would send to {chat_id}: {text[:80]}")
        return MessageInfo(
            id="pending",
            chat_id=chat_id,
            text=text,
            is_outgoing=True,
            reply_to_id=reply_to,
            extra={"status": "skeleton_only"},
        )
