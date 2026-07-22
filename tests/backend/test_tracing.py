"""Tests for the tracing module."""

from __future__ import annotations

from app.agents.tracing import Tracer


class TestTracer:
    def test_start_span_creates_span(self):
        t = Tracer()
        span = t.start_span("agent-a", "do work", task_id="t-1")
        assert span.agent_id == "agent-a"
        assert span.task == "do work"
        assert span.span_id is not None
        assert span.start_time > 0

    def test_span_close_records_duration(self):
        t = Tracer()
        span = t.start_span("agent-x", "task")
        span.close(status="success", output={"done": True})
        assert span.status == "success"
        assert span.output == {"done": True}
        assert span.duration_ms >= 0

    def test_trace_aggregation(self):
        t = Tracer()
        s1 = t.start_span("a1", "task1", trace_id="trace-1")
        s2 = t.start_span("a2", "task2", trace_id="trace-1", parent_span_id=s1.span_id)
        trace = t.get_trace("trace-1")
        assert len(trace) == 2

    def test_get_span(self):
        t = Tracer()
        s1 = t.start_span("a1", "t1")
        assert t.get_span(s1.span_id) is s1
        assert t.get_span("nonexistent") is None

    def test_child_spans(self):
        t = Tracer()
        parent = t.start_span("parent", "root")
        child = t.start_span("child", "sub", parent_span_id=parent.span_id)
        assert child in parent.child_spans

    def test_to_dict_structure(self):
        t = Tracer()
        span = t.start_span("agent", "task")
        span.close(status="success")
        result = t.to_dict()
        assert len(result) >= 1
        entry = result[0]
        assert entry["agent_id"] == "agent"
        assert entry["task"] == "task"
        assert entry["status"] == "success"
        assert "duration_ms" in entry

    def test_clear(self):
        t = Tracer()
        t.start_span("a", "t")
        assert len(t.to_dict()) >= 1
        t.clear()
        assert t.to_dict() == []

    def test_get_all_traces(self):
        t = Tracer()
        t.start_span("a", "t1", trace_id="tr1")
        t.start_span("b", "t2", trace_id="tr2")
        all_traces = t.get_all_traces()
        assert "tr1" in all_traces
        assert "tr2" in all_traces
