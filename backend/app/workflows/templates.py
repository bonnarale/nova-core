"""Workflow templates — built-in workflow templates for common patterns."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.workflows.models import WorkflowDefinition, WorkflowStep, StepType


def _make_step(step_id: str, name: str, step_type: str = "TASK", handler: str = "", depends_on: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": step_id,
        "name": name,
        "step_type": step_type,
        "handler": handler,
        "depends_on": depends_on or [],
    }


def _make_definition(name: str, description: str, steps: list[dict[str, Any]], tags: list[str] | None = None) -> WorkflowDefinition:
    return WorkflowDefinition(
        id=str(uuid4()),
        name=name,
        description=description,
        tags=tags or [],
        steps=[WorkflowStep(**s) for s in steps],
    )


def create_chat_workflow() -> WorkflowDefinition:
    return _make_definition(
        name="Chat Workflow",
        description="Standard conversational chat workflow with context retrieval and response generation.",
        tags=["chat", "conversation", "default"],
        steps=[
            _make_step("s1", "Receive Input", "TASK", "receive_input"),
            _make_step("s2", "Retrieve Context", "TASK", "retrieve_context", ["s1"]),
            _make_step("s3", "Generate Response", "TASK", "generate_response", ["s2"]),
            _make_step("s4", "Return Response", "TASK", "return_response", ["s3"]),
        ],
    )


def create_research_workflow() -> WorkflowDefinition:
    return _make_definition(
        name="Research Workflow",
        description="Multi-step research workflow with search, analysis, and synthesis.",
        tags=["research", "analysis"],
        steps=[
            _make_step("s1", "Parse Query", "TASK", "parse_query"),
            _make_step("s2", "Search Knowledge", "TASK", "search_knowledge", ["s1"]),
            _make_step("s3", "Search Web", "TASK", "search_web", ["s1"]),
            _make_step("s4", "Analyze Results", "PARALLEL", "analyze_results", ["s2", "s3"]),
            _make_step("s5", "Synthesize Findings", "TASK", "synthesize", ["s4"]),
            _make_step("s6", "Format Output", "TASK", "format_output", ["s5"]),
        ],
    )


def create_coding_workflow() -> WorkflowDefinition:
    return _make_definition(
        name="Coding Workflow",
        description="Software development workflow with code generation, review, and testing.",
        tags=["coding", "development"],
        steps=[
            _make_step("s1", "Understand Requirements", "TASK", "understand_requirements"),
            _make_step("s2", "Plan Solution", "TASK", "plan_solution", ["s1"]),
            _make_step("s3", "Generate Code", "TASK", "generate_code", ["s2"]),
            _make_step("s4", "Review Code", "TASK", "review_code", ["s3"]),
            _make_step("s5", "Run Tests", "TASK", "run_tests", ["s4"]),
            _make_step("s6", "Check Quality", "CONDITION", "check_quality", ["s5"]),
            _make_step("s7", "Deploy", "TASK", "deploy", ["s6"]),
        ],
    )


def create_planning_workflow() -> WorkflowDefinition:
    return _make_definition(
        name="Planning Workflow",
        description="Strategic planning workflow with goal decomposition and task creation.",
        tags=["planning", "strategy"],
        steps=[
            _make_step("s1", "Analyze Goal", "TASK", "analyze_goal"),
            _make_step("s2", "Decompose Goal", "TASK", "decompose_goal", ["s1"]),
            _make_step("s3", "Create Tasks", "TASK", "create_tasks", ["s2"]),
            _make_step("s4", "Prioritize Tasks", "TASK", "prioritize_tasks", ["s3"]),
            _make_step("s5", "Assign Resources", "TASK", "assign_resources", ["s4"]),
            _make_step("s6", "Generate Plan", "TASK", "generate_plan", ["s5"]),
        ],
    )


def create_goal_execution_workflow() -> WorkflowDefinition:
    return _make_definition(
        name="Goal Execution Workflow",
        description="End-to-end goal execution with monitoring and adjustment.",
        tags=["goal", "execution"],
        steps=[
            _make_step("s1", "Load Goal", "TASK", "load_goal"),
            _make_step("s2", "Check Progress", "TASK", "check_progress", ["s1"]),
            _make_step("s3", "Execute Step", "TASK", "execute_step", ["s2"]),
            _make_step("s4", "Update Progress", "TASK", "update_progress", ["s3"]),
            _make_step("s5", "Evaluate", "CONDITION", "evaluate", ["s4"]),
            _make_step("s6", "Complete Goal", "TASK", "complete_goal", ["s5"]),
        ],
    )


def create_task_automation_workflow() -> WorkflowDefinition:
    return _make_definition(
        name="Task Automation Workflow",
        description="Automated task execution with scheduling, monitoring, and retry logic.",
        tags=["task", "automation"],
        steps=[
            _make_step("s1", "Trigger Task", "TASK", "trigger_task"),
            _make_step("s2", "Validate Input", "TASK", "validate_input", ["s1"]),
            _make_step("s3", "Execute Task", "TASK", "execute_task", ["s2"]),
            _make_step("s4", "Check Result", "CONDITION", "check_result", ["s3"]),
            _make_step("s5", "Retry on Failure", "TASK", "retry_task", ["s4"]),
            _make_step("s6", "Report Status", "TASK", "report_status", ["s4"]),
        ],
    )


def create_rag_workflow() -> WorkflowDefinition:
    return _make_definition(
        name="RAG Workflow",
        description="Retrieval-Augmented Generation workflow with document retrieval and context-aware generation.",
        tags=["rag", "retrieval", "generation"],
        steps=[
            _make_step("s1", "Parse Query", "TASK", "parse_query"),
            _make_step("s2", "Embed Query", "TASK", "embed_query", ["s1"]),
            _make_step("s3", "Retrieve Documents", "TASK", "retrieve_documents", ["s2"]),
            _make_step("s4", "Rank Results", "TASK", "rank_results", ["s3"]),
            _make_step("s5", "Build Context", "TASK", "build_context", ["s4"]),
            _make_step("s6", "Generate Answer", "TASK", "generate_answer", ["s5"]),
            _make_step("s7", "Cite Sources", "TASK", "cite_sources", ["s6"]),
        ],
    )


def create_multi_agent_workflow() -> WorkflowDefinition:
    return _make_definition(
        name="Multi-Agent Collaboration Workflow",
        description="Multi-agent collaboration workflow with coordination, delegation, and synthesis.",
        tags=["multi-agent", "collaboration"],
        steps=[
            _make_step("s1", "Analyze Task", "TASK", "analyze_task"),
            _make_step("s2", "Delegate to Planner", "AGENT", "delegate_planner", ["s1"]),
            _make_step("s3", "Delegate to Researcher", "AGENT", "delegate_researcher", ["s1"]),
            _make_step("s4", "Delegate to Coder", "AGENT", "delegate_coder", ["s1"]),
            _make_step("s5", "Collect Results", "PARALLEL", "collect_results", ["s2", "s3", "s4"]),
            _make_step("s6", "Review Results", "AGENT", "review_results", ["s5"]),
            _make_step("s7", "Synthesize Output", "TASK", "synthesize_output", ["s6"]),
        ],
    )


DEFAULT_TEMPLATES: dict[str, WorkflowDefinition] = {
    "chat": create_chat_workflow(),
    "research": create_research_workflow(),
    "coding": create_coding_workflow(),
    "planning": create_planning_workflow(),
    "goal_execution": create_goal_execution_workflow(),
    "task_automation": create_task_automation_workflow(),
    "rag": create_rag_workflow(),
    "multi_agent": create_multi_agent_workflow(),
}


def get_template(name: str) -> WorkflowDefinition | None:
    return DEFAULT_TEMPLATES.get(name)


def list_templates() -> list[dict[str, Any]]:
    return [
        {"name": name, "description": defn.description, "tags": defn.tags}
        for name, defn in DEFAULT_TEMPLATES.items()
    ]
