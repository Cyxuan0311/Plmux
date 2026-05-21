"""Lightweight event bus for decoupled component communication."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, Callable, Coroutine, Dict, List

Handler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    def __init__(self) -> None:
        self._sync_handlers: Dict[str, List[Callable[..., None]]] = defaultdict(list)
        self._async_handlers: Dict[str, List[Handler]] = defaultdict(list)

    def on(self, event: str, handler: Callable[..., None]) -> None:
        self._sync_handlers[event].append(handler)

    def on_async(self, event: str, handler: Handler) -> None:
        self._async_handlers[event].append(handler)

    def off(self, event: str, handler: Callable[..., None] | Handler) -> None:
        self._sync_handlers[event] = [h for h in self._sync_handlers[event] if h is not handler]
        self._async_handlers[event] = [h for h in self._async_handlers[event] if h is not handler]

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        for handler in self._sync_handlers.get(event, []):
            try:
                handler(*args, **kwargs)
            except Exception:
                pass

    async def emit_async(self, event: str, *args: Any, **kwargs: Any) -> None:
        tasks = []
        for handler in self._async_handlers.get(event, []):
            tasks.append(asyncio.ensure_future(handler(*args, **kwargs)))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def clear(self) -> None:
        self._sync_handlers.clear()
        self._async_handlers.clear()


_default_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _default_bus
    if _default_bus is None:
        _default_bus = EventBus()
    return _default_bus


def reset_event_bus() -> None:
    global _default_bus
    _default_bus = None