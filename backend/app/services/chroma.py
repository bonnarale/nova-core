from typing import Any

import chromadb

from app.core.config import Settings


class ChromaService:
    def __init__(self, settings: Settings) -> None:
        self._client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)

    @property
    def client(self) -> Any:
        return self._client

    def ready(self) -> bool:
        try:
            self._client.heartbeat()
            return True
        except Exception:
            return False
