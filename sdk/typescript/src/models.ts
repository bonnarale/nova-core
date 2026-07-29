export interface Message {
  role: string;
  content: string;
}

export interface ChatRequest {
  model: string;
  messages: Message[];
  provider?: string;
  agent_id?: string;
  session_id?: string;
  user_id?: string;
  use_cache?: boolean;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

export interface ChatResponse {
  response: Record<string, unknown>;
  provider: string;
  model: string;
  latency_ms: number;
  cache_hit: boolean;
  tokens_input: number;
  tokens_output: number;
}

export interface CreateAgentRequest {
  id: string;
  name: string;
  role: string;
  description?: string;
  system_prompt?: string;
  allowed_tools?: string[];
  memory_scope?: string;
  permissions?: Record<string, unknown>;
  supported_models?: string[];
}

export interface AgentResponse {
  id: string;
  name: string;
  role: string;
  description: string;
  status: string;
}

export interface CreateGoalRequest {
  title: string;
  description?: string;
  priority?: number;
}

export interface GoalResponse {
  id: string;
  user_id: string;
  title: string;
  description: string;
  status: string;
  priority: number;
  progress: number;
}

export interface CreateTaskRequest {
  goal: string;
  plan?: Record<string, unknown>;
  steps?: unknown[];
  dependencies?: string[];
  assigned_agent?: string;
}

export interface TaskResponse {
  id: string;
  goal: string;
  status: string;
  current_step: number;
}

export interface WorkflowCreate {
  name: string;
  description?: string;
  version?: string;
  steps?: Array<Record<string, unknown>>;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface WorkflowResponse {
  id: string;
  name: string;
  description: string;
  version: string;
  tags: string[];
}

export interface WorkflowExecutionCreate {
  workflow_id: string;
  input?: Record<string, unknown>;
  user_id?: string;
  session_id?: string;
  tags?: string[];
}

export interface WorkflowExecutionResponse {
  id: string;
  workflow_id: string;
  status: string;
  error?: string;
}

export interface CreateJobRequest {
  name: string;
  handler?: string;
  schedule?: string;
  params?: Record<string, unknown>;
  enabled?: boolean;
}

export interface JobResponse {
  id: string;
  name: string;
  status: string;
  enabled: boolean;
}

export interface RAGQueryRequest {
  query: string;
  top_k?: number;
  threshold?: number;
  filters?: Array<Record<string, unknown>>;
  user_id?: string;
  session_id?: string;
}

export interface RAGQueryResponse {
  query: string;
  context_text: string;
  citations: Array<Record<string, unknown>>;
  chunks_count: number;
  latency_ms: number;
}

export interface RAGIndexRequest {
  content: string;
  title?: string;
  source?: string;
  category?: string;
  tags?: string[];
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface EntityCreate {
  type: string;
  name: string;
  description?: string;
  tags?: string[];
  properties?: Record<string, unknown>;
  source?: string;
  confidence?: number;
}

export interface EntityResponse {
  id: string;
  type: string;
  name: string;
  description: string;
  status: string;
  confidence: number;
}

export interface RelationshipCreate {
  source_id: string;
  target_id: string;
  type: string;
  weight?: number;
}

export interface RelationshipResponse {
  id: string;
  source_id: string;
  target_id: string;
  type: string;
  weight: number;
  status: string;
}

export interface VectorRecord {
  content: string;
  embedding: number[];
  metadata?: Record<string, unknown>;
}

export interface VectorSearchResult {
  results: Array<Record<string, unknown>>;
  total: number;
}

export interface RegisterPluginRequest {
  name: string;
  version?: string;
  description?: string;
  plugin_type?: string;
  config?: Record<string, unknown>;
}

export interface PluginResponse {
  id: string;
  name: string;
  version: string;
  status: string;
}

export interface PublishEventRequest {
  event_type: string;
  source?: string;
  payload?: Record<string, unknown>;
  session_id?: string;
  user_id?: string;
}

export interface EventResponse {
  id: string;
  event_type: string;
  source: string;
  payload: Record<string, unknown>;
}

export interface APIResponse<T = unknown> {
  success: boolean;
  data: T;
  metadata: Record<string, unknown>;
  errors: Array<Record<string, unknown>>;
}

export interface PaginatedResponse<T = unknown> {
  success: boolean;
  data: T[];
  pagination: {
    total: number;
    page: number;
    page_size: number;
    has_next: boolean;
  };
}

export interface HealthResponse {
  status: string;
}
