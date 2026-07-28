"""YouTube adapter focused on comments and channel management via Data API."""

from __future__ import annotations

from typing import Any, List, Optional

from loguru import logger

from app.config import get_settings
from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class YouTubePlatform(BasePlatform):
    """
    Maps YouTube concepts onto the chat/message model:
      - chats  ≈ videos / comment threads you manage
      - messages ≈ comments

    Requires YOUTUBE_API_KEY (read) and OAuth client secrets for write actions.
    """

    platform = PlatformType.YOUTUBE

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)
        self._youtube = None

    async def connect(self, **credentials: Any) -> bool:
        settings = get_settings()
        api_key = credentials.get("api_key") or settings.youtube_api_key
        if not api_key:
            raise RuntimeError("YOUTUBE_API_KEY is required")

        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise RuntimeError(
                "Install google-api-python-client: pip install google-api-python-client"
            ) from exc

        self._youtube = build("youtube", "v3", developerKey=api_key)
        self.is_connected = True
        self.display_name = self.display_name or f"youtube:{self.account_id}"
        logger.info("YouTube Data API client ready (API key mode)")
        return True

    async def disconnect(self) -> None:
        self._youtube = None
        self.is_connected = False

    async def get_me(self) -> dict:
        return {"platform": "youtube", "account_id": self.account_id, "mode": "api_key"}

    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
        """List recent videos for a channel if channel id provided as account_id."""
        self._ensure()
        # Without OAuth, channel listing is limited. Return empty or search-based later.
        logger.info("YouTube get_chats: provide channel/video workflow as needed")
        return []

    async def get_messages(self, chat_id: str, limit: int = 50) -> List[MessageInfo]:
        """chat_id = videoId → fetch comment threads."""
        self._ensure()
        request = self._youtube.commentThreads().list(
            part="snippet",
            videoId=chat_id,
            maxResults=min(limit, 100),
            textFormat="plainText",
        )
        response = request.execute()
        messages: List[MessageInfo] = []
        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]["snippet"]
            messages.append(
                MessageInfo(
                    id=item["id"],
                    chat_id=chat_id,
                    text=top.get("textDisplay") or top.get("textOriginal") or "",
                    sender_name=top.get("authorDisplayName"),
                    timestamp=top.get("publishedAt"),
                    extra={"like_count": top.get("likeCount"), "author_channel": top.get("authorChannelId")},
                )
            )
        return messages

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to: Optional[str] = None,
        **kwargs: Any,
    ) -> MessageInfo:
        """Posting comments requires OAuth – not available with API key alone."""
        raise NotImplementedError(
            "Posting YouTube comments requires OAuth user credentials. "
            "Extend this adapter with google-auth-oauthlib flow."
        )

    def _ensure(self) -> None:
        if not self.is_connected or self._youtube is None:
            raise RuntimeError("YouTube is not connected")
