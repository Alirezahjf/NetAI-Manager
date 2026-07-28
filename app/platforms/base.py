"""Abstract base class that every platform adapter must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, List, Optional


class PlatformType(str, Enum):
    TELEGRAM = "telegram"
    BALE = "bale"
    RUBIKA = "rubika"
    RUBINO = "rubino"
    SOROUSH = "soroush"
    EMAIL = "email"
    YOUTUBE = "youtube"


@dataclass
class ChatInfo:
    id: str
    title: str
    chat_type: str = "private"  # private | group | channel | other
    username: Optional[str] = None
    unread_count: int = 0
    extra: dict = field(default_factory=dict)


@dataclass
class MessageInfo:
    id: str
    chat_id: str
    text: str
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    is_outgoing: bool = False
    timestamp: Optional[str] = None
    reply_to_id: Optional[str] = None
    extra: dict = field(default_factory=dict)


MessageHandler = Callable[[MessageInfo], Awaitable[None] | None]


class BasePlatform(ABC):
    """Common interface for all messaging / social platforms."""

    platform: PlatformType

    def __init__(self, account_id: str, display_name: str = "") -> None:
        self.account_id = account_id
        self.display_name = display_name or account_id
        self.is_connected: bool = False
        self._message_handlers: List[MessageHandler] = []

    # ---------- lifecycle ----------

    @abstractmethod
    async def connect(self, **credentials: Any) -> bool:
        """Authenticate and open the connection. Return True on success."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close sessions and release resources."""

    # ---------- identity ----------

    @abstractmethod
    async def get_me(self) -> dict:
        """Return basic info about the logged-in account."""

    # ---------- chats & messages ----------

    @abstractmethod
    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
        ...

    @abstractmethod
    async def get_messages(self, chat_id: str, limit: int = 50) -> List[MessageInfo]:
        ...

    @abstractmethod
    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to: Optional[str] = None,
        **kwargs: Any,
    ) -> MessageInfo:
        ...

    async def send_media(
        self,
        chat_id: str,
        file_path: str,
        *,
        caption: str = "",
        **kwargs: Any,
    ) -> MessageInfo:
        """Optional – override in platforms that support media."""
        raise NotImplementedError(f"{self.platform} does not support send_media yet")

    # ---------- events ----------

    def on_message(self, handler: MessageHandler) -> None:
        self._message_handlers.append(handler)

    async def _dispatch_message(self, message: MessageInfo) -> None:
        for handler in self._message_handlers:
            try:
                result = handler(message)
                if hasattr(result, "__await__"):
                    await result  # type: ignore[misc]
            except Exception as exc:  # noqa: BLE001
                print(f"[{self.platform}] message handler error: {exc}")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} account={self.account_id} connected={self.is_connected}>"
