from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any


class ConversationSessionBuilder:
    def __init__(self) -> None:
        self._id = str(uuid.uuid4())
        self._user_id = "test-user"
        self._created_at = datetime.now(timezone.utc)
        self._updated_at = datetime.now(timezone.utc)
        self._status = "active"
        self._metadata: dict[str, Any] = {}

    def with_id(self, val: str) -> ConversationSessionBuilder:
        self._id = val
        return self

    def with_user_id(self, val: str) -> ConversationSessionBuilder:
        self._user_id = val
        return self

    def with_status(self, val: str) -> ConversationSessionBuilder:
        self._status = val
        return self

    def with_metadata(self, val: dict[str, Any]) -> ConversationSessionBuilder:
        self._metadata = val
        return self

    def build_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "user_id": self._user_id,
            "created_at": self._created_at,
            "updated_at": self._updated_at,
            "status": self._status,
            "metadata": self._metadata,
        }

    def build(self) -> Any:
        from app.db.models import ConversationSession

        d = self.build_dict()
        return d


class ConversationMessageBuilder:
    def __init__(self) -> None:
        self._id = str(uuid.uuid4())
        self._session_id = str(uuid.uuid4())
        self._role = "user"
        self._content = "Test message"
        self._created_at = datetime.now(timezone.utc)
        self._metadata: dict[str, Any] = {}

    def with_session_id(self, val: str) -> ConversationMessageBuilder:
        self._session_id = val
        return self

    def with_role(self, val: str) -> ConversationMessageBuilder:
        self._role = val
        return self

    def with_content(self, val: str) -> ConversationMessageBuilder:
        self._content = val
        return self

    def with_metadata(self, val: dict[str, Any]) -> ConversationMessageBuilder:
        self._metadata = val
        return self

    def build_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "session_id": self._session_id,
            "role": self._role,
            "content": self._content,
            "created_at": self._created_at,
            "metadata": self._metadata,
        }

    def build(self) -> Any:
        from app.db.models import ConversationMessage

        d = self.build_dict()
        return d


class UserProfileBuilder:
    def __init__(self) -> None:
        self._id = str(uuid.uuid4())
        self._user_id = "test-user"
        self._display_name = "Test User"
        self._preferences: dict[str, Any] = {}
        self._created_at = datetime.now(timezone.utc)

    def with_user_id(self, val: str) -> UserProfileBuilder:
        self._user_id = val
        return self

    def with_display_name(self, val: str) -> UserProfileBuilder:
        self._display_name = val
        return self

    def with_preferences(self, val: dict[str, Any]) -> UserProfileBuilder:
        self._preferences = val
        return self

    def build_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "user_id": self._user_id,
            "display_name": self._display_name,
            "preferences": self._preferences,
            "created_at": self._created_at,
        }

    def build(self) -> Any:
        from app.db.models import UserProfile

        d = self.build_dict()
        return d


class GoalBuilder:
    def __init__(self) -> None:
        self._id = str(uuid.uuid4())
        self._name = "test-goal"
        self._description = "A test goal"
        self._status = "pending"
        self._priority = "medium"
        self._created_at = datetime.now(timezone.utc)
        self._parent_id: str | None = None
        self._metadata: dict[str, Any] = {}

    def with_name(self, val: str) -> GoalBuilder:
        self._name = val
        return self

    def with_description(self, val: str) -> GoalBuilder:
        self._description = val
        return self

    def with_status(self, val: str) -> GoalBuilder:
        self._status = val
        return self

    def with_priority(self, val: str) -> GoalBuilder:
        self._priority = val
        return self

    def with_parent_id(self, val: str | None) -> GoalBuilder:
        self._parent_id = val
        return self

    def with_metadata(self, val: dict[str, Any]) -> GoalBuilder:
        self._metadata = val
        return self

    def build_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "name": self._name,
            "description": self._description,
            "status": self._status,
            "priority": self._priority,
            "created_at": self._created_at,
            "parent_id": self._parent_id,
            "metadata": self._metadata,
        }

    def build(self) -> Any:
        from app.db.models import Goal

        d = self.build_dict()
        return d


class TaskBuilder:
    def __init__(self) -> None:
        self._id = str(uuid.uuid4())
        self._goal_id = str(uuid.uuid4())
        self._name = "test-task"
        self._description = "A test task"
        self._status = "pending"
        self._priority = "medium"
        self._assignee: str | None = None
        self._created_at = datetime.now(timezone.utc)
        self._metadata: dict[str, Any] = {}

    def with_goal_id(self, val: str) -> TaskBuilder:
        self._goal_id = val
        return self

    def with_name(self, val: str) -> TaskBuilder:
        self._name = val
        return self

    def with_status(self, val: str) -> TaskBuilder:
        self._status = val
        return self

    def with_priority(self, val: str) -> TaskBuilder:
        self._priority = val
        return self

    def with_assignee(self, val: str | None) -> TaskBuilder:
        self._assignee = val
        return self

    def with_metadata(self, val: dict[str, Any]) -> TaskBuilder:
        self._metadata = val
        return self

    def build_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "goal_id": self._goal_id,
            "name": self._name,
            "description": self._description,
            "status": self._status,
            "priority": self._priority,
            "assignee": self._assignee,
            "created_at": self._created_at,
            "metadata": self._metadata,
        }

    def build(self) -> Any:
        from app.db.models import Task

        d = self.build_dict()
        return d


class WorkflowBuilder:
    def __init__(self) -> None:
        self._id = str(uuid.uuid4())
        self._name = "test-workflow"
        self._description = "A test workflow"
        self._steps: list[dict[str, Any]] = []
        self._status = "draft"
        self._version = "1.0.0"
        self._created_at = datetime.now(timezone.utc)

    def with_name(self, val: str) -> WorkflowBuilder:
        self._name = val
        return self

    def with_description(self, val: str) -> WorkflowBuilder:
        self._description = val
        return self

    def with_steps(self, val: list[dict[str, Any]]) -> WorkflowBuilder:
        self._steps = val
        return self

    def add_step(self, step_id: str, step_type: str = "action", **kwargs: Any) -> WorkflowBuilder:
        step: dict[str, Any] = {"id": step_id, "type": step_type}
        step.update(kwargs)
        self._steps.append(step)
        return self

    def with_status(self, val: str) -> WorkflowBuilder:
        self._status = val
        return self

    def with_version(self, val: str) -> WorkflowBuilder:
        self._version = val
        return self

    def build_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "name": self._name,
            "description": self._description,
            "steps": self._steps,
            "status": self._status,
            "version": self._version,
            "created_at": self._created_at,
        }

    def build(self) -> Any:
        from app.db.models import Workflow

        d = self.build_dict()
        return d


class WorkflowExecutionBuilder:
    def __init__(self) -> None:
        self._id = str(uuid.uuid4())
        self._workflow_id = str(uuid.uuid4())
        self._status = "running"
        self._started_at = datetime.now(timezone.utc)
        self._completed_at: datetime | None = None
        self._results: dict[str, Any] = {}
        self._error: str | None = None

    def with_workflow_id(self, val: str) -> WorkflowExecutionBuilder:
        self._workflow_id = val
        return self

    def with_status(self, val: str) -> WorkflowExecutionBuilder:
        self._status = val
        return self

    def with_results(self, val: dict[str, Any]) -> WorkflowExecutionBuilder:
        self._results = val
        return self

    def with_error(self, val: str | None) -> WorkflowExecutionBuilder:
        self._error = val
        return self

    def build_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "workflow_id": self._workflow_id,
            "status": self._status,
            "started_at": self._started_at,
            "completed_at": self._completed_at,
            "results": self._results,
            "error": self._error,
        }

    def build(self) -> Any:
        from app.db.models import WorkflowExecution

        d = self.build_dict()
        return d


class PluginBuilder:
    def __init__(self) -> None:
        self._name = "test-plugin"
        self._version = "1.0.0"
        self._description = "A test plugin"
        self._author = "test"
        self._plugin_type = "utility"
        self._state = "loaded"
        self._enabled = True
        self._permissions: list[str] = []
        self._dependencies: list[str] = []

    def with_name(self, val: str) -> PluginBuilder:
        self._name = val
        return self

    def with_version(self, val: str) -> PluginBuilder:
        self._version = val
        return self

    def with_type(self, val: str) -> PluginBuilder:
        self._plugin_type = val
        return self

    def with_state(self, val: str) -> PluginBuilder:
        self._state = val
        return self

    def with_permissions(self, val: list[str]) -> PluginBuilder:
        self._permissions = val
        return self

    def with_dependencies(self, val: list[str]) -> PluginBuilder:
        self._dependencies = val
        return self

    def build_dict(self) -> dict[str, Any]:
        return {
            "name": self._name,
            "version": self._version,
            "description": self._description,
            "author": self._author,
            "type": self._plugin_type,
            "state": self._state,
            "enabled": self._enabled,
            "permissions": self._permissions,
            "dependencies": self._dependencies,
        }

    def build(self) -> Any:
        from app.plugins.base import Plugin

        d = self.build_dict()
        return d


class EventBuilder:
    def __init__(self) -> None:
        self._id = str(uuid.uuid4())
        self._type = "conversation.created"
        self._source = "test"
        self._payload: dict[str, Any] = {}
        self._priority = "normal"
        self._status = "created"
        self._timestamp = datetime.now(timezone.utc)

    def with_type(self, val: str) -> EventBuilder:
        self._type = val
        return self

    def with_source(self, val: str) -> EventBuilder:
        self._source = val
        return self

    def with_payload(self, val: dict[str, Any]) -> EventBuilder:
        self._payload = val
        return self

    def with_priority(self, val: str) -> EventBuilder:
        self._priority = val
        return self

    def with_status(self, val: str) -> EventBuilder:
        self._status = val
        return self

    def build_dict(self) -> dict[str, Any]:
        return {
            "id": self._id,
            "type": self._type,
            "source": self._source,
            "payload": self._payload,
            "priority": self._priority,
            "status": self._status,
            "timestamp": self._timestamp,
        }

    def build(self) -> Any:
        from app.events.schemas import Event, EventType, EventPriority, EventStatus

        d = self.build_dict()
        try:
            d["type"] = EventType(d["type"])
        except ValueError:
            d["type"] = EventType.CONVERSATION_CREATED
        try:
            d["priority"] = EventPriority(d["priority"])
        except ValueError:
            d["priority"] = EventPriority.NORMAL
        try:
            d["status"] = EventStatus(d["status"])
        except ValueError:
            d["status"] = EventStatus.CREATED
        return Event(**d)
