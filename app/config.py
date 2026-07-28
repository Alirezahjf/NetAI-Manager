"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "NetAI-Manager"
    app_version: str = "0.2.0"
    secret_key: str = "change-me"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    # AI — default: AvalAI (اول AI) OpenAI-compatible gateway
    # Providers: avalai | ollama | openai | openai-compatible
    ai_provider: str = "avalai"
    ai_model: str = "gpt-4o-mini"
    ai_system_prompt: str = (
        "You are a helpful, professional assistant that helps manage social accounts. "
        "Always reply in the same language as the user message. Be concise and natural."
    )

    # AvalAI (اول AI) — https://docs.avalai.ir
    avalai_api_key: Optional[str] = None
    avalai_base_url: str = "https://api.avalai.ir/v1"
    # Alternate in-country mirror (optional): https://api.avalapis.ir/v1

    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = "https://api.openai.com/v1"

    # Telegram
    telegram_api_id: Optional[int] = None
    telegram_api_hash: Optional[str] = None
    telegram_session_name: str = "netai_telegram"

    # Bale (bot token optional; user mode uses phone auth)
    bale_bot_token: Optional[str] = None

    # Soroush
    soroush_default_backend: str = "websocket"

    # Email
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_use_tls: bool = True
    imap_host: Optional[str] = None
    imap_port: int = 993
    email_user: Optional[str] = None
    email_password: Optional[str] = None

    # YouTube
    youtube_api_key: Optional[str] = None
    youtube_client_secrets_file: Optional[str] = None

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
