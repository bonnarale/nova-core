"""GitTool — run git operations via subprocess."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class GitTool(Tool):
    """Execute git commands (clone, status, log, diff, checkout, etc.)."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="git",
            description="Execute git commands — clone, status, log, diff, checkout, add, commit, push, pull, branch.",
            category="devops",
            timeout_default=60.0,
            retry_default=1,
            permission_level="write",
            parameters=[
                ToolParam(name="operation", type="string", required=True, description="One of: clone, status, log, diff, checkout, add, commit, push, pull, branch, init, remote"),
                ToolParam(name="repo_path", type="string", required=False, description="Path to the local repository"),
                ToolParam(name="url", type="string", required=False, description="Remote URL (for clone/push/pull)"),
                ToolParam(name="branch", type="string", required=False, description="Branch name"),
                ToolParam(name="message", type="string", required=False, description="Commit message"),
                ToolParam(name="args", type="string", required=False, description="Additional git arguments"),
                ToolParam(name="paths", type="list", required=False, description="File paths for add/checkout"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        operation = params["operation"]
        repo_path = params.get("repo_path", os.getcwd())

        if not os.path.isdir(repo_path):
            return ToolResult.error_result("git", f"Repository path not found: {repo_path}")

        try:
            if operation == "status":
                return await self._git_cmd(repo_path, "status")
            elif operation == "log":
                return await self._git_log(repo_path, params.get("args", "--oneline -10"))
            elif operation == "diff":
                return await self._git_cmd(repo_path, "diff", params.get("args", ""))
            elif operation == "checkout":
                return await self._git_checkout(repo_path, params)
            elif operation == "add":
                return await self._git_add(repo_path, params)
            elif operation == "commit":
                return await self._git_commit(repo_path, params)
            elif operation == "branch":
                return await self._git_cmd(repo_path, "branch", params.get("args", "-a"))
            elif operation == "pull":
                return await self._git_cmd(repo_path, "pull", params.get("args", ""))
            elif operation == "push":
                return await self._git_cmd(repo_path, "push", params.get("args", ""))
            elif operation == "clone":
                return await self._git_clone(params)
            elif operation == "init":
                return await self._git_init(repo_path)
            elif operation == "remote":
                return await self._git_cmd(repo_path, "remote -v")
            else:
                return ToolResult.error_result("git", f"Unknown git operation: {operation}")
        except Exception as exc:
            return ToolResult.error_result("git", f"Git error: {exc}")

    async def _git_cmd(self, repo_path: str, *parts: str) -> ToolResult:
        cmd = ["git"] + [p for p in parts if p]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode == 0:
            return ToolResult(success=True, data={"command": " ".join(cmd), "output": stdout_str})
        else:
            return ToolResult.error_result("git", stderr_str or f"git returned exit code {proc.returncode}")

    async def _git_log(self, repo_path: str, args: str) -> ToolResult:
        cmd = ["git", "log"] + (args.split() if args else [])
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return ToolResult(success=True, data={"command": "git log", "output": stdout.decode("utf-8", errors="replace").strip()})
        return ToolResult.error_result("git", stderr.decode("utf-8", errors="replace").strip())

    async def _git_checkout(self, repo_path: str, params: dict[str, Any]) -> ToolResult:
        branch = params.get("branch", "")
        paths = params.get("paths", [])
        if branch:
            return await self._git_cmd(repo_path, "checkout", branch)
        elif paths:
            return await self._git_cmd(repo_path, "checkout", "--", *paths)
        return ToolResult.error_result("git", "Provide either 'branch' or 'paths' for checkout")

    async def _git_add(self, repo_path: str, params: dict[str, Any]) -> ToolResult:
        paths = params.get("paths", ["."])
        return await self._git_cmd(repo_path, "add", *paths)

    async def _git_commit(self, repo_path: str, params: dict[str, Any]) -> ToolResult:
        msg = params.get("message", "update")
        return await self._git_cmd(repo_path, "commit", "-m", msg)

    async def _git_clone(self, params: dict[str, Any]) -> ToolResult:
        url = params.get("url", "")
        if not url:
            return ToolResult.error_result("git", "URL is required for clone")
        dest = params.get("repo_path", "")
        cmd = ["git", "clone", url]
        if dest:
            cmd.append(dest)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            return ToolResult(success=True, data={"command": " ".join(cmd), "output": stdout.decode("utf-8", errors="replace").strip()})
        return ToolResult.error_result("git", stderr.decode("utf-8", errors="replace").strip())

    async def _git_init(self, repo_path: str) -> ToolResult:
        return await self._git_cmd(repo_path, "init")
