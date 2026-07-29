from __future__ import annotations

from typing import Any, AsyncIterator, Iterator

from pydantic import BaseModel


class PageIterator:
    def __init__(
        self,
        client: Any,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        page_size: int = 20,
    ) -> None:
        self._client = client
        self._method = method
        self._path = path
        self._params = params or {}
        self._page_size = page_size

    def __iter__(self) -> Iterator[dict[str, Any]]:
        offset = 0
        while True:
            params = {**self._params, "limit": self._page_size, "offset": offset}
            response = self._client._request(self._method, self._path, params=params)
            data = response if isinstance(response, list) else response.get("data", [])
            if not data:
                break
            yield from data
            offset += self._page_size
            if len(data) < self._page_size:
                break

    def all(self) -> list[dict[str, Any]]:
        return list(self)


class AsyncPageIterator:
    def __init__(
        self,
        client: Any,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        page_size: int = 20,
    ) -> None:
        self._client = client
        self._method = method
        self._path = path
        self._params = params or {}
        self._page_size = page_size

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self._aiter()

    async def _aiter(self) -> AsyncIterator[dict[str, Any]]:
        offset = 0
        while True:
            params = {**self._params, "limit": self._page_size, "offset": offset}
            response = await self._client._request(self._method, self._path, params=params)
            data = response if isinstance(response, list) else response.get("data", [])
            if not data:
                break
            for item in data:
                yield item
            offset += self._page_size
            if len(data) < self._page_size:
                break

    async def all(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        async for item in self:
            result.append(item)
        return result
