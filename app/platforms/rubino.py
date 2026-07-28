"""Rubino (روبینو) adapter — uses Rubika auth (ozv_grams + rubinobot)."""

from __future__ import annotations

import asyncio
from typing import Any, List, Optional

from loguru import logger

from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class RubinoPlatform(BasePlatform):
    """
    Rubino has no separate phone auth.
    Pass credentials from a connected Rubika session:
      { "auth": "..." }  (required)
    """

    platform = PlatformType.RUBINO

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)
        self._auth: Optional[str] = None
        self._profile_id: Optional[str] = None

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
            raise RuntimeError(
                "Rubino نیاز به auth روبیکا دارد. اول روبیکا را وصل کنید و auth را پاس دهید."
            )
        self._auth = auth

        def _me() -> dict:
            from rubinobot import Client as RubinoClient

            client = RubinoClient(auth=auth, timeout=20)
            raw = self._run_async(client.get_me())
            return raw.get("data", {}).get("profile", {}) or {}

        try:
            profile = await asyncio.to_thread(_me)
            self._profile_id = profile.get("id")
            self.account_id = str(self._profile_id or self.account_id)
            self.display_name = profile.get("name") or profile.get("username") or self.account_id
            self.is_connected = True
            logger.info(f"Rubino connected: {self.display_name}")
            return True
        except Exception as exc:
            logger.error(f"Rubino connect failed: {exc}")
            raise

    async def disconnect(self) -> None:
        self.is_connected = False
        self._auth = None

    async def get_me(self) -> dict:
        self._ensure()

        def _me() -> dict:
            from rubinobot import Client as RubinoClient

            client = RubinoClient(auth=self._auth, timeout=20)
            raw = self._run_async(client.get_me())
            return raw.get("data", {}).get("profile", {}) or {}

        profile = await asyncio.to_thread(_me)
        return {
            "platform": "rubino",
            "id": profile.get("id"),
            "name": profile.get("name"),
            "username": profile.get("username"),
            "followers": profile.get("follower_count"),
            "posts": profile.get("post_count"),
        }

    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
        """Rubino is profile/social oriented — no classic chat list."""
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
        raise NotImplementedError(
            "Rubino messaging is limited; use follow/profile APIs or extend rubinobot."
        )

    async def follow(self, target: str) -> dict:
        """Follow a Rubino profile by username or profile_id (ozv_grams RubinoWorker)."""
        self._ensure()

        def _follow() -> dict:
            from rubinobot import Client as RubinoClient

            target_s = target.strip()
            if target_s.startswith("@"):
                target_s = target_s[1:]
            if "/" in target_s:
                target_s = target_s.rstrip("/").split("/")[-1]

            client = RubinoClient(auth=self._auth, timeout=20)

            # resolve username
            if len(target_s) <= 20:
                raw = self._run_async(client.is_exist_username(username=target_s))
                data = raw.get("data", {})
                if not data.get("exist", False):
                    return {"success": False, "error": f"@{target_s} پیدا نشد"}
                profile_id = data.get("profile", {}).get("id")
                name = data.get("profile", {}).get("name", target_s)
            else:
                profile_id = target_s
                name = target_s

            my_pid = self._profile_id
            if not my_pid:
                me = self._run_async(client.get_me())
                my_pid = me.get("data", {}).get("profile", {}).get("id")

            raw = self._run_async(client.follow(followee_id=profile_id, profile_id=my_pid))
            if raw.get("status") == "OK" or "ALREADY" in str(raw.get("status_det", "")).upper():
                return {"success": True, "title": name, "profile_id": profile_id}
            return {"success": False, "error": raw.get("status_det", "unknown")}

        return await asyncio.to_thread(_follow)

    def _ensure(self) -> None:
        if not self.is_connected or not self._auth:
            raise RuntimeError("Rubino is not connected")
