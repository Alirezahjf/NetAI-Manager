"""Unified AI engine — AvalAI (اول AI) first, plus Ollama / OpenAI-compatible."""

from __future__ import annotations

from typing import Any, Optional

import httpx
from loguru import logger

from app.config import get_settings


class AIEngine:
    """
    Generate replies and content.

    Default provider is **AvalAI** (اول AI):
      base_url = https://api.avalai.ir/v1
      auth     = Bearer AVALAI_API_KEY
      format   = OpenAI chat.completions (future-proof for model upgrades)

    Docs: https://docs.avalai.ir
    """

    def __init__(self) -> None:
        self.settings = get_settings()

    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        system = system or self.settings.ai_system_prompt
        model = model or self.settings.ai_model
        provider = self.settings.ai_provider.lower().strip()

        if provider in ("avalai", "aval", "اول", "اولai", "اول-ai"):
            return await self._openai_compatible(
                prompt,
                system=system,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.settings.avalai_api_key,
                base_url=self.settings.avalai_base_url,
                provider_label="AvalAI",
            )
        if provider == "ollama":
            return await self._ollama(prompt, system=system, model=model, temperature=temperature)
        if provider in ("openai", "openai-compatible"):
            return await self._openai_compatible(
                prompt,
                system=system,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url or "https://api.openai.com/v1",
                provider_label="OpenAI",
            )
        raise ValueError(f"Unsupported AI provider: {provider}")

    async def reply_to_message(
        self,
        message_text: str,
        *,
        platform: str = "",
        chat_context: str = "",
        extra_instructions: str = "",
    ) -> str:
        system = self.settings.ai_system_prompt
        if extra_instructions:
            system = f"{system}\n\nExtra instructions:\n{extra_instructions}"

        user_prompt = (
            f"Platform: {platform or 'unknown'}\n"
            f"Context: {chat_context or 'none'}\n\n"
            f"Incoming message:\n{message_text}\n\n"
            "Write a natural reply. Do not add explanations outside the reply itself."
        )
        return await self.generate(user_prompt, system=system)

    async def list_models(self) -> list[dict[str, Any]]:
        """List models from AvalAI (or configured OpenAI-compatible endpoint)."""
        provider = self.settings.ai_provider.lower().strip()
        if provider in ("avalai", "aval", "اول", "اولai", "اول-ai"):
            key = self.settings.avalai_api_key
            base = self.settings.avalai_base_url.rstrip("/")
        else:
            key = self.settings.openai_api_key
            base = (self.settings.openai_base_url or "https://api.openai.com/v1").rstrip("/")

        headers = {"Authorization": f"Bearer {key}"} if key else {}
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Public list works without key on AvalAI
            if provider in ("avalai", "aval", "اول", "اولai", "اول-ai") and not key:
                resp = await client.get("https://api.avalai.ir/public/models")
            else:
                resp = await client.get(f"{base}/models", headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "data" in data:
                return data["data"]
            if isinstance(data, list):
                return data
            return [data]

    async def _ollama(
        self,
        prompt: str,
        *,
        system: str,
        model: str,
        temperature: float,
    ) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        payload: dict[str, Any] = {
            "model": model,
            "stream": False,
            "options": {"temperature": temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()

    async def _openai_compatible(
        self,
        prompt: str,
        *,
        system: str,
        model: str,
        temperature: float,
        max_tokens: int,
        api_key: Optional[str],
        base_url: str,
        provider_label: str,
    ) -> str:
        if not api_key:
            raise RuntimeError(
                f"{provider_label} API key is not set. "
                f"For AvalAI set AVALAI_API_KEY in .env (from https://avalai.ir dashboard)."
            )

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("Install openai package: pip install openai") from exc

        client = AsyncOpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
        completion = await client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return (completion.choices[0].message.content or "").strip()


ai_engine = AIEngine()
