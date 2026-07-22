"""DockerTool — run Docker commands via subprocess."""

from __future__ import annotations

import asyncio
from typing import Any

from app.tools.base import Tool, ToolParam, ToolSpec
from app.tools.result import ToolResult


class DockerTool(Tool):
    """Execute Docker commands — exec, run, ps, logs, etc."""

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name="docker",
            description="Execute Docker commands — run, exec, ps, logs, stop, build, pull, images.",
            category="devops",
            timeout_default=120.0,
            retry_default=0,
            permission_level="admin",
            parameters=[
                ToolParam(name="operation", type="string", required=True, description="One of: exec_run, run_container, list_containers, list_images, logs, stop, build, pull"),
                ToolParam(name="image", type="string", required=False, description="Docker image name"),
                ToolParam(name="command", type="string", required=False, description="Command to execute"),
                ToolParam(name="container_id", type="string", required=False, description="Container ID or name"),
                ToolParam(name="workdir", type="string", required=False, description="Working directory inside container"),
                ToolParam(name="env", type="dict", required=False, description="Environment variables"),
                ToolParam(name="args", type="string", required=False, description="Additional Docker arguments"),
            ],
        )

    async def run(self, params: dict[str, Any]) -> ToolResult:
        operation = params["operation"]

        try:
            if operation == "exec_run":
                return await self._exec_run(params)
            elif operation == "run_container":
                return await self._run_container(params)
            elif operation == "list_containers":
                return await self._list_containers(params.get("args", ""))
            elif operation == "list_images":
                return await self._list_images()
            elif operation == "logs":
                return await self._logs(params)
            elif operation == "stop":
                return await self._stop(params)
            elif operation == "build":
                return await self._build(params)
            elif operation == "pull":
                return await self._pull(params)
            else:
                return ToolResult.error_result("docker", f"Unknown docker operation: {operation}")
        except Exception as exc:
            return ToolResult.error_result("docker", f"Docker error: {exc}")

    async def _exec_run(self, params: dict[str, Any]) -> ToolResult:
        cid = params.get("container_id", "")
        cmd = params.get("command", "")
        if not cid or not cmd:
            return ToolResult.error_result("docker", "container_id and command are required")
        return await self._docker_cmd("exec", cid, *cmd.split())

    async def _run_container(self, params: dict[str, Any]) -> ToolResult:
        image = params.get("image", "")
        if not image:
            return ToolResult.error_result("docker", "image is required")
        cmd_parts = ["run", "-d"]
        if params.get("workdir"):
            cmd_parts.extend(["-w", params["workdir"]])
        env = params.get("env", {})
        for key, val in env.items():
            cmd_parts.extend(["-e", f"{key}={val}"])
        cmd_parts.append(image)
        command = params.get("command", "")
        if command:
            cmd_parts.extend(command.split())
        return await self._docker_cmd(*cmd_parts)

    async def _list_containers(self, args: str = "") -> ToolResult:
        cmd = ["ps"]
        if args:
            cmd.append(args)
        return await self._docker_cmd(*cmd)

    async def _list_images(self) -> ToolResult:
        return await self._docker_cmd("images")

    async def _logs(self, params: dict[str, Any]) -> ToolResult:
        cid = params.get("container_id", "")
        if not cid:
            return ToolResult.error_result("docker", "container_id is required")
        return await self._docker_cmd("logs", "--tail", "100", cid)

    async def _stop(self, params: dict[str, Any]) -> ToolResult:
        cid = params.get("container_id", "")
        if not cid:
            return ToolResult.error_result("docker", "container_id is required")
        return await self._docker_cmd("stop", cid)

    async def _build(self, params: dict[str, Any]) -> ToolResult:
        path = params.get("workdir", ".")
        tag = params.get("image", "")
        cmd = ["build", path]
        if tag:
            cmd.extend(["-t", tag])
        return await self._docker_cmd(*cmd)

    async def _pull(self, params: dict[str, Any]) -> ToolResult:
        image = params.get("image", "")
        if not image:
            return ToolResult.error_result("docker", "image is required")
        return await self._docker_cmd("pull", image)

    async def _docker_cmd(self, *args: str) -> ToolResult:
        cmd = ["docker"] + list(args)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode == 0:
            return ToolResult(success=True, data={"command": " ".join(cmd), "output": stdout_str})
        else:
            return ToolResult.error_result("docker", stderr_str or f"docker returned exit code {proc.returncode}")
