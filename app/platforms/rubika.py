"""Rubika (روبیکا) adapter — based on ozv_grams + pyrubi."""

from __future__ import annotations

import asyncio
from typing import Any, List, Optional

from loguru import logger

from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


class RubikaPlatform(BasePlatform):
    """
    Auth + session via pyrubi (same as ozv_grams/platforms/rubika/worker.py).
    Session fields: auth, private_key, user, user_id, name, username

    Rubino reuses the same `auth` string.
    """

    platform = PlatformType.RUBIKA

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)
        self._session: dict[str, Any] = {}
        self._phone_code_hash: Optional[str] = None
        self._phone: Optional[str] = None

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

    def _methods(self):
        from pyrubi.methods import Methods as RubikaMethod

        return RubikaMethod(
            sessionData=self._session,
            platform="web",
            apiVersion=6,
            proxy=None,
            timeOut=15,
            showProgressBar=False,
        )

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
                    raise ValueError("این شماره رمز دوم دارد و فعلاً پشتیبانی نمی‌شود.")
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
            raise RuntimeError("Call start_auth first")

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
                methods = RubikaMethod = None  # noqa
                from pyrubi.methods import Methods as RM

                RM(
                    sessionData=session,
                    platform="web",
                    apiVersion=6,
                    proxy=None,
                    timeOut=10,
                    showProgressBar=False,
                ).registerDevice(deviceModel="netai-manager")
            except Exception:
                pass
            return session

        self._session = await asyncio.to_thread(_verify)
        self.account_id = self._session.get("user_id") or phone
        self.display_name = self._session.get("name") or self.account_id
        self.is_connected = True
        logger.info(f"Rubika connected: {self.display_name}")
        return dict(self._session)

    async def connect(self, **credentials: Any) -> bool:
        # Resume with existing session
        if credentials.get("auth") and credentials.get("private_key"):
            self._session = {
                "auth": credentials["auth"],
                "private_key": credentials["private_key"],
                "user": credentials.get("user", {}),
                "user_id": credentials.get("user_id", self.account_id),
                "name": credentials.get("name", ""),
                "username": credentials.get("username", ""),
            }
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
        logger.info("Rubika SMS code sent — connect again with code=...")
        return False

    async def disconnect(self) -> None:
        self.is_connected = False

    async def get_me(self) -> dict:
        return {
            "platform": "rubika",
            "user_id": self._session.get("user_id"),
            "name": self._session.get("name"),
            "username": self._session.get("username"),
            # auth is sensitive — only expose presence
            "has_auth": bool(self._session.get("auth")),
        }

    def export_session_for_rubino(self) -> dict:
        """Rubino shares Rubika auth."""
        self._ensure()
        return {
            "auth": self._session["auth"],
            "private_key": self._session.get("private_key"),
            "user_id": self._session.get("user_id"),
            "name": self._session.get("name"),
        }

    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
        self._ensure()

        def _fetch() -> List[ChatInfo]:
            methods = self._methods()
            chats: List[ChatInfo] = []
            # pyrubi may expose getChats / get_chats depending on version
            for attr in ("getChats", "get_chats", "getDialogs"):
                if hasattr(methods, attr):
                    try:
                        raw = getattr(methods, attr)()
                        items = raw if isinstance(raw, list) else raw.get("chats", raw.get("data", []))
                        for item in (items or [])[:limit]:
                            if not isinstance(item, dict):
                                continue
                            guid = item.get("object_guid") or item.get("guid") or item.get("chat_id") or ""
                            title = (
                                item.get("title")
                                or item.get("channel_title")
                                or item.get("group_title")
                                or str(guid)
                            )
                            chats.append(
                                ChatInfo(
                                    id=str(guid),
                                    title=str(title),
                                    chat_type=str(item.get("type", "other")),
                                    extra=item,
                                )
                            )
                        break
                    except Exception as exc:
                        logger.warning(f"Rubika {attr} failed: {exc}")
            return chats

        return await asyncio.to_thread(_fetch)

    async def get_messages(self, chat_id: str, limit: int = 50) -> List[MessageInfo]:
        self._ensure()

        def _fetch() -> List[MessageInfo]:
            methods = self._methods()
            out: List[MessageInfo] = []
            for attr in ("getMessages", "get_messages", "getChatMessages"):
                if hasattr(methods, attr):
                    try:
                        raw = getattr(methods, attr)(chat_id)
                        items = raw if isinstance(raw, list) else raw.get("messages", [])
                        for m in (items or [])[:limit]:
                            if not isinstance(m, dict):
                                continue
                            out.append(
                                MessageInfo(
                                    id=str(m.get("message_id") or m.get("id") or ""),
                                    chat_id=str(chat_id),
                                    text=str(m.get("text") or m.get("message") or ""),
                                    sender_id=str(m.get("author_object_guid") or "") or None,
                                    is_outgoing=bool(m.get("is_mine") or m.get("out")),
                                    extra=m,
                                )
                            )
                        break
                    except Exception as exc:
                        logger.warning(f"Rubika {attr} failed: {exc}")
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

        def _send() -> Any:
            methods = self._methods()
            for attr in ("sendMessage", "send_message"):
                if hasattr(methods, attr):
                    fn = getattr(methods, attr)
                    try:
                        return fn(chat_id, text)
                    except TypeError:
                        return fn(object_guid=chat_id, text=text)
            raise RuntimeError("pyrubi has no sendMessage method in this version")

        result = await asyncio.to_thread(_send)
        mid = ""
        if isinstance(result, dict):
            mid = str(result.get("message_id") or result.get("id") or "")
        return MessageInfo(
            id=mid or "sent",
            chat_id=str(chat_id),
            text=text,
            is_outgoing=True,
            reply_to_id=reply_to,
            extra={"raw": result} if not isinstance(result, dict) else result,
        )

    async def join_chat(self, target: str) -> dict:
        """Join group/channel by link or username — ozv_grams logic."""
        self._ensure()

        def _join() -> dict:
            methods = self._methods()
            target_s = target.strip()
            try:
                if "joing" in target_s or "joinc" in target_s:
                    result = methods.joinChat(guidOrLink=target_s)
                    return {"success": True, "raw": result}
                clean = target_s[1:] if target_s.startswith("@") else target_s
                if "rubika.ir/" in clean and "join" not in clean:
                    clean = clean.rstrip("/").split("/")[-1]
                try:
                    info = methods.getChatInfoByUsername(username=clean)
                    guid = None
                    if "channel" in info:
                        guid = info["channel"]["channel_guid"]
                        title = info["channel"].get("channel_title", "")
                    elif "group" in info:
                        guid = info["group"]["group_guid"]
                        title = info["group"].get("group_title", "")
                    else:
                        return {"success": False, "error": "پیدا نشد یا کاربر است"}
                    result = methods.joinChat(guidOrLink=guid)
                    return {"success": True, "title": title, "raw": result}
                except Exception:
                    result = methods.joinChat(guidOrLink=target_s)
                    return {"success": True, "raw": result}
            except Exception as e:
                err = str(e)
                if "ALREADY" in err.upper():
                    return {"success": True, "note": "already member"}
                return {"success": False, "error": err}

        return await asyncio.to_thread(_join)

    def _ensure(self) -> None:
        if not self.is_connected or not self._session.get("auth"):
            raise RuntimeError("Rubika is not connected")
