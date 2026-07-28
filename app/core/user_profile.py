"""Saved user profile (primary phone, pending auth hashes)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
PROFILE_FILE = DATA_DIR / "user_profile.json"

DEFAULTS: dict[str, Any] = {
    "phone": "",
    "pending": {},  # platform -> {phone_code_hash, transaction_hash, ...}
}


def _ensure() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not PROFILE_FILE.exists():
        PROFILE_FILE.write_text(
            json.dumps(DEFAULTS, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def load_profile() -> dict[str, Any]:
    _ensure()
    try:
        data = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    out = dict(DEFAULTS)
    out.update(data)
    if not isinstance(out.get("pending"), dict):
        out["pending"] = {}
    return out


def save_profile(data: dict[str, Any]) -> dict[str, Any]:
    _ensure()
    current = load_profile()
    current.update(data)
    PROFILE_FILE.write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return current


def set_phone(phone: str) -> dict[str, Any]:
    phone = phone.replace(" ", "").replace("-", "")
    return save_profile({"phone": phone})


def set_pending(platform: str, payload: dict[str, Any]) -> dict[str, Any]:
    p = load_profile()
    pending = dict(p.get("pending") or {})
    pending[platform] = payload
    return save_profile({"pending": pending})


def clear_pending(platform: str) -> dict[str, Any]:
    p = load_profile()
    pending = dict(p.get("pending") or {})
    pending.pop(platform, None)
    return save_profile({"pending": pending})
