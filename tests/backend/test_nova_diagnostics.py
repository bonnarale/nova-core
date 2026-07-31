"""Tests for NOVA CORE Self-Diagnostic & Operational Validation System."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))
from nova_diagnose import (
    CheckResult,
    DiagnosticReport,
    Severity,
    Status,
    _compute_score,
    check_command,
    check_file,
    check_module,
    check_port,
    check_python_package,
    check_url,
    detect_python,
    format_json,
    format_report,
    run_diagnostics,
)


# ---------------------------------------------------------------------------
# CheckResult basics
# ---------------------------------------------------------------------------

class TestCheckResult:
    def test_ready_result(self) -> None:
        r = CheckResult(name="test", status=Status.READY, message="ok")
        assert r.status == Status.READY
        assert r.name == "test"

    def test_not_ready_result(self) -> None:
        r = CheckResult(name="fail", status=Status.NOT_READY, message="broken", severity=Severity.CRITICAL)
        assert r.status == Status.NOT_READY
        assert r.severity == Severity.CRITICAL

    def test_auto_fixable_default(self) -> None:
        r = CheckResult(name="x", status=Status.READY, message="ok")
        assert r.auto_fixable is False


# ---------------------------------------------------------------------------
# Python detection
# ---------------------------------------------------------------------------

class TestDetectPython:
    def test_detect_returns_ready_or_not_ready(self) -> None:
        result = detect_python()
        assert isinstance(result, CheckResult)
        assert result.status in (Status.READY, Status.NOT_READY)
        assert result.name == "Python Interpreter"
        assert result.severity == Severity.CRITICAL

    def test_detect_on_this_system(self) -> None:
        result = detect_python()
        # On any system with Python, this should be READY
        assert result.status == Status.READY
        assert result.message != ""


# ---------------------------------------------------------------------------
# Command / module checks
# ---------------------------------------------------------------------------

class TestCheckCommand:
    def test_existing_command(self) -> None:
        r = check_command("Python", sys.executable, required=True)
        assert r.status == Status.READY

    def test_nonexistent_command(self) -> None:
        r = check_command("FakeTool99", "fake_tool_99_nonexistent_xyz", required=False)
        assert r.status == Status.DEGRADED

    def test_nonexistent_required(self) -> None:
        r = check_command("FakeTool99", "fake_tool_99_nonexistent_xyz", required=True)
        assert r.status == Status.NOT_READY
        assert r.severity == Severity.CRITICAL


class TestCheckModule:
    def test_existing_module(self) -> None:
        r = check_module("pip", "pip", required=True)
        assert r.status == Status.READY

    def test_nonexistent_module(self) -> None:
        r = check_module("FakeModule99", "fake_module_99_nonexistent", required=False)
        assert r.status in (Status.NOT_READY, Status.DEGRADED)


class TestCheckPythonPackage:
    def test_installed_package(self) -> None:
        r = check_python_package("json", "json")
        assert r.status == Status.READY

    def test_missing_package(self) -> None:
        r = check_python_package("nonexistent_pkg_xyz", "nonexistent_pkg_xyz")
        assert r.status == Status.NOT_READY
        assert "pip install" in r.recommended


# ---------------------------------------------------------------------------
# Port checks
# ---------------------------------------------------------------------------

class TestCheckPort:
    def test_port_check_returns_check_result(self) -> None:
        r = check_port(99999, "nonexistent")
        assert isinstance(r, CheckResult)
        assert r.status in (Status.READY, Status.DEGRADED)


# ---------------------------------------------------------------------------
# URL checks
# ---------------------------------------------------------------------------

class TestCheckURL:
    def test_unreachable_url(self) -> None:
        r = check_url("http://127.0.0.1:19999/nonexistent", "Test URL")
        assert r.status == Status.NOT_READY


# ---------------------------------------------------------------------------
# File checks
# ---------------------------------------------------------------------------

class TestCheckFile:
    def test_existing_file(self) -> None:
        r = check_file(str(Path(__file__)), "Test file", required=True)
        assert r.status == Status.READY

    def test_missing_file(self) -> None:
        r = check_file("/nonexistent/path/file.txt", "Missing file", required=True)
        assert r.status == Status.NOT_READY

    def test_missing_optional_file(self) -> None:
        r = check_file("/nonexistent/path/file.txt", "Optional file", required=False)
        assert r.status == Status.DEGRADED


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

class TestComputeScore:
    def test_all_ready(self) -> None:
        report = DiagnosticReport()
        report.checks = [
            CheckResult(name="a", status=Status.READY, message="ok", severity=Severity.CRITICAL),
            CheckResult(name="b", status=Status.READY, message="ok", severity=Severity.HIGH),
        ]
        report = _compute_score(report)
        assert report.score == 100
        assert report.overall == Status.READY

    def test_all_not_ready(self) -> None:
        report = DiagnosticReport()
        report.checks = [
            CheckResult(name="a", status=Status.NOT_READY, message="fail", severity=Severity.CRITICAL),
        ]
        report = _compute_score(report)
        assert report.overall == Status.NOT_READY

    def test_mixed_statuses(self) -> None:
        report = DiagnosticReport()
        report.checks = [
            CheckResult(name="a", status=Status.READY, message="ok", severity=Severity.CRITICAL),
            CheckResult(name="b", status=Status.DEGRADED, message="meh", severity=Severity.LOW),
        ]
        report = _compute_score(report)
        assert 50 <= report.score <= 100

    def test_empty_checks(self) -> None:
        report = DiagnosticReport()
        report = _compute_score(report)
        assert report.score == 0
        assert report.overall == Status.NOT_READY


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

class TestFormatting:
    def test_format_report_returns_string(self) -> None:
        report = DiagnosticReport(
            timestamp="2026-01-01 00:00:00",
            platform_info="Test",
            python_interpreter="python3",
            checks=[CheckResult(name="x", status=Status.READY, message="ok")],
            score=100,
            overall=Status.READY,
        )
        output = format_report(report)
        assert "NOVA CORE" in output
        assert "100/100" in output
        assert "OPERATIONAL" in output

    def test_format_json(self) -> None:
        report = DiagnosticReport(
            timestamp="2026-01-01",
            platform_info="Test",
            checks=[CheckResult(name="x", status=Status.READY, message="ok")],
            score=100,
            overall=Status.READY,
        )
        output = format_json(report)
        parsed = json.loads(output)
        assert parsed["score"] == 100
        assert parsed["overall"] == "READY"
        assert len(parsed["checks"]) == 1


# ---------------------------------------------------------------------------
# Full diagnostic run
# ---------------------------------------------------------------------------

class TestRunDiagnostics:
    def test_quick_diagnostics(self) -> None:
        project_root = Path(__file__).resolve().parent.parent.parent
        report = run_diagnostics(project_root, quick=True)
        assert isinstance(report, DiagnosticReport)
        assert report.timestamp != ""
        assert len(report.checks) > 0
        assert 0 <= report.score <= 100
        assert report.overall in (Status.READY, Status.DEGRADED, Status.NOT_READY)

    def test_full_diagnostics(self) -> None:
        project_root = Path(__file__).resolve().parent.parent.parent
        report = run_diagnostics(project_root, quick=False)
        assert isinstance(report, DiagnosticReport)
        assert len(report.checks) > 5
        assert 0 <= report.score <= 100

    def test_diagnostics_without_python_stops_early(self) -> None:
        project_root = Path(__file__).resolve().parent.parent.parent
        with patch("nova_diagnose.detect_python", return_value=CheckResult(
            name="Python Interpreter", status=Status.NOT_READY, message="none",
            severity=Severity.CRITICAL,
        )):
            report = run_diagnostics(project_root, quick=False)
            assert report.overall == Status.NOT_READY
            assert report.score == 0
