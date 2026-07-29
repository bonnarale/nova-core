from __future__ import annotations

import pytest
from nova_core_sdk.hooks import HookManager


class TestHookManager:
    def test_register_and_emit(self) -> None:
        hm = HookManager()
        results = []
        hm.register("test", lambda x: results.append(x))
        hm.emit("test", "hello")
        assert results == ["hello"]

    def test_multiple_hooks_same_event(self) -> None:
        hm = HookManager()
        results = []
        hm.register("ev", lambda: results.append(1))
        hm.register("ev", lambda: results.append(2))
        hm.emit("ev")
        assert results == [1, 2]

    def test_unregister(self) -> None:
        hm = HookManager()
        fn = lambda: None
        hm.register("test", fn)
        hm.unregister("test", fn)
        assert hm.emit("test") == []

    def test_unregister_nonexistent(self) -> None:
        hm = HookManager()
        fn = lambda: None
        hm.unregister("test", fn)  # should not raise

    def test_clear_event(self) -> None:
        hm = HookManager()
        hm.register("a", lambda: 1)
        hm.register("b", lambda: 2)
        hm.clear("a")
        assert hm.emit("a") == []
        assert hm.emit("b") == [2]

    def test_clear_all(self) -> None:
        hm = HookManager()
        hm.register("a", lambda: 1)
        hm.register("b", lambda: 2)
        hm.clear()
        assert hm.emit("a") == []
        assert hm.emit("b") == []

    def test_emit_unknown_event(self) -> None:
        hm = HookManager()
        assert hm.emit("nonexistent") == []

    def test_emit_returns_results(self) -> None:
        hm = HookManager()
        hm.register("calc", lambda x: x * 2)
        hm.register("calc", lambda x: x + 10)
        results = hm.emit("calc", 5)
        assert results == [10, 15]
