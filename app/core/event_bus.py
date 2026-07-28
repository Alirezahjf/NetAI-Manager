"""Simple async-friendly event bus for cross-platform events."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Awaitable, Callable, DefaultDict, List

Handler = Callable[[dict], Awaitable[None] | None]


class EventBus:
    """Central pub/sub for platform events (new_message, status, errors, ...)."""

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, List[Handler]] = defaultdict(list)
        self._lock = asyncio.Lock()

    def on(self, event: str, handler: Handler) -> None:
        self._handlers[event].append(handler)

    def off(self, event: str, handler: Handler) -> None:
        if handler in self._handlers[event]:
            self._handlers[event].remove(handler)

    async def emit(self, event: str, payload: dict[str, Any] | None = None) -> None:
        data = payload or {}
        data.setdefault("event", event)
        handlers = list(self._handlers.get(event, []))
        handlers += list(self._handlers.get("*", []))

        for handler in handlers:
            try:
                result = handler(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:  # noqa: BLE001
                # Never let a bad handler kill the bus
                print(f"[EventBus] handler error on '{event}': {exc}")


# Singleton used across the app
event_bus = EventBus()
