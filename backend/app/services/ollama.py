import httpx

from app.core.config import Settings


class OllamaService:
    def __init__(self, settings: Settings) -> None:
        self._client = httpx.AsyncClient(base_url=settings.ollama_url, timeout=10)

    async def ready(self) -> bool:
        try:
            response = await self._client.get("/api/tags")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def close(self) -> None:
        await self._client.aclose()

