"""Tests for OpenCodeAgent and OpenCodeHandler."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.builtins.opencode_agent import OpenCodeAgent
from app.cognitive.context import CognitiveContext, IntentType
from app.cognitive.decision import (
    DecisionAction,
    OpenCodeHandler,
    default_handler_registry,
)


# ---------------------------------------------------------------------------
# OpenCodeAgent tests
# ---------------------------------------------------------------------------


class TestOpenCodeAgentDefinition:
    def test_definition_metadata(self):
        agent = OpenCodeAgent()
        d = agent.definition
        assert d.agent_id == "opencode"
        assert d.role == "opencode"
        assert "opencode_invoke" in d.allowed_tools

    def test_agent_id(self):
        agent = OpenCodeAgent()
        assert agent.agent_id == "opencode"


class TestOpenCodeAgentHealth:
    @patch("app.agents.builtins.opencode_agent.shutil.which")
    def test_health_healthy(self, mock_which):
        mock_which.return_value = "/usr/bin/opencode"
        agent = OpenCodeAgent()
        result = asyncio.get_event_loop().run_until_complete(agent.health())
        assert result["status"] == "healthy"
        assert result["binary_found"] is True

    @patch("app.agents.builtins.opencode_agent.shutil.which")
    def test_health_degraded(self, mock_which):
        mock_which.return_value = None
        agent = OpenCodeAgent()
        result = asyncio.get_event_loop().run_until_complete(agent.health())
        assert result["status"] == "degraded"
        assert result["binary_found"] is False


class TestOpenCodeAgentExecuteHappyPath:
    @pytest.mark.asyncio
    @patch("app.agents.builtins.opencode_agent.shutil.which", return_value="/usr/bin/opencode")
    @patch("app.agents.builtins.opencode_agent.get_settings")
    @patch("app.agents.builtins.opencode_agent.asyncio.create_subprocess_exec")
    async def test_execute_success(self, mock_subprocess, mock_settings, mock_which):
        # Arrange
        mock_settings.return_value = MagicMock(
            opencode_bin="opencode",
            opencode_timeout=600,
            opencode_cwd="/home/aalej/nova-core",
        )
        proc = AsyncMock()
        proc.communicate = AsyncMock(return_value=(b"Task completed successfully", b""))
        proc.returncode = 0
        mock_subprocess.return_value = proc

        agent = OpenCodeAgent()
        result = await agent.execute("run sdd spec for auth", {"cwd": "/tmp/repo"})

        # Assert command construction
        mock_subprocess.assert_called_once_with(
            "opencode", "--prompt", "run sdd spec for auth", "--cwd", "/tmp/repo",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert result["status"] == "completed"
        assert result["response"] == "Task completed successfully"
        assert result["exit_code"] == 0
        assert "duration_ms" in result
        assert result["agent"] == "opencode"

    @pytest.mark.asyncio
    @patch("app.agents.builtins.opencode_agent.shutil.which", return_value="/usr/bin/opencode")
    @patch("app.agents.builtins.opencode_agent.get_settings")
    @patch("app.agents.builtins.opencode_agent.asyncio.create_subprocess_exec")
    async def test_execute_uses_default_cwd(self, mock_subprocess, mock_settings, mock_which):
        mock_settings.return_value = MagicMock(
            opencode_bin="opencode",
            opencode_timeout=600,
            opencode_cwd="/home/aalej/nova-core",
        )
        proc = AsyncMock()
        proc.communicate = AsyncMock(return_value=(b"done", b""))
        proc.returncode = 0
        mock_subprocess.return_value = proc

        agent = OpenCodeAgent()
        result = await agent.execute("test task", {})

        # Should use default_cwd from config
        call_args = mock_subprocess.call_args
        assert "--cwd" in call_args[0]
        assert "/home/aalej/nova-core" in call_args[0]


class TestOpenCodeAgentExecuteBinaryNotFound:
    @pytest.mark.asyncio
    @patch("app.agents.builtins.opencode_agent.shutil.which", return_value=None)
    @patch("app.agents.builtins.opencode_agent.get_settings")
    async def test_execute_binary_not_found(self, mock_settings, mock_which):
        mock_settings.return_value = MagicMock(
            opencode_bin="opencode",
            opencode_timeout=600,
            opencode_cwd=None,
        )
        agent = OpenCodeAgent()
        result = await agent.execute("any task", {})

        assert result["status"] == "error"
        assert result["error"] == "binary_not_found"
        assert result["duration_ms"] == 0

    @pytest.mark.asyncio
    @patch("app.agents.builtins.opencode_agent.shutil.which", return_value="/usr/bin/opencode")
    @patch("app.agents.builtins.opencode_agent.get_settings")
    @patch("app.agents.builtins.opencode_agent.asyncio.create_subprocess_exec")
    async def test_execute_file_not_found_on_exec(self, mock_subprocess, mock_settings, mock_which):
        mock_settings.return_value = MagicMock(
            opencode_bin="opencode",
            opencode_timeout=600,
            opencode_cwd=None,
        )
        mock_subprocess.side_effect = FileNotFoundError("opencode not found")
        agent = OpenCodeAgent()
        result = await agent.execute("task", {})

        assert result["status"] == "error"
        assert result["error"] == "binary_not_found"


class TestOpenCodeAgentExecuteTimeout:
    @pytest.mark.asyncio
    @patch("app.agents.builtins.opencode_agent.shutil.which", return_value="/usr/bin/opencode")
    @patch("app.agents.builtins.opencode_agent.get_settings")
    @patch("app.agents.builtins.opencode_agent.asyncio.create_subprocess_exec")
    async def test_execute_timeout(self, mock_subprocess, mock_settings, mock_which):
        mock_settings.return_value = MagicMock(
            opencode_bin="opencode",
            opencode_timeout=1,
            opencode_cwd=None,
        )
        proc = AsyncMock()
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
        proc.kill = MagicMock()  # sync mock — kill() is sync in asyncio
        proc.wait = AsyncMock()
        mock_subprocess.return_value = proc

        agent = OpenCodeAgent()
        result = await agent.execute("long task", {})

        assert result["status"] == "error"
        assert result["error"] == "timeout"
        proc.kill.assert_called_once()


class TestOpenCodeAgentExecuteNonZeroExit:
    @pytest.mark.asyncio
    @patch("app.agents.builtins.opencode_agent.shutil.which", return_value="/usr/bin/opencode")
    @patch("app.agents.builtins.opencode_agent.get_settings")
    @patch("app.agents.builtins.opencode_agent.asyncio.create_subprocess_exec")
    async def test_execute_non_zero_exit(self, mock_subprocess, mock_settings, mock_which):
        mock_settings.return_value = MagicMock(
            opencode_bin="opencode",
            opencode_timeout=600,
            opencode_cwd=None,
        )
        proc = AsyncMock()
        proc.communicate = AsyncMock(return_value=(b"", b"Error: invalid command"))
        proc.returncode = 1
        mock_subprocess.return_value = proc

        agent = OpenCodeAgent()
        result = await agent.execute("bad task", {})

        assert result["status"] == "error"
        assert result["exit_code"] == 1
        assert result["error"] == "non_zero_exit"


class TestOpenCodeAgentExecuteUnexpectedError:
    @pytest.mark.asyncio
    @patch("app.agents.builtins.opencode_agent.shutil.which", return_value="/usr/bin/opencode")
    @patch("app.agents.builtins.opencode_agent.get_settings")
    @patch("app.agents.builtins.opencode_agent.asyncio.create_subprocess_exec")
    async def test_execute_unexpected_error(self, mock_subprocess, mock_settings, mock_which):
        mock_settings.return_value = MagicMock(
            opencode_bin="opencode",
            opencode_timeout=600,
            opencode_cwd=None,
        )
        mock_subprocess.side_effect = OSError("Permission denied")

        agent = OpenCodeAgent()
        result = await agent.execute("task", {})

        assert result["status"] == "error"
        assert result["error"] == "unexpected_error"
        assert "Permission denied" in result["response"]


# ---------------------------------------------------------------------------
# OpenCodeHandler tests
# ---------------------------------------------------------------------------


class TestOpenCodeHandler:
    @pytest.fixture
    def handler(self):
        return OpenCodeHandler()

    def test_handled_intents(self, handler):
        assert IntentType.SDD_TASK in handler.handled_intents

    @pytest.mark.asyncio
    async def test_decide_returns_correct_action(self, handler):
        context = CognitiveContext(
            raw_input="run sdd spec for auth module",
            user_id="user-123",
            intent=IntentType.SDD_TASK,
            confidence=0.9,
        )
        decision = await handler.decide(context)

        assert decision.action == DecisionAction.DELEGATE_TO_OPENCODE
        assert decision.handler_name == "opencode"
        assert decision.payload["task"] == "run sdd spec for auth module"
        assert decision.payload["user_id"] == "user-123"
        assert decision.confidence == 0.9

    @pytest.mark.asyncio
    async def test_decide_with_no_user(self, handler):
        context = CognitiveContext(
            raw_input="sdd explore the codebase",
            intent=IntentType.SDD_TASK,
        )
        decision = await handler.decide(context)

        assert decision.action == DecisionAction.DELEGATE_TO_OPENCODE
        assert decision.payload["user_id"] is None


class TestDefaultHandlerRegistry:
    def test_registry_contains_sdd_task(self):
        registry = default_handler_registry()
        assert IntentType.SDD_TASK in registry
        assert isinstance(registry[IntentType.SDD_TASK], OpenCodeHandler)


class TestIntentTypeSDDTask:
    def test_sdd_task_exists(self):
        assert hasattr(IntentType, "SDD_TASK")
        assert IntentType.SDD_TASK.value == "SDD_TASK"

    def test_sdd_task_is_member(self):
        assert IntentType.SDD_TASK in IntentType
