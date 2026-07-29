from __future__ import annotations

from typing import Any, Callable


class HookManager:
    def __init__(self) -> None:
        self._hooks: dict[str, list[Callable[..., Any]]] = {
            "pre_request": [],
            "post_request": [],
            "pre_auth": [],
            "post_auth": [],
            "on_error": [],
            "on_retry": [],
            "on_stream_chunk": [],
        }

    def register(self, event: str, callback: Callable[..., Any]) -> None:
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def unregister(self, event: str, callback: Callable[..., Any]) -> None:
        if event in self._hooks and callback in self._hooks[event]:
            self._hooks[event].remove(callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> list[Any]:
        results: list[Any] = []
        for callback in self._hooks.get(event, []):
            result = callback(*args, **kwargs)
            results.append(result)
        return results

    def clear(self, event: str | None = None) -> None:
        if event:
            self._hooks.pop(event, None)
        else:
            self._hooks.clear()
