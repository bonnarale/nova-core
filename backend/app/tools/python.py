"""PythonTool — run Python code snippets via subprocess."""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class PythonTool(Tool):
    """Execute Python code snippets and scripts."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="python",
            description="Execute Python code snippets and scripts via subprocess.",
            category="code",
            timeout_default=30.0,
            retry_default=0,
            permission_level="admin",
            parameters=[
                ToolParam(name="operation", type="string", required=True, description="One of: eval, exec, run_file"),
                ToolParam(name="code", type="string", required=False, description="Python code to execute (for eval/exec)"),
                ToolParam(name="file_path", type="string", required=False, description="Path to a Python file (for run_file)"),
                ToolParam(name="args", type="string", required=False, description="Command-line arguments to pass"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        operation = params["operation"]

        try:
            if operation == "eval":
                return await self._eval_expr(params.get("code", ""))
            elif operation == "exec":
                return await self._exec_code(params.get("code", ""))
            elif operation == "run_file":
                return await self._run_file(params.get("file_path", ""), params.get("args", ""))
            else:
                return ToolResult.error_result("python", f"Unknown python operation: {operation}")
        except Exception as exc:
            return ToolResult.error_result("python", f"Python execution error: {exc}")

    async def _eval_expr(self, code: str) -> ToolResult:
        if not code:
            return ToolResult.error_result("python", "code is required")
        return await self._python_cmd("-c", f"import json; print(json.dumps(eval({code!r})))")

    async def _exec_code(self, code: str) -> ToolResult:
        if not code:
            return ToolResult.error_result("python", "code is required")
        return await self._python_cmd("-c", code)

    async def _run_file(self, file_path: str, args: str = "") -> ToolResult:
        if not file_path:
            return ToolResult.error_result("python", "file_path is required")
        cmd = [sys.executable, file_path]
        if args:
            cmd.extend(args.split())
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode == 0:
            return ToolResult(success=True, data={"output": stdout_str})
        else:
            return ToolResult.error_result("python", stderr_str or f"Python returned exit code {proc.returncode}")

    async def _python_cmd(self, *args: str) -> ToolResult:
        cmd = [sys.executable] + list(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode == 0:
            return ToolResult(success=True, data={"output": stdout_str})
        else:
            return ToolResult.error_result("python", stderr_str or f"Python returned exit code {proc.returncode}")
