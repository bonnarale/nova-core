import { Configuration, getDefaultHeaders } from "./config.js";
import {
  NovaAPIError,
  NovaAuthError,
  NovaRateLimitError,
  NovaServerError,
  NovaConnectionError,
  NovaTimeoutError,
  NovaValidationError,
} from "./errors.js";
import { RetryHandler } from "./retry.js";
import type { HTTPMethod, TelemetryMetrics } from "./types.js";

export class NovaClient {
  private config: Configuration;
  private retry: RetryHandler;
  private metrics: TelemetryMetrics;

  constructor(config: Configuration) {
    this.config = config;
    this.retry = new RetryHandler(config);
    this.metrics = {
      totalRequests: 0,
      totalErrors: 0,
      totalLatencyMs: 0,
      requestsByEndpoint: {},
      errorsByType: {},
    };
  }

  private async request<T>(method: HTTPMethod, path: string, options: {
    body?: unknown;
    params?: Record<string, string | number | boolean | undefined>;
    headers?: Record<string, string>;
  } = {}): Promise<T> {
    const url = new URL(path, this.config.baseUrl);
    if (options.params) {
      for (const [key, value] of Object.entries(options.params)) {
        if (value !== undefined) {
          url.searchParams.set(key, String(value));
        }
      }
    }

    const headers = {
      ...getDefaultHeaders(this.config),
      ...options.headers,
    };

    const startTime = Date.now();
    this.metrics.totalRequests++;
    const endpointCount = this.metrics.requestsByEndpoint;
    endpointCount[path] = (endpointCount[path] || 0) + 1;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

      const response = await fetch(url.toString(), {
        method,
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const latencyMs = Date.now() - startTime;
      this.metrics.totalLatencyMs += latencyMs;

      if (!response.ok) {
        this.metrics.totalErrors++;
        await this.handleError(response, path);
      }

      const text = await response.text();
      return text ? JSON.parse(text) : ({} as T);
    } catch (error) {
      this.metrics.totalErrors++;
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new NovaTimeoutError(`Request timed out after ${this.config.timeout}ms`);
      }
      if (error instanceof TypeError && error.message.includes("fetch")) {
        throw new NovaConnectionError(`Connection failed: ${error.message}`);
      }
      throw error;
    }
  }

  private async handleError(response: Response, path: string): Promise<never> {
    let body: Record<string, unknown> = {};
    try {
      body = await response.json() as Record<string, unknown>;
    } catch {
      body = { detail: await response.text() };
    }

    const message = String(body.detail || body.message || `HTTP ${response.status}`);
    const status = response.status;

    if (status === 401) throw new NovaAuthError(message, status, body);
    if (status === 422) {
      const errors = (body.errors as Array<Record<string, unknown>>) || [];
      throw new NovaValidationError(message, errors, status, body);
    }
    if (status === 429) {
      const retryAfter = response.headers.get("retry-after");
      throw new NovaRateLimitError(
        message,
        retryAfter ? parseFloat(retryAfter) : undefined,
        status,
        body,
      );
    }
    if (status >= 500) throw new NovaServerError(message, status, body);
    throw new NovaAPIError(message, status, body);
  }

  async get<T = unknown>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
    return this.retry.execute(() => this.request<T>("GET", path, { params }));
  }

  async post<T = unknown>(path: string, body?: unknown, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
    return this.retry.execute(() => this.request<T>("POST", path, { body, params }));
  }

  async put<T = unknown>(path: string, body?: unknown): Promise<T> {
    return this.retry.execute(() => this.request<T>("PUT", path, { body }));
  }

  async patch<T = unknown>(path: string, body?: unknown): Promise<T> {
    return this.retry.execute(() => this.request<T>("PATCH", path, { body }));
  }

  async delete<T = unknown>(path: string): Promise<T> {
    return this.retry.execute(() => this.request<T>("DELETE", path));
  }

  getMetrics(): TelemetryMetrics {
    return { ...this.metrics };
  }

  // Agents
  agents = {
    list: () => this.get("/agents"),
    get: (id: string) => this.get(`/agents/${id}`),
    create: (data: Record<string, unknown>) => this.post("/agents", data),
    update: (id: string, data: Record<string, unknown>) => this.patch(`/agents/${id}`, data),
    delete: (id: string) => this.delete(`/agents/${id}`),
    register: (data: Record<string, unknown>) => this.post("/agents/register", data),
    health: () => this.get("/agents/health"),
    capabilities: () => this.get("/agents/capabilities"),
    dispatch: (data: Record<string, unknown>) => this.post("/agents/runtime/dispatch", data),
    coordinate: (data: Record<string, unknown>) => this.post("/agents/runtime/coordinate", data),
    runtimeMetrics: () => this.get("/agents/runtime/metrics"),
    runtimeTraces: () => this.get("/agents/runtime/traces"),
  };

  // Models
  models = {
    chat: (data: Record<string, unknown>) => this.post("/models/chat", data),
    health: () => this.get("/models/health"),
    metrics: () => this.get("/models/metrics"),
    list: (provider?: string) => this.get("/models/list", provider ? { provider } : undefined),
    providers: () => this.get("/models/providers"),
    cacheStats: () => this.get("/models/cache/stats"),
    clearCache: () => this.delete("/models/cache"),
    traces: (limit = 50) => this.get("/models/traces", { limit }),
  };

  // Memory
  memory = {
    get: (sessionId: string) => this.get(`/memory/${sessionId}`),
  };

  // Kernel
  kernel = {
    execute: (data: Record<string, unknown>) => this.post("/kernel/execute", data),
  };

  // Goals
  goals = {
    list: (userId: string, status?: string) => this.get(`/goals/${userId}`, status ? { status } : undefined),
    create: (userId: string, data: Record<string, unknown>) => this.post(`/goals/${userId}`, data),
    get: (userId: string, goalId: string) => this.get(`/goals/${userId}/detail/${goalId}`),
    update: (userId: string, goalId: string, data: Record<string, unknown>) => this.patch(`/goals/${userId}/detail/${goalId}`, data),
    delete: (userId: string, goalId: string) => this.delete(`/goals/${userId}/detail/${goalId}`),
    nextActions: (userId: string, limit = 10) => this.get(`/goals/${userId}/next-actions`, { limit }),
    blocked: (userId: string) => this.get(`/goals/${userId}/blocked`),
    analyze: (userId: string) => this.get(`/goals/${userId}/analyze`),
  };

  // Tasks
  tasks = {
    list: (status?: string, limit = 20, offset = 0) => this.get("/tasks", { status, limit, offset }),
    create: (data: Record<string, unknown>) => this.post("/tasks", data),
    get: (taskId: string) => this.get(`/tasks/${taskId}`),
    update: (taskId: string, data: Record<string, unknown>) => this.patch(`/tasks/${taskId}`, data),
    delete: (taskId: string) => this.delete(`/tasks/${taskId}`),
    advance: (taskId: string, data?: Record<string, unknown>) => this.post(`/tasks/${taskId}/advance`, data),
    transition: (taskId: string, data: Record<string, unknown>) => this.post(`/tasks/${taskId}/transition`, data),
  };

  // Workflows
  workflows = {
    list: (tag?: string) => this.get("/workflows", tag ? { tag } : undefined),
    create: (data: Record<string, unknown>) => this.post("/workflows", data),
    get: (id: string) => this.get(`/workflows/${id}`),
    update: (id: string, data: Record<string, unknown>) => this.put(`/workflows/${id}`, data),
    delete: (id: string) => this.delete(`/workflows/${id}`),
    execute: (data: Record<string, unknown>) => this.post("/workflows/executions", data),
    listExecutions: (params?: Record<string, unknown>) => this.get("/workflows/executions", params as Record<string, string | number | boolean | undefined>),
    getExecution: (id: string) => this.get(`/workflows/executions/${id}`),
    startExecution: (id: string) => this.post(`/workflows/executions/${id}/start`),
    action: (id: string, action: string) => this.post(`/workflows/executions/${id}/action`, { action }),
    health: () => this.get("/workflows/health"),
    metrics: () => this.get("/workflows/metrics"),
    statistics: () => this.get("/workflows/statistics"),
    templates: () => this.get("/workflows/templates"),
  };

  // Scheduler
  scheduler = {
    createJob: (data: Record<string, unknown>) => this.post("/scheduler/jobs", data),
    listJobs: (status?: string, limit = 20, offset = 0) => this.get("/scheduler/jobs", { status, limit, offset }),
    getJob: (id: string) => this.get(`/scheduler/jobs/${id}`),
    deleteJob: (id: string) => this.delete(`/scheduler/jobs/${id}`),
    executeJob: (id: string) => this.post(`/scheduler/jobs/${id}/execute`),
    cancelJob: (id: string) => this.post(`/scheduler/jobs/${id}/cancel`),
    pauseJob: (id: string) => this.post(`/scheduler/jobs/${id}/pause`),
    resumeJob: (id: string) => this.post(`/scheduler/jobs/${id}/resume`),
    retryJob: (id: string) => this.post(`/scheduler/jobs/${id}/retry`),
    runPending: () => this.post("/scheduler/run-pending"),
    statistics: () => this.get("/scheduler/statistics"),
    health: () => this.get("/scheduler/health"),
  };

  // Tools
  tools = {
    list: () => this.get("/tools"),
    get: (id: string) => this.get(`/tools/${id}`),
    register: (data: Record<string, unknown>) => this.post("/tools/register", data),
    unregister: (id: string) => this.delete(`/tools/${id}`),
    execute: (id: string, data: Record<string, unknown>) => this.post(`/tools/${id}/execute`, data),
    metrics: () => this.get("/tools/metrics"),
    health: (id: string) => this.get(`/tools/${id}/health`),
  };

  // RAG
  rag = {
    query: (data: Record<string, unknown>) => this.post("/rag/query", data),
    retrieve: (data: Record<string, unknown>) => this.post("/rag/retrieve", data),
    index: (data: Record<string, unknown>) => this.post("/rag/index", data),
    reindex: (data: Record<string, unknown>) => this.post("/rag/reindex", data),
    health: () => this.get("/rag/health"),
    metrics: () => this.get("/rag/metrics"),
    statistics: () => this.get("/rag/statistics"),
  };

  // Vector Memory
  vectorMemory = {
    store: (data: Record<string, unknown>) => this.post("/vector-memory/store", data),
    search: (data: Record<string, unknown>) => this.post("/vector-memory/search", data),
    delete: (id: string) => this.delete(`/vector-memory/${id}`),
    statistics: () => this.get("/vector-memory/statistics"),
    health: () => this.get("/vector-memory/health"),
  };

  // Events
  events = {
    publish: (data: Record<string, unknown>) => this.post("/events/publish", data),
    list: (params?: Record<string, unknown>) => this.get("/events", params as Record<string, string | number | boolean | undefined>),
    get: (id: string) => this.get(`/events/${id}`),
    statistics: () => this.get("/events/statistics"),
    health: () => this.get("/events/health"),
  };

  // Plugins
  plugins = {
    list: () => this.get("/plugins/"),
    get: (id: string) => this.get(`/plugins/${id}`),
    register: (data: Record<string, unknown>) => this.post("/plugins/", data),
    unregister: (id: string) => this.delete(`/plugins/${id}`),
    enable: (id: string) => this.post(`/plugins/${id}/enable`),
    disable: (id: string) => this.post(`/plugins/${id}/disable`),
    execute: (id: string, data: Record<string, unknown>) => this.post(`/plugins/${id}/execute`, data),
    health: () => this.get("/plugins/health"),
    statistics: () => this.get("/plugins/statistics"),
  };

  // Learning
  learning = {
    extract: (data: Record<string, unknown>) => this.post("/learning/extract", data),
    search: (data: Record<string, unknown>) => this.post("/learning/search", data),
    artifacts: (userId?: string, artifactType?: string, limit = 20) => this.get("/learning/artifacts", { user_id: userId, artifact_type: artifactType, limit }),
    getArtifact: (id: string) => this.get(`/learning/artifacts/${id}`),
    deleteArtifact: (id: string) => this.delete(`/learning/artifacts/${id}`),
    consolidate: (data: Record<string, unknown>) => this.post("/learning/consolidate", data),
    stats: () => this.get("/learning/stats"),
  };

  // Knowledge Graph
  knowledgeGraph = {
    createEntity: (data: Record<string, unknown>) => this.post("/knowledge-graph/entities", data),
    listEntities: (params?: Record<string, unknown>) => this.get("/knowledge-graph/entities", params as Record<string, string | number | boolean | undefined>),
    getEntity: (id: string) => this.get(`/knowledge-graph/entities/${id}`),
    updateEntity: (id: string, data: Record<string, unknown>) => this.put(`/knowledge-graph/entities/${id}`, data),
    deleteEntity: (id: string) => this.delete(`/knowledge-graph/entities/${id}`),
    createRelationship: (data: Record<string, unknown>) => this.post("/knowledge-graph/relationships", data),
    listRelationships: (params?: Record<string, unknown>) => this.get("/knowledge-graph/relationships", params as Record<string, string | number | boolean | undefined>),
    search: (data: Record<string, unknown>) => this.post("/knowledge-graph/search", data),
    extract: (text: string, source = "extraction") => this.post("/knowledge-graph/extract", { text, source }),
    validate: () => this.get("/knowledge-graph/validate"),
    types: () => this.get("/knowledge-graph/types"),
  };

  // Observability
  observability = {
    health: () => this.get("/observability/health"),
    metrics: () => this.get("/observability/metrics"),
    traces: (limit = 50) => this.get("/observability/traces", { limit }),
    logs: (limit = 50, severity?: string) => this.get("/observability/logs", { limit, severity }),
    diagnostics: () => this.get("/observability/diagnostics"),
    alerts: (state?: string) => this.get("/observability/alerts", state ? { state } : undefined),
  };

  // Deployment
  deployment = {
    health: () => this.get("/deployment/health"),
    readiness: () => this.get("/deployment/readiness"),
    liveness: () => this.get("/deployment/liveness"),
    environment: () => this.get("/deployment/environment"),
    configuration: () => this.get("/deployment/configuration"),
    diagnostics: () => this.get("/deployment/diagnostics"),
    metrics: () => this.get("/deployment/metrics"),
    statistics: () => this.get("/deployment/statistics"),
  };

  // Scaling
  scaling = {
    health: () => this.get("/scaling/health"),
    metrics: () => this.get("/scaling/metrics"),
    workers: () => this.get("/scaling/workers"),
    queues: () => this.get("/scaling/queues"),
    cache: () => this.get("/scaling/cache"),
    resources: () => this.get("/scaling/resources"),
    scaleUp: (amount = 1) => this.post("/scaling/scale-up", undefined, { amount }),
    scaleDown: (amount = 1) => this.post("/scaling/scale-down", undefined, { amount }),
    clearCache: () => this.post("/scaling/cache/clear"),
  };

  // Security
  security = {
    health: () => this.get("/security/health"),
    headers: () => this.get("/security/headers"),
    statistics: () => this.get("/security/statistics"),
    register: (data: Record<string, unknown>) => this.post("/security/auth/register", data),
    login: (data: Record<string, unknown>) => this.post("/security/auth/login", data),
    verifyToken: (token: string) => this.post("/security/auth/token/verify", { token }),
    createApiKey: (data: Record<string, unknown>) => this.post("/security/api-keys", data),
    listApiKeys: (userId: string) => this.get(`/security/api-keys/${userId}`),
    revokeApiKey: (keyId: string) => this.delete(`/security/api-keys/${keyId}`),
    auditLog: (userId?: string, limit = 50) => this.get("/security/audit", { user_id: userId, limit }),
    roles: () => this.get("/security/rbac/roles"),
    checkPermission: (data: Record<string, unknown>) => this.post("/security/rbac/check", data),
  };

  // Enterprise
  enterprise = {
    status: () => this.get("/enterprise/status"),
    organizations: () => this.get("/enterprise/organizations"),
    tenants: (orgId?: string) => this.get("/enterprise/tenants", orgId ? { org_id: orgId } : undefined),
    workspaces: (orgId?: string) => this.get("/enterprise/workspaces", orgId ? { org_id: orgId } : undefined),
    teams: (orgId?: string) => this.get("/enterprise/teams", orgId ? { org_id: orgId } : undefined),
    roles: () => this.get("/enterprise/roles"),
    permissions: () => this.get("/enterprise/permissions"),
    policies: () => this.get("/enterprise/policies"),
    createOrganization: (name: string, ownerId = "") => this.post("/enterprise/organizations", undefined, { name, owner_id: ownerId }),
    createWorkspace: (name: string, orgId = "") => this.post("/enterprise/workspaces", undefined, { name, org_id: orgId }),
    createTeam: (name: string, orgId = "") => this.post("/enterprise/teams", undefined, { name, org_id: orgId }),
    createRole: (name: string) => this.post("/enterprise/roles", undefined, { name }),
    createPolicy: (name: string, policyType: string) => this.post("/enterprise/policies", undefined, { name, policy_type: policyType }),
    audit: (limit = 50) => this.get("/enterprise/audit", { limit }),
    metrics: () => this.get("/enterprise/metrics"),
    licenses: () => this.get("/enterprise/licenses"),
    quotas: () => this.get("/enterprise/quotas"),
  };

  // Profile
  profile = {
    get: (userId: string) => this.get(`/profile/${userId}`),
  };

  // Database
  database = {
    health: () => this.get("/database/health"),
    statistics: () => this.get("/database/statistics"),
    migrations: () => this.get("/database/migrations"),
    schema: () => this.get("/database/schema"),
    metrics: () => this.get("/database/metrics"),
  };

  // Performance
  performance = {
    health: () => this.get("/performance/health"),
    benchmarks: (category?: string) => this.get("/performance/benchmarks", category ? { category } : undefined),
    diagnostics: () => this.get("/performance/diagnostics"),
    recommendations: () => this.get("/performance/recommendations"),
    metrics: () => this.get("/performance/metrics"),
  };

  // Resilience
  resilience = {
    health: () => this.get("/resilience/health"),
    status: () => this.get("/resilience/status"),
    circuitBreakers: () => this.get("/resilience/circuit-breakers"),
    retries: () => this.get("/resilience/retries"),
    diagnostics: () => this.get("/resilience/diagnostics"),
    metrics: () => this.get("/resilience/metrics"),
  };

  // Autonomy
  autonomy = {
    status: () => this.get("/autonomy/status"),
    objectives: () => this.get("/autonomy/objectives"),
    recommendations: () => this.get("/autonomy/recommendations"),
    reflections: (limit = 50) => this.get("/autonomy/reflections", { limit }),
    policies: () => this.get("/autonomy/policies"),
    evaluate: () => this.post("/autonomy/evaluate"),
    approve: (recommendationId: string, approver = "") => this.post("/autonomy/approve", undefined, { recommendation_id: recommendationId, approver }),
    reject: (recommendationId: string, reason = "") => this.post("/autonomy/reject", undefined, { recommendation_id: recommendationId, reason }),
  };

  // Health
  async health(): Promise<{ status: string }> {
    return this.get("/health");
  }
}
