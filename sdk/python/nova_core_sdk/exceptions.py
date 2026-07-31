from __future__ import annotations

from typing import Any


class NovaError(Exception):
    def __init__(self, message: str, status_code: int | None = None, response: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class NovaAPIError(NovaError):
    pass


class NovaAuthError(NovaAPIError):
    pass


class NovaRateLimitError(NovaAPIError):
    def __init__(self, message: str, retry_after: float | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class NovaServerError(NovaAPIError):
    pass


class NovaConnectionError(NovaError):
    pass


class NovaTimeoutError(NovaError):
    pass


class NovaValidationError(NovaAPIError):
    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.errors = errors or []
