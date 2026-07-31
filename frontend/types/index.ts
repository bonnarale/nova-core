export interface Configuration {
  baseUrl: string;
  wsUrl: string;
  apiKey?: string;
  bearerToken?: string;
  timeout: number;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  permissions: string[];
}

export interface NavItem {
  label: string;
  href: string;
  icon?: string;
  children?: NavItem[];
  badge?: string | number;
}

export interface DashboardCard {
  title: string;
  value: string | number;
  change?: number;
  trend?: "up" | "down" | "stable";
  icon?: string;
}

export interface ChartData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
    color?: string;
  }>;
}

export interface TableColumn<T = unknown> {
  key: string;
  label: string;
  sortable?: boolean;
  render?: (value: unknown, row: T) => React.ReactNode;
  width?: string;
}

export interface Notification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  message?: string;
  timestamp: number;
  read: boolean;
}

export interface WorkflowNode {
  id: string;
  type: string;
  label: string;
  x: number;
  y: number;
  config?: Record<string, unknown>;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  timestamp: number;
  agentId?: string;
  toolCalls?: Array<{ name: string; args: unknown; result?: unknown }>;
}

export interface Theme {
  name: string;
  colors: Record<string, string>;
}

export type ServiceStatus = "healthy" | "degraded" | "down" | "unknown";

export interface Agent {
  id: string;
  name: string;
  role: string;
  status: string;
  capabilities: string[];
  created_at: string;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  objective_id?: string;
  created_at: string;
}

export interface Workflow {
  id: string;
  name: string;
  description?: string;
  status: string;
  steps: unknown[];
  created_at: string;
}

export interface Goal {
  id: string;
  title: string;
  description?: string;
  status: string;
  target_date?: string;
  created_at: string;
}

export interface HealthData {
  status: string;
  version?: string;
  uptime?: number;
  [key: string]: unknown;
}

export interface MemoryEntry {
  id: string;
  key: string;
  content: string;
  type?: string;
  created_at: string;
}
