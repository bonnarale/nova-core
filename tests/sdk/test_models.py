from __future__ import annotations

import json
import pytest
from nova_core_sdk.models import (
    ChatRequestModel,
    CreateAgentRequest,
    UpdateAgentRequest,
    DispatchRequest,
    CoordinateRequest,
    ExecuteRequest,
    CreateGoalRequest,
    UpdateGoalRequest,
    CreateTaskRequest,
    UpdateTaskRequest,
    AdvanceStepRequest,
    RAGQueryRequest,
    RAGRetrieveRequest,
    RAGIndexDocRequest,
    RAGReindexRequest,
    RegisterToolRequest,
    ExecuteToolRequest,
    WorkflowCreate,
    WorkflowExecutionCreate,
    WorkflowExecutionAction,
    CreateJobRequest,
    PublishEventRequest,
    EntityCreate,
    EntityUpdate,
    RelationshipCreate,
    VectorRecord,
    VectorMemoryQuery,
    RegisterPluginRequest,
    ExecutePluginRequest,
    ExtractKnowledgeRequest,
    SearchLearningRequest,
    ConsolidateRequest,
)


class TestChatModels:
    def test_chat_request_required_fields(self) -> None:
        m = ChatRequestModel(model="gpt-4", messages=[{"role": "user", "content": "hi"}])
        assert m.model == "gpt-4"
        assert len(m.messages) == 1

    def test_chat_request_defaults(self) -> None:
        m = ChatRequestModel(model="m", messages=[])
        assert m.use_cache is True
        assert m.stream is False
        assert m.temperature is None


class TestAgentModels:
    def test_create_agent_minimal(self) -> None:
        m = CreateAgentRequest(id="a1", name="Agent", role="analyst")
        assert m.id == "a1"
        assert m.system_prompt == ""
        assert m.allowed_tools == []

    def test_update_agent_all_optional(self) -> None:
        m = UpdateAgentRequest()
        assert m.name is None
        assert m.status is None


class TestGoalModels:
    def test_create_goal_defaults(self) -> None:
        m = CreateGoalRequest(title="Goal")
        assert m.priority == 3
        assert m.description is None

    def test_update_goal(self) -> None:
        m = UpdateGoalRequest(status="completed", progress=100)
        assert m.status == "completed"
        assert m.progress == 100


class TestTaskModels:
    def test_create_task(self) -> None:
        m = CreateTaskRequest(goal="Build it")
        assert m.goal == "Build it"
        assert m.plan is None

    def test_advance_step(self) -> None:
        m = AdvanceStepRequest(artifacts={"output": "result"})
        assert m.artifacts == {"output": "result"}


class TestRAGModels:
    def test_rag_query_defaults(self) -> None:
        m = RAGQueryRequest(query="test")
        assert m.top_k == 10
        assert m.threshold == 0.0
        assert m.filters == []

    def test_rag_index_defaults(self) -> None:
        m = RAGIndexDocRequest(content="text")
        assert m.chunk_size == 512
        assert m.chunk_overlap == 50

    def test_rag_reindex(self) -> None:
        m = RAGReindexRequest(reindex_all=True)
        assert m.document_ids == []


class TestToolModels:
    def test_register_tool_defaults(self) -> None:
        m = RegisterToolRequest(name="mytool")
        assert m.category == "general"
        assert m.timeout == 30.0

    def test_execute_tool(self) -> None:
        m = ExecuteToolRequest(params={"x": 1}, agent_id="a1")
        assert m.params == {"x": 1}


class TestWorkflowModels:
    def test_workflow_create_defaults(self) -> None:
        m = WorkflowCreate(name="wf")
        assert m.version == "1.0.0"
        assert m.steps == []

    def test_workflow_execution_create(self) -> None:
        m = WorkflowExecutionCreate(workflow_id="wf-1")
        assert m.input == {}

    def test_workflow_action(self) -> None:
        m = WorkflowExecutionAction(action="pause")
        assert m.action == "pause"


class TestSchedulerModels:
    def test_create_job_defaults(self) -> None:
        m = CreateJobRequest(name="job1")
        assert m.enabled is True
        assert m.params == {}


class TestEventModels:
    def test_publish_event(self) -> None:
        m = PublishEventRequest(event_type="test.event")
        assert m.payload == {}


class TestKGModels:
    def test_entity_create(self) -> None:
        m = EntityCreate(type="PERSON", name="John")
        assert m.confidence == 1.0
        assert m.source == "manual"

    def test_relationship_create(self) -> None:
        m = RelationshipCreate(source_id="s1", target_id="t1", type="knows")
        assert m.weight == 1.0


class TestVectorModels:
    def test_vector_record(self) -> None:
        m = VectorRecord(content="text", embedding=[0.1, 0.2, 0.3])
        assert len(m.embedding) == 3

    def test_vector_query(self) -> None:
        m = VectorMemoryQuery(query="search")
        assert m.top_k == 10


class TestPluginModels:
    def test_register_plugin(self) -> None:
        m = RegisterPluginRequest(name="myplugin")
        assert m.version == "1.0.0"
        assert m.plugin_type == "extension"

    def test_execute_plugin(self) -> None:
        m = ExecutePluginRequest(operation="run")
        assert m.params == {}
