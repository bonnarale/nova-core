from __future__ import annotations

import json
from typing import Any, AsyncIterator, Iterator


class StreamProcessor:
    def __init__(self, response: Any) -> None:
        self._response = response

    def __iter__(self) -> Iterator[dict[str, Any]]:
        for line in self._response.iter_lines():
            if not line:
                continue
            line_str = line if isinstance(line, str) else line.decode("utf-8")
            if line_str.startswith("data: "):
                data_str = line_str[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    yield json.loads(data_str)
                except json.JSONDecodeError:
                    continue

    def text(self) -> str:
        chunks: list[str] = []
        for chunk in self:
            if "choices" in chunk:
                for choice in chunk["choices"]:
                    delta = choice.get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        chunks.append(content)
            elif "content" in chunk:
                chunks.append(chunk["content"])
        return "".join(chunks)


class AsyncStreamProcessor:
    def __init__(self, response: Any) -> None:
        self._response = response

    async def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        async for line in self._response.aiter_lines():
            if not line:
                continue
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    yield json.loads(data_str)
                except json.JSONDecodeError:
                    continue

    async def text(self) -> str:
        chunks: list[str] = []
        async for chunk in self:
            if "choices" in chunk:
                for choice in chunk["choices"]:
                    delta = choice.get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        chunks.append(content)
            elif "content" in chunk:
                chunks.append(chunk["content"])
        return "".join(chunks)
