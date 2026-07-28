"""Rubika adapter — accurate pyrubi.Client API (AliGanji1/Pyrubi)."""

from __future__ import annotations

import asyncio
from typing import Any, List, Optional

from loguru import logger

from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class RubikaPlatform(BasePlatform):
    """
    Uses official high-level Client from pyrubi:

        from pyrubi import Client
        client = Client(auth=..., private=...)
        client.get_chats()
        client.get_messages(object_guid=...)
        client.send_text(object_guid=..., text=...)

    Docs/source: https://github.com/AliGanji1/Pyrubi
    """

    platform = PlatformType.RUBIKA

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)
        self._client: Any = None
        self._session: dict[str, Any] = {}
        self._phone: Optional[str] = None
        self._phone_code_hash: Optional[str] = None

    # ---------- client factory ----------

    def _build_client(self, auth: str, private_key: str):
        from pyrubi import Client

        return Client(auth=auth, private=private_key)

    def _tmp_methods(self):
        from pyrubi.methods import Methods as RubikaMethod

        return RubikaMethod(
            sessionData={},
            platform="web",
            apiVersion=6,
            proxy=None,
            timeOut=15,
            showProgressBar=False,
        )

    # ---------- auth ----------

    async def start_auth(self, phone_number: str) -> dict:
        phone = phone_number.replace("+", "").replace(" ", "")
        if phone.startswith("98"):
            phone = "0" + phone[2:]

        def _send() -> dict:
            tmp = self._tmp_methods()
            result = tmp.sendCode(phoneNumber=phone)
            pch = result.get("phone_code_hash")
            if not pch:
                if result.get("status") == "SendPassKey":
                    raise ValueError("این شماره رمز دوم دارد.")
                raise ValueError(f"خطا در ارسال کد: {result}")
            return {"phone_code_hash": pch, "phone_number": phone}

        data = await asyncio.to_thread(_send)
        self._phone_code_hash = data["phone_code_hash"]
        self._phone = data["phone_number"]
        return data

    async def verify_code(self, code: str, phone_code_hash: Optional[str] = None) -> dict:
        from pyrubi.crypto import Cryption

        phone = self._phone or self.account_id
        pch = phone_code_hash or self._phone_code_hash
        if not pch:
            raise RuntimeError("ابتدا start_auth را صدا بزنید")

        def _verify() -> dict:
            tmp = self._tmp_methods()
            sr = tmp.signIn(phoneNumber=phone, phoneCodeHash=pch, phoneCode=code)
            if sr.get("status") != "OK":
                raise ValueError("کد تایید اشتباه است")
            auth = Cryption.decryptRsaOaep(sr["private_key"], sr["auth"])
            user = sr.get("user", {})
            session = {
                "auth": auth,
                "private_key": sr["private_key"],
                "user": user,
                "user_id": user.get("user_guid", ""),
                "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                "username": user.get("username", ""),
            }
            try:
                client = self._build_client(session["auth"], session["private_key"])
                # register device best-effort
                if hasattr(client, "methods"):
                    client.methods.registerDevice(deviceModel="netai-manager")
            except Exception:
                pass
            return session

        self._session = await asyncio.to_thread(_verify)
        self._client = self._build_client(self._session["auth"], self._session["private_key"])
        self.account_id = self._session.get("user_id") or phone
        self.display_name = self._session.get("name") or self.account_id
        self.is_connected = True
        logger.info(f"Rubika connected: {self.display_name}")
        return {
            "auth": self._session["auth"],
            "private_key": self._session["private_key"],
            "user_id": self._session.get("user_id"),
            "name": self._session.get("name"),
            "username": self._session.get("username"),
        }

    async def connect(self, **credentials: Any) -> bool:
        if credentials.get("auth") and credentials.get("private_key"):
            self._session = {
                "auth": credentials["auth"],
                "private_key": credentials["private_key"],
                "user": credentials.get("user", {}),
                "user_id": credentials.get("user_id", self.account_id),
                "name": credentials.get("name", ""),
                "username": credentials.get("username", ""),
            }
            self._client = self._build_client(self._session["auth"], self._session["private_key"])
            self.account_id = str(self._session.get("user_id") or self.account_id)
            self.display_name = self._session.get("name") or self.account_id
            self.is_connected = True
            return True

        phone = credentials.get("phone") or self.account_id
        code = credentials.get("code")
        if code:
            if credentials.get("phone_code_hash"):
                self._phone_code_hash = credentials["phone_code_hash"]
            self._phone = phone
            await self.verify_code(code)
            return True

        await self.start_auth(phone)
        return False

    async def disconnect(self) -> None:
        self.is_connected = False
        self._client = None

    async def get_me(self) -> dict:
        return {
            "platform": "rubika",
            "user_id": self._session.get("user_id"),
            "name": self._session.get("name"),
            "username": self._session.get("username"),
            "has_auth": bool(self._session.get("auth")),
        }

    def export_auth_for_rubino(self) -> str:
        self._ensure()
        return self._session["auth"]

    # ---------- chats / messages (pyrubi Client) ----------

    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
        self._ensure()

        def _fetch() -> List[ChatInfo]:
            raw = self._client.get_chats(start_id=None)
            items = raw.get("chats", []) if isinstance(raw, dict) else []
            out: List[ChatInfo] = []
            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                guid = str(item.get("object_guid") or "")
                abs_obj = item.get("abs_object") or {}
                title = (
                    item.get("title")
                    or abs_obj.get("title")
                    or abs_obj.get("first_name")
                    or guid
                )
                last = item.get("last_message") or {}
                out.append(
                    ChatInfo(
                        id=guid,
                        title=str(title),
                        chat_type=str(item.get("type") or abs_obj.get("type") or "chat"),
                        unread_count=int(item.get("count_unseen") or item.get("unread_count") or 0),
                        last_message=str(last.get("text") or "") or None,
                        extra={"platform": "rubika", **item},
                    )
                )
            return out

        return await asyncio.to_thread(_fetch)

    async def get_messages(self, chat_id: str, limit: int = 50) -> List[MessageInfo]:
        self._ensure()

        def _fetch() -> List[MessageInfo]:
            raw = self._client.get_messages(
                object_guid=chat_id,
                max_message_id=None,
                filter_type=None,
                limit=limit,
            )
            items = raw.get("messages", []) if isinstance(raw, dict) else []
            out: List[MessageInfo] = []
            for m in items:
                if not isinstance(m, dict):
                    continue
                out.append(
                    MessageInfo(
                        id=str(m.get("message_id") or ""),
                        chat_id=str(chat_id),
                        text=str(m.get("text") or ""),
                        sender_id=str(m.get("author_object_guid") or "") or None,
                        sender_name=None,
                        timestamp=str(m.get("time") or m.get("created_time") or "") or None,
                        is_outgoing=bool(m.get("is_mine")),
                        reply_to_id=str(m.get("reply_to_message_id") or "") or None,
                        extra={"platform": "rubika", **m},
                    )
                )
            # pyrubi returns newest first often — reverse for UI chronological
            out.reverse()
            return out

        return await asyncio.to_thread(_fetch)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to: Optional[str] = None,
        **kwargs: Any,
    ) -> MessageInfo:
        self._ensure()

        def _send() -> dict:
            return self._client.send_text(
                object_guid=chat_id,
                text=text,
                message_id=reply_to,
            )

        result = await asyncio.to_thread(_send)
        mid = ""
        if isinstance(result, dict):
            msg = result.get("message") or result
            mid = str(msg.get("message_id") or result.get("message_id") or "")
        return MessageInfo(
            id=mid or "sent",
            chat_id=str(chat_id),
            text=text,
            is_outgoing=True,
            reply_to_id=reply_to,
            extra={"platform": "rubika", "raw": result},
        )

    async def join_chat(self, target: str) -> dict:
        self._ensure()

        def _join() -> dict:
            try:
                result = self._client.join_chat(guid_or_link=target)
                return {"success": True, "raw": result}
            except Exception as e:
                err = str(e)
                if "ALREADY" in err.upper():
                    return {"success": True, "note": "already member"}
                return {"success": False, "error": err}

        return await asyncio.to_thread(_join)

    def _ensure(self) -> None:
        if not self.is_connected or not self._client:
            raise RuntimeError("Rubika is not connected")
