export type HTTPMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface RequestOptions {
  method: HTTPMethod;
  path: string;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  headers?: Record<string, string>;
}

export interface StreamChunk {
  choices?: Array<{
    delta?: { content?: string };
    text?: string;
  }>;
  content?: string;
}

export interface WebSocketMessage {
  type: string;
  payload: Record<string, unknown>;
  id?: string;
  timestamp?: string;
}

export interface TelemetrySpan {
  name: string;
  startTime: number;
  endTime?: number;
  attributes: Record<string, unknown>;
  status: "ok" | "error";
}

export interface TelemetryMetrics {
  totalRequests: number;
  totalErrors: number;
  totalLatencyMs: number;
  requestsByEndpoint: Record<string, number>;
  errorsByType: Record<string, number>;
}
