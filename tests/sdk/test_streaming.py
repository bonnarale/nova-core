from __future__ import annotations

import pytest
from nova_core_sdk.streaming import StreamProcessor, AsyncStreamProcessor


class TestStreamProcessor:
    def test_init(self) -> None:
        class MockResponse:
            pass
        processor = StreamProcessor(MockResponse())
        assert processor._response is not None


class TestAsyncStreamProcessor:
    def test_init(self) -> None:
        class MockResponse:
            pass
        processor = AsyncStreamProcessor(MockResponse())
        assert processor._response is not None
