import { api as apiClient } from "@/lib/api";
import type { Agent, Task, Workflow, Goal, HealthData, MemoryEntry } from "@/types";

export const healthService = {
  check: () => apiClient.get<HealthData>("/api/v1/health"),
  detailed: () => apiClient.get<HealthData>("/api/v1/health/detailed"),
};

export const agentsService = {
  list: () => apiClient.get<Agent[]>("/api/v1/agents"),
  get: (id: string) => apiClient.get<Agent>(`/api/v1/agents/${id}`),
  create: (data: Partial<Agent>) => apiClient.post<Agent>("/api/v1/agents", data),
  update: (id: string, data: Partial<Agent>) => apiClient.put<Agent>(`/api/v1/agents/${id}`, data),
  delete: (id: string) => apiClient.delete(`/api/v1/agents/${id}`),
};

export const tasksService = {
  list: () => apiClient.get<Task[]>("/api/v1/tasks"),
  get: (id: string) => apiClient.get<Task>(`/api/v1/tasks/${id}`),
  create: (data: Partial<Task>) => apiClient.post<Task>("/api/v1/tasks", data),
  update: (id: string, data: Partial<Task>) => apiClient.put<Task>(`/api/v1/tasks/${id}`, data),
  complete: (id: string) => apiClient.post<Task>(`/api/v1/tasks/${id}/complete`),
};

export const workflowsService = {
  list: () => apiClient.get<Workflow[]>("/api/v1/workflows"),
  get: (id: string) => apiClient.get<Workflow>(`/api/v1/workflows/${id}`),
  create: (data: Partial<Workflow>) => apiClient.post<Workflow>("/api/v1/workflows", data),
  execute: (id: string) => apiClient.post(`/api/v1/workflows/${id}/execute`),
};

export const goalsService = {
  list: () => apiClient.get<Goal[]>("/api/v1/goals"),
  get: (id: string) => apiClient.get<Goal>(`/api/v1/goals/${id}`),
  create: (data: Partial<Goal>) => apiClient.post<Goal>("/api/v1/goals", data),
  update: (id: string, data: Partial<Goal>) => apiClient.put<Goal>(`/api/v1/goals/${id}`, data),
};

export const memoryService = {
  list: () => apiClient.get<MemoryEntry[]>("/api/v1/memory"),
  search: (query: string) => apiClient.get<MemoryEntry[]>(`/api/v1/memory/search?q=${encodeURIComponent(query)}`),
  create: (data: Partial<MemoryEntry>) => apiClient.post<MemoryEntry>("/api/v1/memory", data),
};

export const modelsService = {
  list: () => apiClient.get("/api/v1/models"),
  get: (id: string) => apiClient.get(`/api/v1/models/${id}`),
};

export const schedulerService = {
  jobs: () => apiClient.get("/api/v1/scheduler/jobs"),
  createJob: (data: Record<string, unknown>) => apiClient.post("/api/v1/scheduler/jobs", data),
  pauseJob: (id: string) => apiClient.post(`/api/v1/scheduler/jobs/${id}/pause`),
  resumeJob: (id: string) => apiClient.post(`/api/v1/scheduler/jobs/${id}/resume`),
};

export const deploymentService = {
  history: () => apiClient.get("/api/v1/deployment/history"),
  deploy: (data: Record<string, unknown>) => apiClient.post("/api/v1/deployment/deploy", data),
  rollback: (id: string) => apiClient.post(`/api/v1/deployment/rollback/${id}`),
};
