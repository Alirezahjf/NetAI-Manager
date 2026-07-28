"""Bale (بله) adapter — based on ozv_grams BaleWorker + balethon patterns."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any, List, Optional

from loguru import logger

from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class BalePlatform(BasePlatform):
    """
    Bale user-mode auth (phone + SMS code) and session (JWT),
    following the same flow as ozv_grams/platforms/bale.

    Full chat/send capabilities expand when balethon Client is available
    with a stored JWT. Join/search helpers mirror ozv_grams workers.
    """

    platform = PlatformType.BALE

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)
        self._session: dict[str, Any] = {}
        self._auth_pending: dict[str, Any] = {}

    # ----- auth (2-step like ozv_grams) -----

    async def start_auth(self, phone_number: str) -> dict:
        """Send SMS code. Returns transaction_hash for verify step."""
        try:
            from balethon.proto import request_pb2, response_pb2  # type: ignore
            from balethon.network.http2connection import HTTP2Connection  # type: ignore
        except ImportError:
            # Fallback: instruct to use vendored balethon from ozv_grams
            raise RuntimeError(
                "balethon (از ozv_grams) نصب نیست. "
                "پوشه balethon را از ریپوی ozv_grams کنار پروژه قرار دهید یا PYTHONPATH را تنظیم کنید."
            )

        phone = phone_number.replace("+", "").replace(" ", "")
        if phone.startswith("0"):
            phone = "98" + phone[1:]

        device_hash = str(uuid.uuid4())
        start_phone = request_pb2.StartPhoneAuth(
            phone_number=int(phone),
            app_id=4,
            api_key="C28D46DC4C3A7A26564BFCC48B929086A95C93C98E789A19847BEE8627DE4E7D",
            device_hash=device_hash,
            device_title="Chrome_137.0.0.0, Windows",
            send_code_type=1,
        )

        conn = HTTP2Connection()
        response = await conn.request(
            "POST",
            service="bale.auth.v1.Auth/StartPhoneAuth",
            content=start_phone.SerializeToString(),
        )
        result = response_pb2.StartPhoneAuth()
        result.ParseFromString(response)

        self._auth_pending = {
            "transaction_hash": result.transaction_hash,
            "is_registered": result.is_registered,
            "phone_number": phone,
            "device_hash": device_hash,
        }
        return dict(self._auth_pending)

    async def verify_code(self, code: str, auth_data: Optional[dict] = None) -> dict:
        try:
            from balethon.proto import request_pb2, response_pb2, struct_pb2  # type: ignore
            from balethon.network.http2connection import HTTP2Connection  # type: ignore
        except ImportError as exc:
            raise RuntimeError("balethon required for Bale auth") from exp

        data = auth_data or self._auth_pending
        if not data.get("transaction_hash"):
            raise RuntimeError("Call start_auth first")

        validate = request_pb2.ValidateCode(
            transaction_hash=data["transaction_hash"],
            code=code,
            is_jwt=struct_pb2.BoolValue(value=True),
        )
        conn = HTTP2Connection()
        response = await conn.request(
            "POST",
            service="bale.auth.v1.Auth/ValidateCode",
            content=validate.SerializeToString(),
        )
        result = response_pb2.Auth()
        result.ParseFromString(response)

        self._session = {
            "user_id": result.user.id,
            "jwt": result.jwt.value,
            "name": result.user.name,
            "phone": data.get("phone_number"),
        }
        self.account_id = str(result.user.id)
        self.display_name = result.user.name or self.account_id
        self.is_connected = True
        logger.info(f"Bale connected: {self.display_name}")
        return dict(self._session)

    async def connect(self, **credentials: Any) -> bool:
        """
        credentials options:
          - jwt + user_id (+ name)  → resume session
          - phone + code            → full login (start_auth + verify if needed)
          - phone only              → start_auth only (is_connected stays False until verify)
        """
        if credentials.get("jwt") and credentials.get("user_id"):
            self._session = {
                "jwt": credentials["jwt"],
                "user_id": credentials["user_id"],
                "name": credentials.get("name", ""),
                "phone": credentials.get("phone"),
            }
            self.account_id = str(credentials["user_id"])
            self.display_name = credentials.get("name") or self.account_id
            self.is_connected = True
            return True

        phone = credentials.get("phone") or self.account_id
        code = credentials.get("code")

        if code:
            if not self._auth_pending and credentials.get("transaction_hash"):
                self._auth_pending = {
                    "transaction_hash": credentials["transaction_hash"],
                    "phone_number": phone,
                }
            await self.verify_code(code)
            return True

        # Only start auth
        await self.start_auth(phone)
        logger.info("Bale SMS code sent — call connect again with code=...")
        return False

    async def disconnect(self) -> None:
        self.is_connected = False
        self._session = {}

    async def get_me(self) -> dict:
        return {
            "platform": "bale",
            "user_id": self._session.get("user_id"),
            "name": self._session.get("name"),
            "phone": self._session.get("phone"),
            "has_jwt": bool(self._session.get("jwt")),
        }

    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
        """Requires balethon Client with full dialogs API — extend as needed."""
        self._ensure()
        logger.warning("Bale get_chats: use balethon Client dialogs when available")
        return []

    async def get_messages(self, chat_id: str, limit: int = 50) -> List[MessageInfo]:
        self._ensure()
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
        # Prefer balethon Client if importable
        try:
            from balethon import Client  # type: ignore

            # Userbot mode needs phone file session; with JWT we use WS path via Client if supported
            client = Client(str(self._session.get("phone") or self.account_id))
            # If session dict already has jwt, inject
            if self._session.get("jwt"):
                client.session = {
                    "id": self._session["user_id"],
                    "jwt": self._session["jwt"],
                }
                from balethon.network.wsconnection import WSConnection  # type: ignore

                client.ws_connection = WSConnection(self._session["jwt"], None)

            await client.connect()
            try:
                msg = await client.send_message(chat_id, text)
                mid = str(getattr(msg, "id", "") or "")
            finally:
                await client.disconnect()

            return MessageInfo(
                id=mid,
                chat_id=str(chat_id),
                text=text,
                is_outgoing=True,
                reply_to_id=reply_to,
            )
        except Exception as exc:
            logger.error(f"Bale send_message failed: {exc}")
            raise RuntimeError(f"Bale send failed: {exc}") from exp

    async def join_target(self, target_link: str) -> dict:
        """Join group/channel — same logic as ozv_grams BaleWorker.join."""
        self._ensure()
        # Re-use simplified import of worker pattern via dynamic call
        raise NotImplementedError(
            "برای join از worker بله در ozv_grams استفاده کنید یا متد join را با JWT کامل کنید."
        )

    def _ensure(self) -> None:
        if not self.is_connected or not self._session.get("jwt"):
            raise RuntimeError("Bale is not connected (need JWT session)")
