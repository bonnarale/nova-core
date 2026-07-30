"use client";

import { api } from "./api";

export interface NovaDashboardData {
  system_status: {
    status?: string;
    lifecycle?: { phase: string };
    metrics?: Record<string, unknown>;
    [key: string]: unknown;
  };
  objectives: { count: number; items: Array<{ id: string; title: string; status: string; progress: number; priority: number; category: string; tasks?: unknown[]; goals?: unknown[]; milestones?: unknown[] }> };
  projects: { count: number; items: Array<{ id: string; name: string; status: string; progress: number; objective_id?: string; phases?: unknown[]; milestones?: unknown[] }> };
  approvals: { count: number; items: Array<{ id: string; action_type: string; description: string; risk_level: string; status: string; created_at: string; metadata?: Record<string, unknown> }> };
  recommendations: { count: number; items: Array<{ id: string; category: string; title: string; description: string; priority: string; status: string }> };
  backlog: { count: number; items: Array<{ id: string; title: string; description: string; category: string; priority: number; status: string; source: string }> };
  roadmaps: { count: number; items: Array<{ id: string; name: string; description: string; status: string; duration_years: number; phases: unknown[] }> };
  metrics: Record<string, unknown>;
  lifecycle: Record<string, unknown>;
}

export interface ChatResponse {
  response: string;
  analysis?: Record<string, unknown>;
  actions_taken?: string[];
  objectives?: Array<{ id: string; title: string; status: string; priority: number; category: string }>;
  projects?: Array<{ id: string; name: string; status: string; objective_id?: string }>;
  milestones?: Array<{ id: string; title: string; status: string; objective_id?: string; project_id?: string }>;
  tasks?: Array<{ id: string; title: string; status: string; priority: number; objective_id?: string; project_id?: string }>;
  roadmap?: { id: string; name: string; status: string; phases: unknown[] } | null;
  approval_required?: boolean;
  timestamp?: string;
}

export interface Objective {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  progress: number;
  created_at: string;
  tasks?: Array<{ id: string; title: string; status: string }>;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  status: string;
  progress: number;
  phase?: string;
  phases?: Array<{ name: string; status: string; progress: number }>;
  created_at: string;
  milestones?: Array<{ id: string; title: string; status: string; due_date?: string }>;
  tasks_count?: number;
  completed_tasks?: number;
}

export interface Roadmap {
  id: string;
  name: string;
  description: string;
  status: string;
  start_year: number;
  end_year: number;
  phases: Array<{ id: string; name: string; status: string; start_date: string; end_date: string; progress: number }>;
  created_at: string;
}

export interface BacklogItem {
  id: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  category: string;
  created_at: string;
  estimated_effort?: string;
}

export interface Approval {
  id: string;
  title: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  created_at: string;
  requested_by?: string;
  details?: Record<string, unknown>;
  mandatory?: boolean;
}

export interface Recommendation {
  id: string;
  title: string;
  description: string;
  type: string;
  priority: string;
  status: string;
  created_at: string;
  reasoning?: string;
}

export interface MemoryStatus {
  learning_status: {
    total_artifacts: number;
    active_investigations: number;
    last_extraction?: string;
  };
  vector_memory: {
    total_vectors: number;
    dimensions: number;
    index_size?: number;
    health: string;
  };
  knowledge_graph: {
    total_entities: number;
    total_relations: number;
    health: string;
  };
  context_status: {
    active_contexts: number;
    total_tokens_used: number;
    max_tokens: number;
  };
}

export interface ObservabilityData {
  health: {
    status: string;
    uptime: number;
    services: Array<{ name: string; status: string; latency_ms?: number }>;
  };
  metrics: {
    requests_total: number;
    requests_per_second: number;
    error_rate: number;
    avg_latency_ms: number;
    p95_latency_ms: number;
    p99_latency_ms: number;
  };
  traces: Array<{ id: string; name: string; duration_ms: number; status: string; timestamp: string }>;
  diagnostics: Array<{ component: string; status: string; message: string; timestamp: string }>;
  alerts: Array<{ id: string; severity: string; message: string; timestamp: string; acknowledged: boolean }>;
}

export interface ToolInfo {
  id: string;
  name: string;
  description: string;
  status: string;
  type: string;
  executions: number;
  success_rate: number;
  avg_latency_ms: number;
  last_used?: string;
}

export interface ToolsData {
  tools: ToolInfo[];
  metrics: {
    total_executions: number;
    success_rate: number;
    avg_latency_ms: number;
    active_tools: number;
  };
  recent_executions: Array<{ id: string; tool_name: string; status: string; duration_ms: number; timestamp: string }>;
}

export interface ActivityEntry {
  id: string;
  goal_id: string | null;
  goal_title: string | null;
  action: string;
  status: string;
  goal_priority: number | null;
  approval_id: string | null;
  reason: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

class NovaWebAPI {
  private client = api;

  async dashboard(): Promise<NovaDashboardData> {
    try {
      return await this.client.get<NovaDashboardData>("/nova-web/dashboard");
    } catch {
      return {
        system_status: {},
        objectives: { count: 0, items: [] },
        projects: { count: 0, items: [] },
        approvals: { count: 0, items: [] },
        recommendations: { count: 0, items: [] },
        backlog: { count: 0, items: [] },
        roadmaps: { count: 0, items: [] },
        metrics: {},
        lifecycle: {},
      };
    }
  }

  async chat(message: string): Promise<ChatResponse> {
    return this.client.post<ChatResponse>("/nova-web/chat", { message });
  }

  async objectives(): Promise<Objective[]> {
    try {
      return await this.client.get<Objective[]>("/nova-web/objectives");
    } catch {
      return [];
    }
  }

  async projects(): Promise<Project[]> {
    try {
      return await this.client.get<Project[]>("/nova-web/projects");
    } catch {
      return [];
    }
  }

  async createProject(data: { name: string; description: string }): Promise<Project> {
    return this.client.post<Project>("/nova-web/projects", data);
  }

  async roadmaps(): Promise<Roadmap[]> {
    try {
      return await this.client.get<Roadmap[]>("/nova-web/roadmaps");
    } catch {
      return [];
    }
  }

  async createRoadmap(data: { name: string; description: string; start_year: number; end_year: number }): Promise<Roadmap> {
    return this.client.post<Roadmap>("/nova-web/roadmaps", data);
  }

  async backlog(): Promise<BacklogItem[]> {
    try {
      return await this.client.get<BacklogItem[]>("/nova-web/backlog");
    } catch {
      return [];
    }
  }

  async createBacklogItem(data: { title: string; description: string; priority: string; category: string }): Promise<BacklogItem> {
    return this.client.post<BacklogItem>("/nova-web/backlog", data);
  }

  async approvals(): Promise<Approval[]> {
    try {
      return await this.client.get<Approval[]>("/nova-web/approvals");
    } catch {
      return [];
    }
  }

  async approve(id: string, reason?: string): Promise<{ status: string }> {
    return this.client.post<{ status: string }>(`/nova-web/approvals/${id}/approve`, { reason });
  }

  async reject(id: string, reason?: string): Promise<{ status: string }> {
    return this.client.post<{ status: string }>(`/nova-web/approvals/${id}/reject`, { reason });
  }

  async approvalHistory(): Promise<Approval[]> {
    try {
      return await this.client.get<Approval[]>("/nova-web/approvals/history");
    } catch {
      return [];
    }
  }

  async recommendations(): Promise<Recommendation[]> {
    try {
      return await this.client.get<Recommendation[]>("/nova-web/recommendations");
    } catch {
      return [];
    }
  }

  async acceptRecommendation(id: string): Promise<{ status: string }> {
    return this.client.post<{ status: string }>(`/nova-web/recommendations/${id}/accept`);
  }

  async memory(): Promise<MemoryStatus> {
    try {
      return await this.client.get<MemoryStatus>("/nova-web/memory");
    } catch {
      return {
        learning_status: { total_artifacts: 0, active_investigations: 0 },
        vector_memory: { total_vectors: 0, dimensions: 0, health: "unknown" },
        knowledge_graph: { total_entities: 0, total_relations: 0, health: "unknown" },
        context_status: { active_contexts: 0, total_tokens_used: 0, max_tokens: 0 },
      };
    }
  }

  async observability(): Promise<ObservabilityData> {
    try {
      return await this.client.get<ObservabilityData>("/nova-web/observability");
    } catch {
      return {
        health: { status: "unknown", uptime: 0, services: [] },
        metrics: { requests_total: 0, requests_per_second: 0, error_rate: 0, avg_latency_ms: 0, p95_latency_ms: 0, p99_latency_ms: 0 },
        traces: [],
        diagnostics: [],
        alerts: [],
      };
    }
  }

  async tools(): Promise<ToolsData> {
    try {
      return await this.client.get<ToolsData>("/nova-web/tools");
    } catch {
      return {
        tools: [],
        metrics: { total_executions: 0, success_rate: 0, avg_latency_ms: 0, active_tools: 0 },
        recent_executions: [],
      };
    }
  }

  async fetchRecentActivity(limit: number = 20): Promise<ActivityEntry[]> {
    try {
      const response = await this.client.get<{ entries: ActivityEntry[]; total: number }>(
        `/api/v1/activity/recent?limit=${limit}`
      );
      return response.entries || [];
    } catch {
      return [];
    }
  }
}

export const novaWeb = new NovaWebAPI();
