"""Rubino — followers count only (expand later with user-provided methods)."""

from __future__ import annotations

import asyncio
from typing import Any, List, Optional

from loguru import logger

from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class RubinoPlatform(BasePlatform):
    """
    Minimal Rubino connection using Rubika auth string.
    Primary goal for now: report follower_count from get_me / profile.
    Full messaging methods can be plugged in later.
    """

    platform = PlatformType.RUBINO

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)
        self._auth: Optional[str] = None
        self._profile: dict[str, Any] = {}

    @staticmethod
    def _run_async(coro):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, coro).result()
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    async def connect(self, **credentials: Any) -> bool:
        auth = credentials.get("auth")
        if not auth:
            raise RuntimeError("Rubino نیاز به auth روبیکا دارد")
        self._auth = auth

        def _me() -> dict:
            from rubinobot import Client as RubinoClient

            client = RubinoClient(auth=auth, timeout=20)
            raw = self._run_async(client.get_me())
            return raw.get("data", {}).get("profile", {}) or {}

        try:
            self._profile = await asyncio.to_thread(_me)
            self.account_id = str(self._profile.get("id") or self.account_id)
            self.display_name = (
                self._profile.get("name")
                or self._profile.get("username")
                or self.account_id
            )
            self.is_connected = True
            logger.info(
                f"Rubino connected: {self.display_name} "
                f"(followers={self._profile.get('follower_count')})"
            )
            return True
        except Exception as exc:
            logger.error(f"Rubino connect failed: {exc}")
            raise

    async def disconnect(self) -> None:
        self.is_connected = False
        self._auth = None

    async def get_me(self) -> dict:
        self._ensure()
        return {
            "platform": "rubino",
            "id": self._profile.get("id"),
            "name": self._profile.get("name"),
            "username": self._profile.get("username"),
            "followers": self._profile.get("follower_count", 0),
            "followings": self._profile.get("following_count", 0),
            "posts": self._profile.get("post_count", 0),
        }

    async def get_followers_count(self) -> int:
        me = await self.get_me()
        return int(me.get("followers") or 0)

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
        raise NotImplementedError("Rubino messaging در آپدیت بعدی اضافه می‌شود")

    def _ensure(self) -> None:
        if not self.is_connected:
            raise RuntimeError("Rubino is not connected")
