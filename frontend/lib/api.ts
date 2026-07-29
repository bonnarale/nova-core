const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_PREFIX = "/api/v1";

import { globalToast } from "@/lib/toast";

export class NovaAPI {
  private baseUrl: string;
  private headers: Record<string, string>;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
    this.headers = { "Content-Type": "application/json" };
  }

  setAuthToken(token: string) {
    this.headers["Authorization"] = `Bearer ${token}`;
  }

  setApiKey(key: string) {
    this.headers["X-API-Key"] = key;
  }

  private async request<T>(method: string, path: string, body?: unknown, params?: Record<string, string>): Promise<T> {
    const url = new URL(`${API_PREFIX}${path}`, this.baseUrl);
    if (params) {
      Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
    }
    const res = await fetch(url.toString(), {
      method,
      headers: this.headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      const msg = err.detail || `HTTP ${res.status}`;
      globalToast.error(`API Error: ${msg}`);
      throw new Error(msg);
    }
    return res.json();
  }

  get<T>(path: string, params?: Record<string, string>) {
    return this.request<T>("GET", path, undefined, params);
  }
  post<T>(path: string, body?: unknown, params?: Record<string, string>) {
    return this.request<T>("POST", path, body, params);
  }
  put<T>(path: string, body?: unknown) {
    return this.request<T>("PUT", path, body);
  }
  patch<T>(path: string, body?: unknown) {
    return this.request<T>("PATCH", path, body);
  }
  delete<T>(path: string) {
    return this.request<T>("DELETE", path);
  }

  async stream(path: string, body?: unknown): Promise<ReadableStream<Uint8Array>> {
    const url = new URL(`${API_PREFIX}${path}`, this.baseUrl);
    const res = await fetch(url.toString(), {
      method: "POST",
      headers: { ...this.headers, Accept: "text/event-stream" },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!res.ok) {
      globalToast.error(`Stream error: ${res.status}`);
      throw new Error(`Stream error: ${res.status}`);
    }
    return res.body!;
  }

  health() { return this.get<{ status: string }>("/health"); }
  models = {
    chat: (data: Record<string, unknown>) => this.post("/models/chat", data),
    list: () => this.get("/models/list"),
    health: () => this.get("/models/health"),
    providers: () => this.get("/models/providers"),
    metrics: () => this.get("/models/metrics"),
  };
  agents = {
    list: () => this.get("/agents"),
    get: (id: string) => this.get(`/agents/${id}`),
    create: (data: Record<string, unknown>) => this.post("/agents", data),
    dispatch: (data: Record<string, unknown>) => this.post("/agents/runtime/dispatch", data),
    health: () => this.get("/agents/health"),
    metrics: () => this.get("/agents/runtime/metrics"),
  };
  memory = { get: (sid: string) => this.get(`/memory/${sid}`) };
  kernel = { execute: (data: Record<string, unknown>) => this.post("/kernel/execute", data) };
  goals = {
    list: (uid: string) => this.get(`/goals/${uid}`),
    create: (uid: string, data: Record<string, unknown>) => this.post(`/goals/${uid}`, data),
    analyze: (uid: string) => this.get(`/goals/${uid}/analyze`),
  };
  tasks = {
    list: (p?: Record<string, string>) => this.get("/tasks", p),
    create: (data: Record<string, unknown>) => this.post("/tasks", data),
    get: (id: string) => this.get(`/tasks/${id}`),
  };
  workflows = {
    list: () => this.get("/workflows"),
    create: (data: Record<string, unknown>) => this.post("/workflows", data),
    get: (id: string) => this.get(`/workflows/${id}`),
    execute: (data: Record<string, unknown>) => this.post("/workflows/executions", data),
    health: () => this.get("/workflows/health"),
    metrics: () => this.get("/workflows/metrics"),
  };
  scheduler = {
    listJobs: () => this.get("/scheduler/jobs"),
    createJob: (data: Record<string, unknown>) => this.post("/scheduler/jobs", data),
    statistics: () => this.get("/scheduler/statistics"),
    health: () => this.get("/scheduler/health"),
  };
  tools = {
    list: () => this.get("/tools"),
    register: (data: Record<string, unknown>) => this.post("/tools/register", data),
    metrics: () => this.get("/tools/metrics"),
  };
  rag = {
    query: (data: Record<string, unknown>) => this.post("/rag/query", data),
    index: (data: Record<string, unknown>) => this.post("/rag/index", data),
    health: () => this.get("/rag/health"),
    metrics: () => this.get("/rag/metrics"),
    statistics: () => this.get("/rag/statistics"),
  };
  vectorMemory = {
    search: (data: Record<string, unknown>) => this.post("/vector-memory/search", data),
    store: (data: Record<string, unknown>) => this.post("/vector-memory/store", data),
    statistics: () => this.get("/vector-memory/statistics"),
    health: () => this.get("/vector-memory/health"),
  };
  events = {
    list: (p?: Record<string, string>) => this.get("/events", p),
    publish: (data: Record<string, unknown>) => this.post("/events/publish", data),
    statistics: () => this.get("/events/statistics"),
  };
  plugins = {
    list: () => this.get("/plugins/"),
    register: (data: Record<string, unknown>) => this.post("/plugins/", data),
    health: () => this.get("/plugins/health"),
    statistics: () => this.get("/plugins/statistics"),
  };
  knowledgeGraph = {
    entities: (p?: Record<string, string>) => this.get("/knowledge-graph/entities", p),
    createEntity: (data: Record<string, unknown>) => this.post("/knowledge-graph/entities", data),
    search: (data: Record<string, unknown>) => this.post("/knowledge-graph/search", data),
    validate: () => this.get("/knowledge-graph/validate"),
  };
  learning = {
    artifacts: () => this.get("/learning/artifacts"),
    extract: (data: Record<string, unknown>) => this.post("/learning/extract", data),
    stats: () => this.get("/learning/stats"),
  };
  observability = {
    health: () => this.get("/observability/health"),
    metrics: () => this.get("/observability/metrics"),
    traces: (p?: Record<string, string>) => this.get("/observability/traces", p),
    logs: (p?: Record<string, string>) => this.get("/observability/logs", p),
    diagnostics: () => this.get("/observability/diagnostics"),
    alerts: () => this.get("/observability/alerts"),
  };
  deployment = {
    health: () => this.get("/deployment/health"),
    readiness: () => this.get("/deployment/readiness"),
    diagnostics: () => this.get("/deployment/diagnostics"),
    configuration: () => this.get("/deployment/configuration"),
    metrics: () => this.get("/deployment/metrics"),
  };
  scaling = {
    health: () => this.get("/scaling/health"),
    workers: () => this.get("/scaling/workers"),
    cache: () => this.get("/scaling/cache"),
    resources: () => this.get("/scaling/resources"),
    metrics: () => this.get("/scaling/metrics"),
  };
  security = {
    health: () => this.get("/security/health"),
    statistics: () => this.get("/security/statistics"),
    roles: () => this.get("/security/rbac/roles"),
    auditLog: (p?: Record<string, string>) => this.get("/security/audit", p),
  };
  enterprise = {
    status: () => this.get("/enterprise/status"),
    organizations: () => this.get("/enterprise/organizations"),
    tenants: () => this.get("/enterprise/tenants"),
    metrics: () => this.get("/enterprise/metrics"),
    audit: (p?: Record<string, string>) => this.get("/enterprise/audit", p),
  };
  profile = { get: (uid: string) => this.get(`/profile/${uid}`) };
}

export const novaAPI = new NovaAPI();
// Backward compatibility alias
export const api = novaAPI;

/**
 * Sync the API client with the current auth token.
 * Call this when token changes (login/logout).
 */
export function syncAuthToken(token: string) {
  if (token) {
    novaAPI.setAuthToken(token);
  } else {
    // Clear the auth header by resetting headers
    novaAPI.setAuthToken("");
  }
}
