"""Email platform via IMAP (read) + SMTP (send)."""

from __future__ import annotations

import asyncio
import email
from email.header import decode_header
from email.mime.text import MIMEText
from email.utils import parsedate_to_datetime
from typing import Any, List, Optional

from loguru import logger

from app.config import get_settings
from app.platforms.base import BasePlatform, ChatInfo, MessageInfo, PlatformType


def _decode_mime_header(value: Optional[str]) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, charset in parts:
        if isinstance(text, bytes):
            out.append(text.decode(charset or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


class EmailPlatform(BasePlatform):
    platform = PlatformType.EMAIL

    def __init__(self, account_id: str, display_name: str = "") -> None:
        super().__init__(account_id, display_name)
        self._user: Optional[str] = None
        self._password: Optional[str] = None

    async def connect(self, **credentials: Any) -> bool:
        settings = get_settings()
        self._user = credentials.get("user") or settings.email_user or self.account_id
        self._password = credentials.get("password") or settings.email_password
        if not self._user or not self._password:
            raise RuntimeError("EMAIL_USER and EMAIL_PASSWORD are required")

        self.account_id = self._user
        self.display_name = self.display_name or self._user
        self.is_connected = True
        logger.info(f"Email account configured: {self._user}")
        return True

    async def disconnect(self) -> None:
        self.is_connected = False

    async def get_me(self) -> dict:
        return {"email": self.account_id, "platform": "email"}

    async def get_chats(self, limit: int = 50) -> List[ChatInfo]:
        # Treat folders as "chats"
        return [
            ChatInfo(id="INBOX", title="Inbox", chat_type="folder"),
            ChatInfo(id="Sent", title="Sent", chat_type="folder"),
        ]

    async def get_messages(self, chat_id: str, limit: int = 50) -> List[MessageInfo]:
        self._ensure()
        settings = get_settings()
        host = settings.imap_host
        port = settings.imap_port
        if not host:
            raise RuntimeError("IMAP_HOST is not configured")

        def _fetch() -> List[MessageInfo]:
            import imaplib

            messages: List[MessageInfo] = []
            with imaplib.IMAP4_SSL(host, port) as imap:
                imap.login(self._user, self._password)
                folder = chat_id or "INBOX"
                imap.select(folder)
                status, data = imap.search(None, "ALL")
                if status != "OK":
                    return messages
                ids = data[0].split()
                for num in ids[-limit:]:
                    st, msg_data = imap.fetch(num, "(RFC822)")
                    if st != "OK" or not msg_data or not msg_data[0]:
                        continue
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)
                    subject = _decode_mime_header(msg.get("Subject"))
                    from_ = _decode_mime_header(msg.get("From"))
                    date_hdr = msg.get("Date")
                    ts = None
                    if date_hdr:
                        try:
                            ts = parsedate_to_datetime(date_hdr).isoformat()
                        except Exception:  # noqa: BLE001
                            ts = date_hdr
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode(errors="replace")
                                    break
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode(errors="replace")

                    messages.append(
                        MessageInfo(
                            id=num.decode() if isinstance(num, bytes) else str(num),
                            chat_id=folder,
                            text=f"{subject}\n\n{body}".strip(),
                            sender_name=from_,
                            timestamp=ts,
                            extra={"subject": subject},
                        )
                    )
            return list(reversed(messages))

        return await asyncio.to_thread(_fetch)

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_to: Optional[str] = None,
        **kwargs: Any,
    ) -> MessageInfo:
        """chat_id is treated as recipient email address. subject via kwargs."""
        self._ensure()
        settings = get_settings()
        subject = kwargs.get("subject", "Message from NetAI Manager")
        to_addr = chat_id

        def _send() -> None:
            import smtplib

            msg = MIMEText(text, _charset="utf-8")
            msg["Subject"] = subject
            msg["From"] = self._user
            msg["To"] = to_addr

            if settings.smtp_use_tls:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
                    smtp.starttls()
                    smtp.login(self._user, self._password)
                    smtp.send_message(msg)
            else:
                with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp:
                    smtp.login(self._user, self._password)
                    smtp.send_message(msg)

        await asyncio.to_thread(_send)
        return MessageInfo(
            id="sent",
            chat_id=to_addr,
            text=text,
            is_outgoing=True,
            extra={"subject": subject},
        )

    def _ensure(self) -> None:
        if not self.is_connected:
            raise RuntimeError("Email is not connected")
