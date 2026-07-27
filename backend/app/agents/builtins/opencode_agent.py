"""OpenCodeAgent — delegates SDD tasks to the OpenCode CLI via subprocess."""

from __future__ import annotations

import asyncio
import logging
import shutil
import time
from typing import Any

from app.agents.base import AgentDefinition, BaseAgent
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DEFINITION = AgentDefinition(
    agent_id="opencode",
    name="OpenCode Agent",
    role="opencode",
    description="Delegates SDD lifecycle tasks (explore, propose, spec, design, tasks, apply, verify, archive) to the OpenCode CLI.",
    system_prompt="You are an SDD delegation agent. You invoke OpenCode to execute structured development workflow tasks.",
    allowed_tools=["opencode_invoke", "subprocess_run"],
    memory_scope="session",
    permissions={"can_execute_commands": True},
    supported_models=[],
)


class OpenCodeAgent(BaseAgent):
    """Agent that delegates SDD tasks to the OpenCode CLI subprocess."""

    def __init__(self) -> None:
        super().__init__(agent_id="opencode")

    @property
    def definition(self) -> AgentDefinition:
        return _DEFINITION

    async def execute(
        self,
        task: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Build and run the OpenCode CLI command, returning a structured result."""
        settings = get_settings()
        opencode_bin = settings.opencode_bin
        timeout = settings.opencode_timeout
        default_cwd = settings.opencode_cwd

        # Task-provided cwd overrides config
        cwd = context.get("cwd", default_cwd)

        # Validate binary exists
        if not shutil.which(opencode_bin):
            return {
                "agent": self.agent_id,
                "status": "error",
                "response": f"OpenCode binary not found: {opencode_bin}",
                "duration_ms": 0,
                "exit_code": None,
                "error": "binary_not_found",
            }

        # Build command
        cmd = [opencode_bin, "--prompt", task]
        if cwd:
            cmd.extend(["--cwd", cwd])

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )
            duration_ms = int((time.monotonic() - start) * 1000)

            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            if proc.returncode != 0:
                return {
                    "agent": self.agent_id,
                    "status": "error",
                    "response": stdout or stderr,
                    "duration_ms": duration_ms,
                    "exit_code": proc.returncode,
                    "error": "non_zero_exit",
                }

            return {
                "agent": self.agent_id,
                "status": "completed",
                "response": stdout,
                "duration_ms": duration_ms,
                "exit_code": 0,
            }

        except asyncio.TimeoutError:
            duration_ms = int((time.monotonic() - start) * 1000)
            try:
                proc.kill()
                await proc.wait()
            except Exception:
                logger.debug("Failed to kill timed-out OpenCode process")
            return {
                "agent": self.agent_id,
                "status": "error",
                "response": f"OpenCode timed out after {timeout}s",
                "duration_ms": duration_ms,
                "exit_code": None,
                "error": "timeout",
            }
        except FileNotFoundError:
            return {
                "agent": self.agent_id,
                "status": "error",
                "response": f"OpenCode binary not found: {opencode_bin}",
                "duration_ms": 0,
                "exit_code": None,
                "error": "binary_not_found",
            }
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            return {
                "agent": self.agent_id,
                "status": "error",
                "response": str(exc),
                "duration_ms": duration_ms,
                "exit_code": None,
                "error": "unexpected_error",
            }

    async def health(self) -> dict[str, Any]:
        """Validate that the OpenCode binary is reachable."""
        settings = get_settings()
        binary = settings.opencode_bin
        found = shutil.which(binary) is not None
        return {
            "agent_id": self.agent_id,
            "status": "healthy" if found else "degraded",
            "binary": binary,
            "binary_found": found,
        }
