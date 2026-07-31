"""Abstract base classes for the API Platform subsystem."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.api.enums import APIVersion, ErrorCode, LifecycleState


class APIProvider(ABC):
    """Provider interface for the API platform."""

    @abstractmethod
    async def initialize(self) -> None:
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        ...

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        ...


class APIVersionProvider(ABC):
    """Provider interface for API versioning."""

    @abstractmethod
    def get_version(self) -> str:
        ...

    @abstractmethod
    def get_supported_versions(self) -> list[str]:
        ...

    @abstractmethod
    def is_deprecated(self, version: str) -> bool:
        ...

    @abstractmethod
    def get_deprecation_date(self, version: str) -> str | None:
        ...


class APIRegistry(ABC):
    """Interface for endpoint registration."""

    @abstractmethod
    def register_endpoint(
        self,
        path: str,
        method: str,
        handler: Any,
        tags: list[str] | None = None,
        version: str = "v1",
        **kwargs: Any,
    ) -> None:
        ...

    @abstractmethod
    def get_endpoints(self) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def get_endpoint(self, path: str, method: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    def list_by_tag(self, tag: str) -> list[dict[str, Any]]:
        ...

    @abstractmethod
    def count(self) -> int:
        ...


class ResponseFormatter(ABC):
    """Interface for formatting API responses."""

    @abstractmethod
    def success(
        self,
        data: Any = None,
        metadata: dict[str, Any] | None = None,
        request_id: str = "",
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    def error(
        self,
        code: ErrorCode,
        message: str,
        details: list[dict[str, Any]] | None = None,
        request_id: str = "",
    ) -> dict[str, Any]:
        ...

    @abstractmethod
    def paginated(
        self,
        data: list[Any],
        total: int,
        page: int = 1,
        page_size: int = 20,
        request_id: str = "",
    ) -> dict[str, Any]:
        ...


class ErrorHandler(ABC):
    """Interface for handling API errors."""

    @abstractmethod
    def handle_validation(self, errors: list[dict[str, Any]], request_id: str = "") -> dict[str, Any]:
        ...

    @abstractmethod
    def handle_not_found(self, resource: str, request_id: str = "") -> dict[str, Any]:
        ...

    @abstractmethod
    def handle_unauthorized(self, message: str = "", request_id: str = "") -> dict[str, Any]:
        ...

    @abstractmethod
    def handle_forbidden(self, message: str = "", request_id: str = "") -> dict[str, Any]:
        ...

    @abstractmethod
    def handle_conflict(self, message: str, request_id: str = "") -> dict[str, Any]:
        ...

    @abstractmethod
    def handle_rate_limit(self, retry_after: int = 60, request_id: str = "") -> dict[str, Any]:
        ...

    @abstractmethod
    def handle_internal(self, message: str = "", request_id: str = "") -> dict[str, Any]:
        ...

    @abstractmethod
    def handle_timeout(self, request_id: str = "") -> dict[str, Any]:
        ...

    @abstractmethod
    def handle_deprecated(self, message: str = "", sunset_date: str = "", request_id: str = "") -> dict[str, Any]:
        ...


class OpenAPIProvider(ABC):
    """Interface for OpenAPI schema generation."""

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_tags(self) -> list[dict[str, str]]:
        ...

    @abstractmethod
    def get_security_schemes(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_info(self) -> dict[str, Any]:
        ...
