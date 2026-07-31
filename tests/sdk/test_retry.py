from __future__ import annotations

import pytest
from nova_core_sdk.retry import RetryHandler
from nova_core_sdk.exceptions import NovaRateLimitError, NovaServerError


class TestRetryHandler:
    def test_delay_calculation(self) -> None:
        handler = RetryHandler(max_retries=3, base_delay=0.5, max_delay=30.0, backoff=2.0)
        assert handler.calculate_delay(0) == 0.5
        assert handler.calculate_delay(1) == 1.0
        assert handler.calculate_delay(2) == 2.0

    def test_delay_capped(self) -> None:
        handler = RetryHandler(max_retries=10, base_delay=1.0, max_delay=5.0, backoff=2.0)
        assert handler.calculate_delay(10) == 5.0

    def test_retry_after_override(self) -> None:
        handler = RetryHandler()
        assert handler.calculate_delay(0, retry_after=10.0) == 10.0

    def test_should_retry_within_limit(self) -> None:
        handler = RetryHandler(max_retries=3)
        assert handler.should_retry(0, 500) is True
        assert handler.should_retry(3, 500) is False

    def test_should_retry_status_codes(self) -> None:
        handler = RetryHandler(max_retries=5)
        assert handler.should_retry(0, 429) is True
        assert handler.should_retry(0, 500) is True
        assert handler.should_retry(0, 502) is True
        assert handler.should_retry(0, 400) is False
        assert handler.should_retry(0, 401) is False
        assert handler.should_retry(0, 404) is False

    def test_should_retry_no_status(self) -> None:
        handler = RetryHandler(max_retries=3)
        assert handler.should_retry(0, None) is True

    @pytest.mark.asyncio
    async def test_execute_success(self) -> None:
        handler = RetryHandler(max_retries=2)
        call_count = 0

        async def success_fn() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await handler.execute_with_retry(success_fn)
        assert result == "ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(self) -> None:
        handler = RetryHandler(max_retries=3, base_delay=0.01)
        call_count = 0

        async def flaky_fn() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NovaServerError("server error", status_code=500)
            return "ok"

        result = await handler.execute_with_retry(flaky_fn)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_execute_exhausted_retries(self) -> None:
        handler = RetryHandler(max_retries=2, base_delay=0.01)

        async def always_fail() -> None:
            raise NovaServerError("fail", status_code=500)

        with pytest.raises(NovaServerError):
            await handler.execute_with_retry(always_fail)
