from __future__ import annotations

import time
from typing import Any

import httpx

from nova_core_sdk.auth import AuthProvider, create_auth
from nova_core_sdk.configuration import Configuration
from nova_core_sdk.exceptions import (
    NovaAPIError,
    NovaAuthError,
    NovaConnectionError,
    NovaRateLimitError,
    NovaServerError,
    NovaTimeoutError,
    NovaValidationError,
)
from nova_core_sdk.hooks import HookManager
from nova_core_sdk.middleware import Middleware, TelemetryMiddleware
from nova_core_sdk.pagination import AsyncPageIterator
from nova_core_sdk.retry import RetryHandler
from nova_core_sdk.streaming import AsyncStreamProcessor
from nova_core_sdk.telemetry import TelemetryCollector
from nova_core_sdk.websocket import AsyncWebSocketClient


class NovaClient:
    def __init__(self, config: Configuration | None = None, **kwargs: Any) -> None:
        self._config = config or Configuration(**kwargs)
        self._auth: AuthProvider = create_auth(self._config)
        self._middleware = Middleware()
        self._hooks = HookManager()
        self._retry = RetryHandler(
            max_retries=self._config.max_retries,
            base_delay=self._config.retry_base_delay,
            max_delay=self._config.retry_max_delay,
            backoff=self._config.retry_backoff,
        )
        self._telemetry = TelemetryCollector(enabled=self._config.telemetry_enabled)
        self._client = httpx.AsyncClient(
            base_url=self._config.base_url,
            timeout=self._config.timeout,
            headers=self._config.get_default_headers(),
            verify=self._config.verify_ssl,
        )

    @property
    def agents(self) -> AgentsService:
        return AgentsService(self)

    @property
    def models(self) -> ModelsService:
        return ModelsService(self)

    @property
    def memory(self) -> MemoryService:
        return MemoryService(self)

    @property
    def kernel(self) -> KernelService:
        return KernelService(self)

    @property
    def goals(self) -> GoalsService:
        return GoalsService(self)

    @property
    def tasks(self) -> TasksService:
        return TasksService(self)

    @property
    def workflows(self) -> WorkflowsService:
        return WorkflowsService(self)

    @property
    def scheduler(self) -> SchedulerService:
        return SchedulerService(self)

    @property
    def tools(self) -> ToolsService:
        return ToolsService(self)

    @property
    def rag(self) -> RAGService:
        return RAGService(self)

    @property
    def vector_memory(self) -> VectorMemoryService:
        return VectorMemoryService(self)

    @property
    def events(self) -> EventsService:
        return EventsService(self)

    @property
    def plugins(self) -> PluginsService:
        return PluginsService(self)

    @property
    def learning(self) -> LearningService:
        return LearningService(self)

    @property
    def knowledge_graph(self) -> KnowledgeGraphService:
        return KnowledgeGraphService(self)

    @property
    def observability(self) -> ObservabilityService:
        return ObservabilityService(self)

    @property
    def deployment(self) -> DeploymentService:
        return DeploymentService(self)

    @property
    def scaling(self) -> ScalingService:
        return ScalingService(self)

    @property
    def security(self) -> SecurityService:
        return SecurityService(self)

    @property
    def enterprise(self) -> EnterpriseService:
        return EnterpriseService(self)

    @property
    def profile(self) -> ProfileService:
        return ProfileService(self)

    @property
    def database(self) -> DatabaseService:
        return DatabaseService(self)

    @property
    def performance(self) -> PerformanceService:
        return PerformanceService(self)

    @property
    def resilience(self) -> ResilienceService:
        return ResilienceService(self)

    @property
    def autonomy(self) -> AutonomyService:
        return AutonomyService(self)

    async def _request(
        self,
        method: str,
        path: str,
        json_data: Any = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        req_headers = {**self._config.get_default_headers(), **(headers or {})}
        self._hooks.emit("pre_request", method, path, req_headers, json_data)
        context = self._middleware.process_request(method, path, req_headers, json_data)
        url = context.get("url", path)

        start = time.time()
        span = self._telemetry.start_span(f"{method} {url}")
        try:
            response = await self._client.request(
                method,
                url,
                json=json_data,
                params=params,
                headers=context.get("headers", req_headers),
            )
            latency_ms = (time.time() - start) * 1000
            self._telemetry.record_request(url, latency_ms, response.status_code)
            self._telemetry.end_span(span)

            if response.status_code >= 400:
                self._handle_error(response, url)

            result = response.json() if response.content else {}
            self._hooks.emit("post_request", result)
            return result
        except httpx.TimeoutException as exc:
            self._telemetry.end_span(span, "error")
            raise NovaTimeoutError(f"Request timed out: {exc}") from exc
        except httpx.ConnectError as exc:
            self._telemetry.end_span(span, "error")
            raise NovaConnectionError(f"Connection failed: {exc}") from exc

    def _handle_error(self, response: httpx.Response, url: str) -> None:
        try:
            body = response.json()
        except Exception:
            body = {"detail": response.text}

        message = body.get("detail", body.get("message", f"HTTP {response.status_code}"))
        status = response.status_code

        if status == 401:
            raise NovaAuthError(message, status_code=status, response=body)
        if status == 422:
            errors = body.get("errors", [])
            raise NovaValidationError(message, errors=errors, status_code=status, response=body)
        if status == 429:
            retry_after = None
            ra_header = response.headers.get("retry-after")
            if ra_header:
                try:
                    retry_after = float(ra_header)
                except ValueError:
                    pass
            raise NovaRateLimitError(message, retry_after=retry_after, status_code=status, response=body)
        if status >= 500:
            raise NovaServerError(message, status_code=status, response=body)
        raise NovaAPIError(message, status_code=status, response=body)

    async def get(self, path: str, **kwargs: Any) -> Any:
        return await self._request("GET", path, **kwargs)

    async def post(self, path: str, json_data: Any = None, **kwargs: Any) -> Any:
        return await self._request("POST", path, json_data=json_data, **kwargs)

    async def put(self, path: str, json_data: Any = None, **kwargs: Any) -> Any:
        return await self._request("PUT", path, json_data=json_data, **kwargs)

    async def patch(self, path: str, json_data: Any = None, **kwargs: Any) -> Any:
        return await self._request("PATCH", path, json_data=json_data, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Any:
        return await self._request("DELETE", path, **kwargs)

    async def stream_chat(self, path: str, json_data: Any = None) -> AsyncStreamProcessor:
        req_headers = {**self._config.get_default_headers()}
        req_headers["Accept"] = "text/event-stream"
        response = await self._client.send(
            self._client.build_request("POST", path, json=json_data, headers=req_headers),
            stream=True,
        )
        return AsyncStreamProcessor(response)

    def websocket(self, path: str) -> AsyncWebSocketClient:
        ws_url = self._config.base_url.replace("http", "ws") + path
        return AsyncWebSocketClient(ws_url, self._config.get_default_headers())

    async def paginate(
        self, method: str, path: str, params: dict[str, Any] | None = None, page_size: int = 20
    ) -> AsyncPageIterator:
        return AsyncPageIterator(self, method, path, params, page_size)

    async def health(self) -> dict[str, Any]:
        return await self.get("/health")

    async def close(self) -> None:
        await self._client.aclose()


class AgentsService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def list(self) -> dict[str, Any]:
        return await self._client.get("/agents")

    async def get(self, agent_id: str) -> dict[str, Any]:
        return await self._client.get(f"/agents/{agent_id}")

    async def create(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/agents", json_data=kwargs)

    async def update(self, agent_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._client.patch(f"/agents/{agent_id}", json_data=kwargs)

    async def delete(self, agent_id: str) -> None:
        await self._client.delete(f"/agents/{agent_id}")

    async def register(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/agents/register", json_data=kwargs)

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/agents/health")

    async def capabilities(self) -> dict[str, Any]:
        return await self._client.get("/agents/capabilities")

    async def dispatch(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/agents/runtime/dispatch", json_data=kwargs)

    async def coordinate(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/agents/runtime/coordinate", json_data=kwargs)

    async def runtime_metrics(self) -> dict[str, Any]:
        return await self._client.get("/agents/runtime/metrics")

    async def runtime_traces(self) -> dict[str, Any]:
        return await self._client.get("/agents/runtime/traces")


class ModelsService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def chat(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/models/chat", json_data=kwargs)

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/models/health")

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/models/metrics")

    async def list_models(self, provider: str | None = None) -> dict[str, Any]:
        params = {"provider": provider} if provider else None
        return await self._client.get("/models/list", params=params)

    async def providers(self) -> dict[str, Any]:
        return await self._client.get("/models/providers")

    async def cache_stats(self) -> dict[str, Any]:
        return await self._client.get("/models/cache/stats")

    async def clear_cache(self) -> dict[str, Any]:
        return await self._client.delete("/models/cache")

    async def traces(self, limit: int = 50) -> dict[str, Any]:
        return await self._client.get("/models/traces", params={"limit": limit})


class MemoryService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def get(self, session_id: str) -> dict[str, Any]:
        return await self._client.get(f"/memory/{session_id}")


class KernelService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/kernel/execute", json_data=kwargs)


class GoalsService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def list(self, user_id: str, status: str | None = None) -> list[dict[str, Any]]:
        params = {"status": status} if status else None
        return await self._client.get(f"/goals/{user_id}", params=params)

    async def create(self, user_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post(f"/goals/{user_id}", json_data=kwargs)

    async def get(self, user_id: str, goal_id: str) -> dict[str, Any]:
        return await self._client.get(f"/goals/{user_id}/detail/{goal_id}")

    async def update(self, user_id: str, goal_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._client.patch(f"/goals/{user_id}/detail/{goal_id}", json_data=kwargs)

    async def delete(self, user_id: str, goal_id: str) -> None:
        await self._client.delete(f"/goals/{user_id}/detail/{goal_id}")

    async def next_actions(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        return await self._client.get(f"/goals/{user_id}/next-actions", params={"limit": limit})

    async def blocked(self, user_id: str) -> list[dict[str, Any]]:
        return await self._client.get(f"/goals/{user_id}/blocked")

    async def analyze(self, user_id: str) -> dict[str, Any]:
        return await self._client.get(f"/goals/{user_id}/analyze")


class TasksService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def list(self, status: str | None = None, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return await self._client.get("/tasks", params=params)

    async def create(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/tasks", json_data=kwargs)

    async def get(self, task_id: str) -> dict[str, Any]:
        return await self._client.get(f"/tasks/{task_id}")

    async def update(self, task_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._client.patch(f"/tasks/{task_id}", json_data=kwargs)

    async def delete(self, task_id: str) -> None:
        await self._client.delete(f"/tasks/{task_id}")

    async def advance(self, task_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post(f"/tasks/{task_id}/advance", json_data=kwargs)

    async def transition(self, task_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post(f"/tasks/{task_id}/transition", json_data=kwargs)


class WorkflowsService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def list(self, tag: str | None = None) -> list[dict[str, Any]]:
        params = {"tag": tag} if tag else None
        return await self._client.get("/workflows", params=params)

    async def create(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/workflows", json_data=kwargs)

    async def get(self, workflow_id: str) -> dict[str, Any]:
        return await self._client.get(f"/workflows/{workflow_id}")

    async def update(self, workflow_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._client.put(f"/workflows/{workflow_id}", json_data=kwargs)

    async def delete(self, workflow_id: str) -> None:
        await self._client.delete(f"/workflows/{workflow_id}")

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/workflows/executions", json_data=kwargs)

    async def list_executions(self, **kwargs: Any) -> list[dict[str, Any]]:
        return await self._client.get("/workflows/executions", params=kwargs)

    async def get_execution(self, execution_id: str) -> dict[str, Any]:
        return await self._client.get(f"/workflows/executions/{execution_id}")

    async def start_execution(self, execution_id: str) -> dict[str, Any]:
        return await self._client.post(f"/workflows/executions/{execution_id}/start")

    async def action(self, execution_id: str, action: str) -> dict[str, Any]:
        return await self._client.post(
            f"/workflows/executions/{execution_id}/action",
            json_data={"action": action},
        )

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/workflows/health")

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/workflows/metrics")

    async def statistics(self) -> dict[str, Any]:
        return await self._client.get("/workflows/statistics")

    async def templates(self) -> dict[str, Any]:
        return await self._client.get("/workflows/templates")


class SchedulerService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def create_job(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/scheduler/jobs", json_data=kwargs)

    async def list_jobs(self, status: str | None = None, limit: int = 20, offset: int = 0) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        return await self._client.get("/scheduler/jobs", params=params)

    async def get_job(self, job_id: str) -> dict[str, Any]:
        return await self._client.get(f"/scheduler/jobs/{job_id}")

    async def delete_job(self, job_id: str) -> dict[str, Any]:
        return await self._client.delete(f"/scheduler/jobs/{job_id}")

    async def execute_job(self, job_id: str) -> dict[str, Any]:
        return await self._client.post(f"/scheduler/jobs/{job_id}/execute")

    async def cancel_job(self, job_id: str) -> dict[str, Any]:
        return await self._client.post(f"/scheduler/jobs/{job_id}/cancel")

    async def pause_job(self, job_id: str) -> dict[str, Any]:
        return await self._client.post(f"/scheduler/jobs/{job_id}/pause")

    async def resume_job(self, job_id: str) -> dict[str, Any]:
        return await self._client.post(f"/scheduler/jobs/{job_id}/resume")

    async def retry_job(self, job_id: str) -> dict[str, Any]:
        return await self._client.post(f"/scheduler/jobs/{job_id}/retry")

    async def run_pending(self) -> dict[str, Any]:
        return await self._client.post("/scheduler/run-pending")

    async def statistics(self) -> dict[str, Any]:
        return await self._client.get("/scheduler/statistics")

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/scheduler/health")


class ToolsService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def list(self) -> dict[str, Any]:
        return await self._client.get("/tools")

    async def get(self, tool_id: str) -> dict[str, Any]:
        return await self._client.get(f"/tools/{tool_id}")

    async def register(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/tools/register", json_data=kwargs)

    async def unregister(self, tool_id: str) -> None:
        await self._client.delete(f"/tools/{tool_id}")

    async def execute(self, tool_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post(f"/tools/{tool_id}/execute", json_data=kwargs)

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/tools/metrics")

    async def health(self, tool_id: str) -> dict[str, Any]:
        return await self._client.get(f"/tools/{tool_id}/health")


class RAGService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def query(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/rag/query", json_data=kwargs)

    async def retrieve(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/rag/retrieve", json_data=kwargs)

    async def index(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/rag/index", json_data=kwargs)

    async def reindex(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/rag/reindex", json_data=kwargs)

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/rag/health")

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/rag/metrics")

    async def statistics(self) -> dict[str, Any]:
        return await self._client.get("/rag/statistics")


class VectorMemoryService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def store(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/vector-memory/store", json_data=kwargs)

    async def search(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/vector-memory/search", json_data=kwargs)

    async def similarity(self, embedding: list[float], **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/vector-memory/similarity", json_data={"embedding": embedding}, params=kwargs)

    async def delete(self, vector_id: str) -> dict[str, Any]:
        return await self._client.delete(f"/vector-memory/{vector_id}")

    async def statistics(self) -> dict[str, Any]:
        return await self._client.get("/vector-memory/statistics")

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/vector-memory/health")


class EventsService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def publish(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/events/publish", json_data=kwargs)

    async def list(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.get("/events", params=kwargs)

    async def get(self, event_id: str) -> dict[str, Any]:
        return await self._client.get(f"/events/{event_id}")

    async def statistics(self) -> dict[str, Any]:
        return await self._client.get("/events/statistics")

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/events/health")


class PluginsService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def list(self) -> dict[str, Any]:
        return await self._client.get("/plugins/")

    async def get(self, plugin_id: str) -> dict[str, Any]:
        return await self._client.get(f"/plugins/{plugin_id}")

    async def register(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/plugins/", json_data=kwargs)

    async def unregister(self, plugin_id: str) -> dict[str, Any]:
        return await self._client.delete(f"/plugins/{plugin_id}")

    async def enable(self, plugin_id: str) -> dict[str, Any]:
        return await self._client.post(f"/plugins/{plugin_id}/enable")

    async def disable(self, plugin_id: str) -> dict[str, Any]:
        return await self._client.post(f"/plugins/{plugin_id}/disable")

    async def execute(self, plugin_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post(f"/plugins/{plugin_id}/execute", json_data=kwargs)

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/plugins/health")

    async def statistics(self) -> dict[str, Any]:
        return await self._client.get("/plugins/statistics")


class LearningService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def extract(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/learning/extract", json_data=kwargs)

    async def search(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/learning/search", json_data=kwargs)

    async def artifacts(self, user_id: str | None = None, artifact_type: str | None = None, limit: int = 20) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        if artifact_type:
            params["artifact_type"] = artifact_type
        return await self._client.get("/learning/artifacts", params=params)

    async def get_artifact(self, artifact_id: str) -> dict[str, Any]:
        return await self._client.get(f"/learning/artifacts/{artifact_id}")

    async def delete_artifact(self, artifact_id: str) -> None:
        await self._client.delete(f"/learning/artifacts/{artifact_id}")

    async def consolidate(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/learning/consolidate", json_data=kwargs)

    async def stats(self) -> dict[str, Any]:
        return await self._client.get("/learning/stats")


class KnowledgeGraphService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def create_entity(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/knowledge-graph/entities", json_data=kwargs)

    async def list_entities(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.get("/knowledge-graph/entities", params=kwargs)

    async def get_entity(self, entity_id: str) -> dict[str, Any]:
        return await self._client.get(f"/knowledge-graph/entities/{entity_id}")

    async def update_entity(self, entity_id: str, **kwargs: Any) -> dict[str, Any]:
        return await self._client.put(f"/knowledge-graph/entities/{entity_id}", json_data=kwargs)

    async def delete_entity(self, entity_id: str) -> None:
        await self._client.delete(f"/knowledge-graph/entities/{entity_id}")

    async def create_relationship(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/knowledge-graph/relationships", json_data=kwargs)

    async def list_relationships(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.get("/knowledge-graph/relationships", params=kwargs)

    async def search(self, **kwargs: Any) -> dict[str, Any]:
        return await self._client.post("/knowledge-graph/search", json_data=kwargs)

    async def extract(self, text: str, source: str = "extraction") -> dict[str, Any]:
        return await self._client.post("/knowledge-graph/extract", json_data={"text": text, "source": source})

    async def validate(self) -> dict[str, Any]:
        return await self._client.get("/knowledge-graph/validate")

    async def types(self) -> dict[str, Any]:
        return await self._client.get("/knowledge-graph/types")


class ObservabilityService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/observability/health")

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/observability/metrics")

    async def traces(self, limit: int = 50) -> dict[str, Any]:
        return await self._client.get("/observability/traces", params={"limit": limit})

    async def logs(self, limit: int = 50, severity: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if severity:
            params["severity"] = severity
        return await self._client.get("/observability/logs", params=params)

    async def diagnostics(self) -> dict[str, Any]:
        return await self._client.get("/observability/diagnostics")

    async def alerts(self, state: str | None = None) -> dict[str, Any]:
        params = {"state": state} if state else None
        return await self._client.get("/observability/alerts", params=params)


class DeploymentService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/deployment/health")

    async def readiness(self) -> dict[str, Any]:
        return await self._client.get("/deployment/readiness")

    async def liveness(self) -> dict[str, Any]:
        return await self._client.get("/deployment/liveness")

    async def environment(self) -> dict[str, Any]:
        return await self._client.get("/deployment/environment")

    async def configuration(self) -> dict[str, Any]:
        return await self._client.get("/deployment/configuration")

    async def diagnostics(self) -> dict[str, Any]:
        return await self._client.get("/deployment/diagnostics")

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/deployment/metrics")

    async def statistics(self) -> dict[str, Any]:
        return await self._client.get("/deployment/statistics")


class ScalingService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/scaling/health")

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/scaling/metrics")

    async def workers(self) -> dict[str, Any]:
        return await self._client.get("/scaling/workers")

    async def queues(self) -> dict[str, Any]:
        return await self._client.get("/scaling/queues")

    async def cache(self) -> dict[str, Any]:
        return await self._client.get("/scaling/cache")

    async def resources(self) -> dict[str, Any]:
        return await self._client.get("/scaling/resources")

    async def scale_up(self, amount: int = 1) -> dict[str, Any]:
        return await self._client.post("/scaling/scale-up", params={"amount": amount})

    async def scale_down(self, amount: int = 1) -> dict[str, Any]:
        return await self._client.post("/scaling/scale-down", params={"amount": amount})

    async def clear_cache(self) -> dict[str, Any]:
        return await self._client.post("/scaling/cache/clear")


class SecurityService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/security/health")

    async def headers(self) -> dict[str, Any]:
        return await self._client.get("/security/headers")

    async def statistics(self) -> dict[str, Any]:
        return await self._client.get("/security/statistics")

    async def register(self, username: str, email: str, password: str) -> dict[str, Any]:
        return await self._client.post("/security/auth/register", json_data={"username": username, "email": email, "password": password})

    async def login(self, username: str, password: str) -> dict[str, Any]:
        return await self._client.post("/security/auth/login", json_data={"username": username, "password": password})

    async def verify_token(self, token: str) -> dict[str, Any]:
        return await self._client.post("/security/auth/token/verify", json_data={"token": token})

    async def create_api_key(self, user_id: str, name: str, scopes: list[str] | None = None) -> dict[str, Any]:
        return await self._client.post("/security/api-keys", json_data={"user_id": user_id, "name": name, "scopes": scopes or []})

    async def list_api_keys(self, user_id: str) -> dict[str, Any]:
        return await self._client.get(f"/security/api-keys/{user_id}")

    async def revoke_api_key(self, key_id: str) -> dict[str, Any]:
        return await self._client.delete(f"/security/api-keys/{key_id}")

    async def audit_log(self, user_id: str | None = None, limit: int = 50) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if user_id:
            params["user_id"] = user_id
        return await self._client.get("/security/audit", params=params)

    async def roles(self) -> dict[str, Any]:
        return await self._client.get("/security/rbac/roles")

    async def check_permission(self, user_id: str, resource: str, action: str) -> dict[str, Any]:
        return await self._client.post("/security/rbac/check", json_data={"user_id": user_id, "resource": resource, "action": action})


class EnterpriseService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def status(self) -> dict[str, Any]:
        return await self._client.get("/enterprise/status")

    async def organizations(self) -> dict[str, Any]:
        return await self._client.get("/enterprise/organizations")

    async def tenants(self, org_id: str | None = None) -> dict[str, Any]:
        params = {"org_id": org_id} if org_id else None
        return await self._client.get("/enterprise/tenants", params=params)

    async def workspaces(self, org_id: str | None = None) -> dict[str, Any]:
        params = {"org_id": org_id} if org_id else None
        return await self._client.get("/enterprise/workspaces", params=params)

    async def teams(self, org_id: str | None = None) -> dict[str, Any]:
        params = {"org_id": org_id} if org_id else None
        return await self._client.get("/enterprise/teams", params=params)

    async def roles(self) -> dict[str, Any]:
        return await self._client.get("/enterprise/roles")

    async def permissions(self) -> dict[str, Any]:
        return await self._client.get("/enterprise/permissions")

    async def policies(self) -> dict[str, Any]:
        return await self._client.get("/enterprise/policies")

    async def create_organization(self, name: str, owner_id: str = "") -> dict[str, Any]:
        return await self._client.post("/enterprise/organizations", params={"name": name, "owner_id": owner_id})

    async def create_workspace(self, name: str, org_id: str = "") -> dict[str, Any]:
        return await self._client.post("/enterprise/workspaces", params={"name": name, "org_id": org_id})

    async def create_team(self, name: str, org_id: str = "") -> dict[str, Any]:
        return await self._client.post("/enterprise/teams", params={"name": name, "org_id": org_id})

    async def create_role(self, name: str) -> dict[str, Any]:
        return await self._client.post("/enterprise/roles", params={"name": name})

    async def create_policy(self, name: str, policy_type: str) -> dict[str, Any]:
        return await self._client.post("/enterprise/policies", params={"name": name, "policy_type": policy_type})

    async def audit(self, limit: int = 50) -> dict[str, Any]:
        return await self._client.get("/enterprise/audit", params={"limit": limit})

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/enterprise/metrics")

    async def licenses(self) -> dict[str, Any]:
        return await self._client.get("/enterprise/licenses")

    async def quotas(self) -> dict[str, Any]:
        return await self._client.get("/enterprise/quotas")


class ProfileService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def get(self, user_id: str) -> dict[str, Any]:
        return await self._client.get(f"/profile/{user_id}")


class DatabaseService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/database/health")

    async def statistics(self) -> dict[str, Any]:
        return await self._client.get("/database/statistics")

    async def migrations(self) -> dict[str, Any]:
        return await self._client.get("/database/migrations")

    async def schema(self) -> dict[str, Any]:
        return await self._client.get("/database/schema")

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/database/metrics")


class PerformanceService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/performance/health")

    async def benchmarks(self, category: str | None = None) -> dict[str, Any]:
        params = {"category": category} if category else None
        return await self._client.get("/performance/benchmarks", params=params)

    async def diagnostics(self) -> dict[str, Any]:
        return await self._client.get("/performance/diagnostics")

    async def recommendations(self) -> dict[str, Any]:
        return await self._client.get("/performance/recommendations")

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/performance/metrics")

    async def start_profiling(self, profile_type: str = "cpu", target: str = "") -> dict[str, Any]:
        return await self._client.post("/performance/profile/start", params={"profile_type": profile_type, "target": target})

    async def stop_profiling(self, session_id: str) -> dict[str, Any]:
        return await self._client.post("/performance/profile/stop", params={"session_id": session_id})

    async def run_benchmark(self, category: str = "general", iterations: int = 100) -> dict[str, Any]:
        return await self._client.post("/performance/benchmark/run", params={"category": category, "iterations": iterations})


class ResilienceService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def health(self) -> dict[str, Any]:
        return await self._client.get("/resilience/health")

    async def status(self) -> dict[str, Any]:
        return await self._client.get("/resilience/status")

    async def circuit_breakers(self) -> dict[str, Any]:
        return await self._client.get("/resilience/circuit-breakers")

    async def retries(self) -> dict[str, Any]:
        return await self._client.get("/resilience/retries")

    async def diagnostics(self) -> dict[str, Any]:
        return await self._client.get("/resilience/diagnostics")

    async def metrics(self) -> dict[str, Any]:
        return await self._client.get("/resilience/metrics")


class AutonomyService:
    def __init__(self, client: NovaClient) -> None:
        self._client = client

    async def status(self) -> dict[str, Any]:
        return await self._client.get("/autonomy/status")

    async def objectives(self) -> dict[str, Any]:
        return await self._client.get("/autonomy/objectives")

    async def recommendations(self) -> dict[str, Any]:
        return await self._client.get("/autonomy/recommendations")

    async def reflections(self, limit: int = 50) -> dict[str, Any]:
        return await self._client.get("/autonomy/reflections", params={"limit": limit})

    async def policies(self) -> dict[str, Any]:
        return await self._client.get("/autonomy/policies")

    async def evaluate(self) -> dict[str, Any]:
        return await self._client.post("/autonomy/evaluate")

    async def approve(self, recommendation_id: str, approver: str = "") -> dict[str, Any]:
        return await self._client.post("/autonomy/approve", params={"recommendation_id": recommendation_id, "approver": approver})

    async def reject(self, recommendation_id: str, reason: str = "") -> dict[str, Any]:
        return await self._client.post("/autonomy/reject", params={"recommendation_id": recommendation_id, "reason": reason})
