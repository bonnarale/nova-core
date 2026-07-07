"""Kernel execution engine - the core orchestrator for NOVA CORE."""

import asyncio
import logging
from typing import Any, Optional

from app.core.config import Settings
from app.kernel.config import get_kernel_settings, KernelSettings
from app.kernel.context import ExecutionContext, set_current_context
from app.kernel.events import EventType, KernelEvent, emit
from app.kernel.registry import get_agent, get_provider
from app.kernel.router import route_task
from app.kernel.session import create_session, get_session, Session

logger = logging.getLogger(__name__)


class KernelEngine:
    """The main kernel execution engine for NOVA CORE.

    This engine orchestrates agent execution, manages sessions,
    and provides the core runtime for the AI operating system.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._kernel_settings: KernelSettings = get_kernel_settings()
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(
            self._kernel_settings.max_concurrent_tasks
        )
        self._running: bool = False
        logger.info("Kernel engine initialized with max_concurrent_tasks=%d", self._kernel_settings.max_concurrent_tasks)

    @property
    def settings(self) -> Settings:
        """Get the application settings."""
        return self._settings

    @property
    def kernel_settings(self) -> KernelSettings:
        """Get the kernel-specific settings."""
        return self._kernel_settings

    async def start(self) -> None:
        """Start the kernel engine."""
        self._running = True
        logger.info("Kernel engine starting")
        emit(KernelEvent.create(event_type=EventType.AGENT_STARTED, agent_id="kernel"))

    async def stop(self) -> None:
        """Stop the kernel engine."""
        self._running = False
        logger.info("Kernel engine stopping")
        emit(KernelEvent.create(event_type=EventType.AGENT_STOPPED, agent_id="kernel"))

    @property
    def is_running(self) -> bool:
        """Check if the kernel is running."""
        return self._running

    async def execute_task(
        self,
        task: str,
        agent_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        session_id: Optional[Any] = None,
        context: Optional[ExecutionContext] = None,
    ) -> dict[str, Any]:
        """Execute a task through the kernel.

        Args:
            task: The task description or input.
            agent_id: Optional agent ID to execute the task.
            tool_id: Optional tool ID to execute the task.
            session_id: Optional session ID to associate with.
            context: Optional execution context.

        Returns:
            Task execution result.
        """
        async with self._semaphore:
            if context is None:
                context = ExecutionContext()

            set_current_context(context)

            if session_id:
                session = get_session(session_id)
                if session:
                    context = session.get_context()
                    context.set("task", task)

            return await route_task(
                task=task,
                agent_id=agent_id,
                tool_id=tool_id,
                context=context,
            )

    async def run_agent(
        self,
        agent_id: str,
        task: str,
        session_id: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Run a task with a specific agent.

        Args:
            agent_id: The agent to run.
            task: The task to execute.
            session_id: Optional session ID.

        Returns:
            Agent execution result.
        """
        return await self.execute_task(
            task=task,
            agent_id=agent_id,
            session_id=session_id,
        )

    def get_llm_provider(self) -> Optional[Any]:
        """Get the LLM provider from registry."""
        return get_provider("llm")

    def get_embedding_provider(self) -> Optional[Any]:
        """Get the embedding provider from registry."""
        return get_provider("embedding")


# Global kernel instance
_kernel: Optional[KernelEngine] = None


def get_kernel(settings: Optional[Settings] = None) -> KernelEngine:
    """Get or create the global kernel instance."""
    global _kernel
    if _kernel is None:
        if settings is None:
            settings = Settings()
        _kernel = KernelEngine(settings)
    return _kernel