from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.account_manager import account_manager
from app.core.user_profile import (
    clear_pending,
    load_profile,
    set_pending,
    set_phone,
)
from app.platforms import (
    BalePlatform,
    EmailPlatform,
    RubikaPlatform,
    RubinoPlatform,
    SoroushPlatform,
    TelegramPlatform,
    YouTubePlatform,
)
from app.platforms.base import PlatformType

router = APIRouter()

PLATFORM_MAP = {
    PlatformType.TELEGRAM.value: TelegramPlatform,
    PlatformType.BALE.value: BalePlatform,
    PlatformType.RUBIKA.value: RubikaPlatform,
    PlatformType.RUBINO.value: RubinoPlatform,
    PlatformType.SOROUSH.value: SoroushPlatform,
    PlatformType.EMAIL.value: EmailPlatform,
    PlatformType.YOUTUBE.value: YouTubePlatform,
}

PHONE_PLATFORMS = {"telegram", "bale", "rubika", "soroush"}


class PhoneBody(BaseModel):
    phone: str = Field(..., min_length=8, description="مثلاً 09123456789")


class SendCodeBody(BaseModel):
    platform: str
    phone: Optional[str] = None
    # optional extras e.g. api_id/api_hash for telegram
    credentials: dict[str, Any] = Field(default_factory=dict)


class VerifyCodeBody(BaseModel):
    platform: str
    code: str = Field(..., min_length=3)
    phone: Optional[str] = None
    phone_code_hash: Optional[str] = None
    transaction_hash: Optional[str] = None
    credentials: dict[str, Any] = Field(default_factory=dict)


class ConnectRequest(BaseModel):
    platform: str
    account_id: str
    display_name: Optional[str] = None
    credentials: dict[str, Any] = Field(default_factory=dict)


def _plat(p: str) -> str:
    return p.lower().strip()


@router.get("/phone")
async def get_phone():
    p = load_profile()
    return {"phone": p.get("phone") or ""}


@router.put("/phone")
async def save_phone(body: PhoneBody):
    return set_phone(body.phone)


@router.get("/status")
async def platforms_status():
    """Status of each platform for the Adam-style connect menu."""
    profile = load_profile()
    phone = profile.get("phone") or ""
    accounts = account_manager.list_accounts()
    by_plat: dict[str, list] = {}
    for a in accounts:
        by_plat.setdefault(a["platform"], []).append(a)

    items = []
    for key, label, color in [
        ("telegram", "تلگرام", "#229ED9"),
        ("bale", "بله", "#00A884"),
        ("rubika", "روبیکا", "#6C2BD9"),
        ("rubino", "روبینو", "#E1306C"),
        ("soroush", "سروش", "#0088CC"),
        ("email", "ایمیل", "#EA4335"),
        ("youtube", "یوتیوب", "#FF0000"),
    ]:
        accs = by_plat.get(key, [])
        connected = any(a.get("is_connected") for a in accs)
        items.append(
            {
                "platform": key,
                "name": label,
                "color": color,
                "connected": connected,
                "accounts": accs,
                "needs_phone": key in PHONE_PLATFORMS,
                "auth_style": "phone_code" if key in PHONE_PLATFORMS else "credentials",
            }
        )
    return {"phone": phone, "platforms": items}


@router.post("/send-code")
async def send_code(body: SendCodeBody):
    """Step 1: send verification code for a messenger."""
    platform = _plat(body.platform)
    if platform not in PLATFORM_MAP:
        raise HTTPException(400, f"Unsupported platform: {platform}")
    if platform not in PHONE_PLATFORMS:
        raise HTTPException(400, f"{platform} از کد پیامکی استفاده نمی‌کند")

    profile = load_profile()
    phone = (body.phone or profile.get("phone") or "").strip()
    if not phone:
        raise HTTPException(400, "ابتدا شماره موبایل را ذخیره کنید")

    existing = account_manager.get(platform, phone)
    if existing and existing.is_connected:
        return {"status": "already_connected", "platform": platform, "phone": phone}

    cls = PLATFORM_MAP[platform]
    client = cls(account_id=phone, display_name="")

    try:
        # Prefer explicit start_auth if available
        if hasattr(client, "start_auth"):
            data = await client.start_auth(phone)
        else:
            # connect with only phone should trigger code send and return False
            ok = await client.connect(phone=phone, **body.credentials)
            if ok:
                account_manager.register(client)
                clear_pending(platform)
                return {
                    "status": "connected",
                    "platform": platform,
                    "phone": phone,
                    "account_id": client.account_id,
                }
            data = {
                "phone_code_hash": getattr(client, "_phone_code_hash", None),
                "transaction_hash": getattr(client, "_transaction_hash", None),
            }
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, detail=str(exc)) from exp

    pending = {
        "phone": phone,
        "phone_code_hash": data.get("phone_code_hash") if isinstance(data, dict) else None,
        "transaction_hash": data.get("transaction_hash") if isinstance(data, dict) else None,
        "raw": data if isinstance(data, dict) else {},
        **body.credentials,
    }
    # keep temporary client reference on pending for platforms that need it
    set_pending(platform, pending)
    # stash client under a soft key so verify can reuse same instance if needed
    account_manager.register(client)  # not yet fully connected; is_connected may be False

    return {
        "status": "code_sent",
        "platform": platform,
        "phone": phone,
        "phone_code_hash": pending.get("phone_code_hash"),
        "transaction_hash": pending.get("transaction_hash"),
        "message": "کد تأیید ارسال شد. از SMS یا داخل همان پیام‌رسان چک کنید.",
    }


@router.post("/verify-code")
async def verify_code(body: VerifyCodeBody):
    """Step 2: enter code → account connected."""
    platform = _plat(body.platform)
    if platform not in PLATFORM_MAP:
        raise HTTPException(400, f"Unsupported platform: {platform}")

    profile = load_profile()
    pending = (profile.get("pending") or {}).get(platform) or {}
    phone = (body.phone or pending.get("phone") or profile.get("phone") or "").strip()
    if not phone:
        raise HTTPException(400, "شماره موبایل مشخص نیست")

    phone_code_hash = body.phone_code_hash or pending.get("phone_code_hash")
    transaction_hash = body.transaction_hash or pending.get("transaction_hash")

    client = account_manager.get(platform, phone)
    if not client:
        cls = PLATFORM_MAP[platform]
        client = cls(account_id=phone, display_name="")

    creds = {
        "phone": phone,
        "code": body.code,
        "phone_code_hash": phone_code_hash,
        "transaction_hash": transaction_hash,
        **(pending if isinstance(pending, dict) else {}),
        **body.credentials,
    }

    try:
        if hasattr(client, "verify_code"):
            await client.verify_code(
                body.code,
                phone_code_hash=phone_code_hash,
                transaction_hash=transaction_hash,
            )
            ok = client.is_connected
        else:
            ok = await client.connect(**creds)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, detail=str(exc)) from exp

    if not ok and not client.is_connected:
        raise HTTPException(400, "کد تأیید نامعتبر است یا اتصال برقرار نشد")

    account_manager.register(client)
    clear_pending(platform)
    return {
        "status": "connected",
        "platform": platform,
        "account_id": client.account_id,
        "display_name": client.display_name,
        "phone": phone,
    }


@router.get("/")
async def list_accounts(platform: Optional[str] = None):
    return {"accounts": account_manager.list_accounts(platform)}


@router.post("/connect")
async def connect_account(body: ConnectRequest):
    platform = _plat(body.platform)
    if platform not in PLATFORM_MAP:
        raise HTTPException(400, f"Unsupported platform: {platform}")

    existing = account_manager.get(platform, body.account_id)
    if existing and existing.is_connected:
        return {"status": "already_connected", "accounts": account_manager.list_accounts(platform)}

    cls = PLATFORM_MAP[platform]
    client = cls(account_id=body.account_id, display_name=body.display_name or "")
    try:
        ok = await client.connect(**body.credentials)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, detail=str(exc)) from exp

    # phone-only → code was sent
    if not ok:
        pending = {
            "phone": body.credentials.get("phone") or body.account_id,
            "phone_code_hash": getattr(client, "_phone_code_hash", None),
            "transaction_hash": getattr(client, "_transaction_hash", None),
            **body.credentials,
        }
        set_pending(platform, pending)
        account_manager.register(client)
        return {
            "status": "code_sent",
            "platform": platform,
            "account_id": body.account_id,
            "phone_code_hash": pending.get("phone_code_hash"),
            "transaction_hash": pending.get("transaction_hash"),
            "message": "کد تأیید ارسال شد",
        }

    account_manager.register(client)
    clear_pending(platform)
    return {
        "status": "connected",
        "platform": platform,
        "account_id": client.account_id,
        "display_name": client.display_name,
    }


@router.post("/{platform}/{account_id}/disconnect")
async def disconnect_account(platform: str, account_id: str):
    client = account_manager.get(platform, account_id)
    if not client:
        raise HTTPException(404, "Account not found")
    await client.disconnect()
    account_manager.unregister(platform, account_id)
    return {"status": "disconnected"}


@router.get("/{platform}/{account_id}/me")
async def account_me(platform: str, account_id: str):
    client = account_manager.get(platform, account_id)
    if not client:
        raise HTTPException(404, "Account not found")
    try:
        return await client.get_me()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, detail=str(exc)) from exp
