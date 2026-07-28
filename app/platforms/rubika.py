"""Rubika (روبیکا) platform adapter – professional skeleton."""

from __future__ import annotations

from typing import Any, List, Optional

from loguru import logger

from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class RubikaPlatform(BasePlatform):
    """
    Rubika does not publish a stable public user API for third-party clients.
    This adapter defines the contract so you can plug in:
      - official bot/API if available for your use-case
      - reverse-engineered client (high risk, ToS-sensitive)
      - browser automation (Selenium/Playwright) as last resort

    Keep credentials and session files out of git.
    """

    platform = PlatformType.RUBIKA

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)

    async def connect(self, **credentials: Any) -> bool:
        logger.warning(
            "Rubika adapter is a skeleton. Implement auth carefully and respect Rubika ToS."
        )
        self.is_connected = True
        self.display_name = self.display_name or f"rubika:{self.account_id}"
        return True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def get_me(self) -> dict:
        return {"platform": "rubika", "account_id": self.account_id, "status": "skeleton"}

    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
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
        if not self.is_connected:
            raise RuntimeError("Rubika is not connected")
        logger.info(f"[Rubika skeleton] would send to {chat_id}: {text[:80]}")
        return MessageInfo(
            id="pending",
            chat_id=chat_id,
            text=text,
            is_outgoing=True,
            reply_to_id=reply_to,
            extra={"status": "skeleton_only"},
        )
