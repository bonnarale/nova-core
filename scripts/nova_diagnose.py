#!/usr/bin/env python3
"""NOVA CORE — Self-Diagnostic & Operational Validation System.

Detects environment, validates dependencies, checks services,
and produces an operational readiness score.

Usage:
    python scripts/nova-diagnose.py          # Full diagnostics
    python scripts/nova-diagnose.py --quick  # Quick health check
    python scripts/nova-diagnose.py --start  # Startup validation mode
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Status(str, Enum):
    READY = "READY"
    NOT_READY = "NOT_READY"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


@dataclass
class CheckResult:
    name: str
    status: Status
    message: str
    severity: Severity = Severity.HIGH
    detected: str = ""
    recommended: str = ""
    auto_fixable: bool = False


@dataclass
class DiagnosticReport:
    timestamp: str = ""
    platform_info: str = ""
    python_interpreter: str = ""
    checks: list[CheckResult] = field(default_factory=list)
    score: int = 0
    overall: Status = Status.UNKNOWN


# ---------------------------------------------------------------------------
# Python interpreter detection
# ---------------------------------------------------------------------------

def detect_python() -> CheckResult:
    """Detect the best available Python interpreter."""
    project_root = Path(__file__).resolve().parent.parent
    venv_paths = [
        project_root / ".venv" / "bin" / "python",
        project_root / "venv" / "bin" / "python",
        project_root / ".venv" / "Scripts" / "python.exe",
    ]

    # 1. Check virtual environment first
    for venv_py in venv_paths:
        if venv_py.exists():
            try:
                ver = subprocess.run(
                    [str(venv_py), "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                if ver.returncode == 0:
                    return CheckResult(
                        name="Python Interpreter",
                        status=Status.READY,
                        message=f"Virtual environment Python found: {ver.stdout.strip()}",
                        detected=str(venv_py),
                        recommended=str(venv_py),
                        severity=Severity.CRITICAL,
                    )
            except Exception:
                continue

    # 2. Check python3, then python
    for cmd in ("python3", "python"):
        path = shutil.which(cmd)
        if path:
            try:
                ver = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True, text=True, timeout=5,
                )
                if ver.returncode == 0:
                    return CheckResult(
                        name="Python Interpreter",
                        status=Status.READY,
                        message=f"System Python found: {ver.stdout.strip()}",
                        detected=f"{cmd} ({path})",
                        recommended=f"{cmd}",
                        severity=Severity.CRITICAL,
                    )
            except Exception:
                continue

    return CheckResult(
        name="Python Interpreter",
        status=Status.NOT_READY,
        message="No valid Python interpreter found.",
        severity=Severity.CRITICAL,
        recommended="Install Python 3.12+ or create a virtual environment.",
    )


# ---------------------------------------------------------------------------
# Dependency detection
# ---------------------------------------------------------------------------

def check_command(name: str, cmd: str, required: bool = True, version_flag: str = "--version") -> CheckResult:
    """Check if a command-line tool exists and get its version."""
    path = shutil.which(cmd)
    if not path:
        return CheckResult(
            name=name,
            status=Status.NOT_READY if required else Status.DEGRADED,
            message=f"{name} not found." + ("" if required else " (optional)"),
            severity=Severity.CRITICAL if required else Severity.MEDIUM,
            detected="not found",
            recommended=f"Install {name}" if required else "Optional — install if needed",
        )
    try:
        result = subprocess.run(
            [cmd, version_flag], capture_output=True, text=True, timeout=10,
        )
        version_str = (result.stdout + result.stderr).strip().split("\n")[0][:120]
        return CheckResult(
            name=name,
            status=Status.READY,
            message=f"{name} found: {version_str}",
            detected=path,
            severity=Severity.CRITICAL if required else Severity.MEDIUM,
        )
    except Exception as e:
        return CheckResult(
            name=name,
            status=Status.DEGRADED,
            message=f"{name} found but version check failed: {e}",
            detected=path,
            severity=Severity.MEDIUM,
        )


def check_module(name: str, module: str, required: bool = True) -> CheckResult:
    """Check if a Python module is importable (for tools like uvicorn)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", module, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        stdout = result.stdout.strip()
        if result.returncode == 0 and stdout:
            version_str = stdout.split("\n")[0][:120]
            return CheckResult(
                name=name,
                status=Status.READY,
                message=f"{name} found: {version_str}",
                detected=f"{sys.executable} -m {module}",
                severity=Severity.CRITICAL if required else Severity.MEDIUM,
            )
    except Exception:
        pass
    return CheckResult(
        name=name,
        status=Status.NOT_READY if required else Status.DEGRADED,
        message=f"{name} not available as Python module.",
        severity=Severity.CRITICAL if required else Severity.MEDIUM,
        recommended=f"pip install {module}" if required else "Optional",
    )


def check_port(port: int, name: str) -> CheckResult:
    """Check if a port is available or already in use by a service."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return CheckResult(
                name=f"Port {port} ({name})",
                status=Status.READY,
                message=f"Port {port} is active — {name} appears to be running.",
                severity=Severity.INFO,
            )
    except (ConnectionRefusedError, OSError, TimeoutError):
        return CheckResult(
            name=f"Port {port} ({name})",
            status=Status.DEGRADED,
            message=f"Port {port} is not responding — {name} is not running.",
            severity=Severity.MEDIUM,
        )


def check_python_package(package: str, import_name: str | None = None) -> CheckResult:
    """Check if a Python package is importable."""
    mod = import_name or package
    try:
        __import__(mod)
        return CheckResult(
            name=f"Python package: {package}",
            status=Status.READY,
            message=f"{package} is installed.",
            severity=Severity.MEDIUM,
        )
    except ImportError:
        return CheckResult(
            name=f"Python package: {package}",
            status=Status.NOT_READY,
            message=f"{package} is NOT installed.",
            severity=Severity.HIGH,
            recommended=f"pip install {package}",
        )


def check_url(url: str, name: str, timeout: int = 5) -> CheckResult:
    """Check if a URL is responding. For /health endpoints, parse the JSON body."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")[:500]
            # For health endpoints, parse the JSON body for actual status
            if "/health" in url:
                try:
                    import json as _json
                    data = _json.loads(body)
                    health_status = data.get("status", "unknown")
                    if health_status == "ok":
                        return CheckResult(
                            name=name,
                            status=Status.READY,
                            message=f"{name} is healthy (HTTP {resp.status}).",
                            detected=body[:200],
                            severity=Severity.CRITICAL,
                        )
                    elif health_status == "degraded":
                        return CheckResult(
                            name=name,
                            status=Status.DEGRADED,
                            message=f"{name} is degraded (HTTP {resp.status}). Status: {health_status}",
                            detected=body[:200],
                            severity=Severity.HIGH,
                        )
                except Exception:
                    pass
            return CheckResult(
                name=name,
                status=Status.READY,
                message=f"{name} is responding (HTTP {resp.status}).",
                detected=body[:200],
                severity=Severity.CRITICAL,
            )
    except urllib.error.HTTPError as e:
        return CheckResult(
            name=name,
            status=Status.DEGRADED,
            message=f"{name} returned HTTP {e.code}.",
            severity=Severity.HIGH,
        )
    except Exception as e:
        return CheckResult(
            name=name,
            status=Status.NOT_READY,
            message=f"{name} is not reachable: {e}",
            severity=Severity.CRITICAL,
            recommended="Ensure the service is started.",
        )


def check_file(path: str, name: str, required: bool = True) -> CheckResult:
    """Check if a file or directory exists."""
    p = Path(path)
    exists = p.exists()
    return CheckResult(
        name=name,
        status=Status.READY if exists else (Status.NOT_READY if required else Status.DEGRADED),
        message=f"{name} {'exists' if exists else 'not found'}.",
        detected=str(p),
        severity=Severity.CRITICAL if required else Severity.LOW,
    )


def check_docker_container(container: str, name: str) -> CheckResult:
    """Check if a Docker container is running and healthy."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Status}}", container],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            state = result.stdout.strip()
            if state == "running":
                health = subprocess.run(
                    ["docker", "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}", container],
                    capture_output=True, text=True, timeout=10,
                )
                health_status = health.stdout.strip() if health.returncode == 0 else "unknown"
                # Treat healthy and no-healthcheck as READY; treat unhealthy as DEGRADED
                if health_status in ("healthy", "no-healthcheck"):
                    status = Status.READY
                elif health_status == "starting":
                    status = Status.DEGRADED
                else:
                    status = Status.DEGRADED
                return CheckResult(
                    name=f"Docker: {name}",
                    status=status,
                    message=f"{name} container is running (health: {health_status}).",
                    detected=f"docker container {container}",
                    severity=Severity.INFO,
                )
            return CheckResult(
                name=f"Docker: {name}",
                status=Status.DEGRADED,
                message=f"{name} container state: {state}.",
                severity=Severity.HIGH,
            )
    except Exception:
        pass
    return CheckResult(
        name=f"Docker: {name}",
        status=Status.DEGRADED,
        message=f"{name} container not found or unreachable.",
        severity=Severity.HIGH,
    )


def discover_docker_containers() -> dict[str, str]:
    """Discover Docker Compose containers dynamically using docker compose ps."""
    containers: dict[str, str] = {}
    project_root = Path(__file__).resolve().parent.parent
    compose_file = project_root / "docker-compose.yml"
    if not compose_file.exists():
        return containers
    try:
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "ps", "--format", "json"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            import json as _json
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    svc = _json.loads(line)
                    name = svc.get("Name", "")
                    service = svc.get("Service", "")
                    if name and service:
                        containers[service] = name
                except _json.JSONDecodeError:
                    continue
    except Exception:
        pass
    return containers


def check_wsl_frontend() -> CheckResult:
    """Check if frontend is accessible via WSL."""
    try:
        result = subprocess.run(
            ["wsl", "-d", "Ubuntu-26.04", "--", "bash", "-c",
             "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/nova 2>/dev/null || echo '000'"],
            capture_output=True, text=True, timeout=15,
        )
        code = result.stdout.strip().strip("'")
        if code in ("200", "307"):
            return CheckResult(
                name="Frontend App",
                status=Status.READY,
                message=f"Frontend is accessible via WSL (HTTP {code}).",
                detected="wsl://localhost:3000/nova",
                severity=Severity.HIGH,
            )
    except Exception:
        pass
    return CheckResult(
        name="Frontend App",
        status=Status.NOT_READY,
        message="Frontend is not reachable.",
        severity=Severity.HIGH,
        recommended="Ensure the frontend dev server is running in WSL.",
    )


# ---------------------------------------------------------------------------
# Full diagnostic suite
# ---------------------------------------------------------------------------

def run_diagnostics(project_root: Path, quick: bool = False) -> DiagnosticReport:
    """Run all diagnostic checks and return a report."""
    report = DiagnosticReport()
    report.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    report.platform_info = f"{platform.system()} {platform.release()} ({platform.machine()})"

    # --- Python ---
    py_check = detect_python()
    report.python_interpreter = py_check.detected or "not found"
    report.checks.append(py_check)

    if py_check.status == Status.NOT_READY:
        report.checks.append(CheckResult(
            name="Python (blocker)",
            status=Status.NOT_READY,
            message="Cannot continue without Python. Stopping diagnostics.",
            severity=Severity.CRITICAL,
        ))
        report.overall = Status.NOT_READY
        report.score = 0
        return report

    # --- CLI tools ---
    report.checks.append(check_command("Node.js", "node", required=True))
    report.checks.append(check_command("npm", "npm", required=False))
    report.checks.append(check_module("uvicorn", "uvicorn", required=True))
    report.checks.append(check_command("Make", "make", required=False))

    docker_available = shutil.which("docker") is not None
    report.checks.append(check_command("Docker", "docker", required=False))
    if docker_available:
        report.checks.append(check_command("Docker Compose", "docker", required=False, version_flag="compose version"))

    if quick:
        return _quick_score(report)

    # --- Python packages ---
    critical_packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("httpx", "httpx"),
        ("sqlalchemy", "sqlalchemy"),
    ]
    optional_packages = [
        ("redis", "redis"),
        ("asyncpg", "asyncpg"),
        ("chromadb", "chromadb"),
    ]
    for pkg, imp in critical_packages:
        report.checks.append(check_python_package(pkg, imp))
    for pkg, imp in optional_packages:
        c = check_python_package(pkg, imp)
        c.severity = Severity.MEDIUM
        report.checks.append(c)

    # --- Project files ---
    report.checks.append(check_file(str(project_root / "backend" / "app" / "main.py"), "Backend main.py", required=True))
    report.checks.append(check_file(str(project_root / "frontend" / "package.json"), "Frontend package.json", required=True))
    report.checks.append(check_file(str(project_root / "Makefile"), "Makefile", required=False))

    # --- Ports ---
    report.checks.append(check_port(8000, "Backend"))
    report.checks.append(check_port(11434, "Ollama"))

    # Docker internal services — check via Docker if available
    if docker_available:
        discovered = discover_docker_containers()
        service_map = {
            "postgres": "PostgreSQL",
            "redis": "Redis",
            "chroma": "ChromaDB",
            "backend": "Backend Container",
        }
        for service_key, display_name in service_map.items():
            container_name = discovered.get(service_key)
            if container_name:
                report.checks.append(check_docker_container(container_name, display_name))
            else:
                # Fallback to port check if container not discovered
                port_map = {"postgres": 5432, "redis": 6379}
                if service_key in port_map:
                    report.checks.append(check_port(port_map[service_key], display_name))
    else:
        report.checks.append(check_port(5432, "PostgreSQL"))
        report.checks.append(check_port(6379, "Redis"))

    # --- Live API checks (only if backend port is active) ---
    backend_active = any(
        c.name == "Port 8000 (Backend)" and c.status == Status.READY
        for c in report.checks
    )
    if backend_active:
        report.checks.append(check_url("http://127.0.0.1:8000/health", "Backend /health"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/nova-web/dashboard", "NOVA Web Dashboard API"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/nova-web/objectives", "NOVA Web Objectives API"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/nova-web/projects", "NOVA Web Projects API"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/nova-web/approvals", "NOVA Web Approvals API"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/nova-web/recommendations", "NOVA Web Recommendations API"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/nova-web/memory", "NOVA Web Memory API"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/nova-web/tools", "NOVA Web Tools API"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/nova-web/observability", "NOVA Web Observability API"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/agents", "Agents API"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/tasks", "Tasks API"))
        report.checks.append(check_url("http://127.0.0.1:8000/api/v1/workflows", "Workflows API"))

    frontend_active = any(
        c.name == "Port 3000 (Frontend)" and c.status == Status.READY
        for c in report.checks
    )
    # Check frontend — try direct, then WSL relay
    if not frontend_active:
        fe_check = check_url("http://127.0.0.1:3000/nova", "Frontend App")
        if fe_check.status != Status.READY and docker_available:
            # Try via WSL if available
            fe_check = check_wsl_frontend()
        fe_check.severity = Severity.HIGH
        report.checks.append(fe_check)
    else:
        report.checks.append(check_url("http://127.0.0.1:3000", "Frontend App"))

    return _compute_score(report)


def _quick_score(report: DiagnosticReport) -> DiagnosticReport:
    """Quick mode: just score what we have."""
    return _compute_score(report)


def _compute_score(report: DiagnosticReport) -> DiagnosticReport:
    """Compute operational readiness score 0-100."""
    if not report.checks:
        report.score = 0
        report.overall = Status.NOT_READY
        return report

    total_weight = 0.0
    earned_weight = 0.0

    for c in report.checks:
        weight = {
            Severity.CRITICAL: 10.0,
            Severity.HIGH: 5.0,
            Severity.MEDIUM: 2.0,
            Severity.LOW: 1.0,
            Severity.INFO: 0.5,
        }.get(c.severity, 1.0)
        total_weight += weight
        if c.status == Status.READY:
            earned_weight += weight
        elif c.status == Status.DEGRADED:
            earned_weight += weight * 0.4

    report.score = int((earned_weight / total_weight) * 100) if total_weight > 0 else 0

    # Determine overall status
    critical_failures = [
        c for c in report.checks
        if c.status == Status.NOT_READY and c.severity == Severity.CRITICAL
    ]
    if critical_failures:
        report.overall = Status.NOT_READY
    elif report.score >= 80:
        report.overall = Status.READY
    elif report.score >= 50:
        report.overall = Status.DEGRADED
    else:
        report.overall = Status.NOT_READY

    return report


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

_STATUS_ICONS = {
    Status.READY: "OK",
    Status.NOT_READY: "FAIL",
    Status.DEGRADED: "WARN",
    Status.UNKNOWN: "??",
}

_SEVERITY_LABELS = {
    Severity.CRITICAL: "CRIT",
    Severity.HIGH: "HIGH",
    Severity.MEDIUM: "MED",
    Severity.LOW: "LOW",
    Severity.INFO: "INFO",
}


def format_report(report: DiagnosticReport, file: Any = None) -> str:
    """Format the diagnostic report for terminal output."""
    lines: list[str] = []
    w = lines.append

    w("")
    w("=" * 70)
    w("  NOVA CORE — Operational Diagnostics")
    w("=" * 70)
    w(f"  Timestamp:  {report.timestamp}")
    w(f"  Platform:   {report.platform_info}")
    w(f"  Python:     {report.python_interpreter}")
    w("=" * 70)
    w("")

    # Group checks by status
    failed = [c for c in report.checks if c.status == Status.NOT_READY]
    degraded = [c for c in report.checks if c.status == Status.DEGRADED]
    ok = [c for c in report.checks if c.status == Status.READY]

    if failed:
        w("  FAILURES:")
        w("  " + "-" * 66)
        for c in failed:
            icon = _STATUS_ICONS[c.status]
            sev = _SEVERITY_LABELS[c.severity]
            w(f"  [{icon}] [{sev}] {c.name}")
            w(f"         {c.message}")
            if c.detected:
                w(f"         Detected:  {c.detected}")
            if c.recommended:
                w(f"         Action:    {c.recommended}")
        w("")

    if degraded:
        w("  WARNINGS:")
        w("  " + "-" * 66)
        for c in degraded:
            icon = _STATUS_ICONS[c.status]
            sev = _SEVERITY_LABELS[c.severity]
            w(f"  [{icon}] [{sev}] {c.name}")
            w(f"         {c.message}")
            if c.recommended:
                w(f"         Action:    {c.recommended}")
        w("")

    w("  OK:")
    w("  " + "-" * 66)
    for c in ok:
        w(f"  [OK] {c.name}: {c.message}")
    w("")

    # Score
    w("=" * 70)
    overall_str = report.overall.value
    if report.overall == Status.READY:
        verdict = "NOVA IS OPERATIONAL"
    elif report.overall == Status.DEGRADED:
        verdict = "NOVA IS PARTIALLY OPERATIONAL (degraded)"
    else:
        verdict = "NOVA IS NOT OPERATIONAL"

    w(f"  Operational Score: {report.score}/100")
    w(f"  Overall Status:    {overall_str}")
    w(f"  Verdict:           {verdict}")
    w("=" * 70)

    # Recommendations
    if failed:
        w("")
        w("  RECOMMENDATIONS:")
        w("  " + "-" * 66)
        for c in failed:
            if c.recommended:
                w(f"  * {c.name}: {c.recommended}")
        w("")

    return "\n".join(lines)


def format_json(report: DiagnosticReport) -> str:
    """Format the diagnostic report as JSON."""
    return json.dumps({
        "timestamp": report.timestamp,
        "platform": report.platform_info,
        "python": report.python_interpreter,
        "score": report.score,
        "overall": report.overall.value,
        "checks": [
            {
                "name": c.name,
                "status": c.status.value,
                "severity": c.severity.value,
                "message": c.message,
                "detected": c.detected,
                "recommended": c.recommended,
            }
            for c in report.checks
        ],
    }, indent=2)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="NOVA CORE Self-Diagnostic System")
    parser.add_argument("--quick", action="store_true", help="Quick health check only")
    parser.add_argument("--start", action="store_true", help="Startup validation mode (fail if NOT READY)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    report = run_diagnostics(project_root, quick=args.quick)

    if args.json:
        print(format_json(report))
    else:
        print(format_report(report))

    if args.start and report.overall == Status.NOT_READY:
        print("\n  STARTUP ABORTED: Critical failures detected.")
        print("  Fix the issues above and try again.\n")
        return 1

    if report.overall == Status.NOT_READY:
        return 1
    elif report.overall == Status.DEGRADED:
        return 0  # Allow degraded
    return 0


if __name__ == "__main__":
    sys.exit(main())
