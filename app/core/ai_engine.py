"""Unified AI engine supporting Ollama and OpenAI-compatible APIs."""

from __future__ import annotations

from typing import Any, Optional

import httpx
from loguru import logger

from app.config import get_settings


class AIEngine:
    """Generate replies and content using configured AI provider."""

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
        provider = self.settings.ai_provider.lower()

        if provider == "ollama":
            return await self._ollama(prompt, system=system, model=model, temperature=temperature)
        if provider in ("openai", "openai-compatible"):
            return await self._openai_compatible(
                prompt,
                system=system,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
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
        """High-level helper for auto-reply scenarios."""
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
    ) -> str:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")

        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise RuntimeError("Install openai package: pip install openai") from exc

        client = AsyncOpenAI(
            api_key=self.settings.openai_api_key,
            base_url=self.settings.openai_base_url or None,
        )
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


# Shared instance
ai_engine = AIEngine()
