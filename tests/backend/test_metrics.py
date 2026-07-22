"""Tests for the metrics module."""

from __future__ import annotations

import time

from app.agents.metrics import MetricsCollector


class TestMetricsCollector:
    def test_increment(self):
        m = MetricsCollector()
        m.increment("requests")
        m.increment("requests")
        m.increment("errors")
        snap = m.snapshot()
        assert snap["counters"]["requests"] == 2
        assert snap["counters"]["errors"] == 1

    def test_gauge(self):
        m = MetricsCollector()
        m.gauge("temperature", 36.5)
        assert m.snapshot()["gauges"]["temperature"] == 36.5

    def test_record_duration(self):
        m = MetricsCollector()
        m.record_duration("api_call", 150.0)
        m.record_duration("api_call", 250.0)
        snap = m.snapshot()
        assert snap["timers"]["api_call"]["count"] == 2
        assert snap["timers"]["api_call"]["avg_ms"] == 200.0
        assert snap["timers"]["api_call"]["min_ms"] == 150.0
        assert snap["timers"]["api_call"]["max_ms"] == 250.0

    def test_timer_context_manager(self):
        m = MetricsCollector()
        with m.time("operation"):
            time.sleep(0.01)
        snap = m.snapshot()
        assert snap["timers"]["operation"]["count"] == 1
        assert snap["timers"]["operation"]["avg_ms"] >= 5

    def test_clear(self):
        m = MetricsCollector()
        m.increment("counter")
        m.record_duration("timer", 100)
        m.clear()
        snap = m.snapshot()
        assert snap["counters"] == {}
        assert snap["timers"] == {}

    def test_empty_timer(self):
        m = MetricsCollector()
        snap = m.snapshot()
        assert snap["timers"] == {}

    def test_multiple_counters(self):
        m = MetricsCollector()
        for label in ["a", "b", "c"]:
            m.increment(label)
        snap = m.snapshot()
        assert all(snap["counters"][l] == 1 for l in ["a", "b", "c"])
