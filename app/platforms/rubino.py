"""Rubino (روبینو) platform adapter – professional skeleton."""

from __future__ import annotations

from typing import Any, List, Optional

from loguru import logger

from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class RubinoPlatform(BasePlatform):
    """
    Rubino is closely related to the Rubika ecosystem.
    Treat this adapter the same way: define the interface first,
    implement transport only with authorized methods.
    """

    platform = PlatformType.RUBINO

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)

    async def connect(self, **credentials: Any) -> bool:
        logger.warning("Rubino adapter is a skeleton. Implement with care and legal compliance.")
        self.is_connected = True
        self.display_name = self.display_name or f"rubino:{self.account_id}"
        return True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def get_me(self) -> dict:
        return {"platform": "rubino", "account_id": self.account_id, "status": "skeleton"}

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
            raise RuntimeError("Rubino is not connected")
        logger.info(f"[Rubino skeleton] would send to {chat_id}: {text[:80]}")
        return MessageInfo(
            id="pending",
            chat_id=chat_id,
            text=text,
            is_outgoing=True,
            reply_to_id=reply_to,
            extra={"status": "skeleton_only"},
        )
