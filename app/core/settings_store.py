"""Persistent JSON settings for AI, bots, WooCommerce, auto-reply."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"

DEFAULTS: dict[str, Any] = {
    "ai": {
        "provider": "avalai",
        "model": "gpt-4o-mini",
        "api_key": "",
        "base_url": "https://api.avalai.ir/v1",
        "system_prompt": (
            "You are a helpful assistant managing multi-platform messages. "
            "Reply in the user's language. Be concise and professional."
        ),
        "auto_reply_enabled": False,
        "auto_reply_platforms": ["telegram", "rubika", "bale", "soroush"],
    },
    "bots": {
        "telegram_bot_token": "",
        "bale_bot_token": "",
        "admin_chat_ids": [],
        "notify_on_new_message": True,
    },
    "woocommerce": {
        "enabled": False,
        "store_url": "",
        "consumer_key": "",
        "consumer_secret": "",
    },
    "ui": {
        "language": "fa",
        "theme": "dark",
    },
}


def _ensure() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(
            json.dumps(DEFAULTS, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def load_settings() -> dict[str, Any]:
    _ensure()
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    # deep-merge defaults
    out = json.loads(json.dumps(DEFAULTS))
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def save_settings(data: dict[str, Any]) -> dict[str, Any]:
    _ensure()
    current = load_settings()
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(current.get(k), dict):
            current[k].update(v)
        else:
            current[k] = v
    SETTINGS_FILE.write_text(
        json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return current
