class HealthResponse {
  final String status;
  final String version;
  final double uptime;
  final List<ServiceHealth> services;

  HealthResponse({required this.status, required this.version, required this.uptime, required this.services});

  factory HealthResponse.fromJson(Map<String, dynamic> json) {
    return HealthResponse(
      status: json['status'] as String? ?? 'unknown',
      version: json['version'] as String? ?? '0.0.0',
      uptime: (json['uptime'] as num?)?.toDouble() ?? 0,
      services: (json['services'] as List<dynamic>? ?? []).map((s) => ServiceHealth.fromJson(s)).toList(),
    );
  }
}

class ServiceHealth {
  final String name;
  final String status;
  final double? latencyMs;
  ServiceHealth({required this.name, required this.status, this.latencyMs});
  factory ServiceHealth.fromJson(Map<String, dynamic> json) {
    return ServiceHealth(name: json['name'] ?? '', status: json['status'] ?? 'unknown', latencyMs: (json['latency_ms'] as num?)?.toDouble());
  }
}

class Agent {
  final String id;
  final String name;
  final String role;
  final String status;
  final List<String> capabilities;
  final DateTime createdAt;

  Agent({required this.id, required this.name, required this.role, required this.status, this.capabilities = const [], required this.createdAt});

  factory Agent.fromJson(Map<String, dynamic> json) {
    return Agent(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      role: json['role'] ?? '',
      status: json['status'] ?? 'inactive',
      capabilities: (json['capabilities'] as List<dynamic>? ?? []).cast<String>(),
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
    );
  }
}

class Task {
  final String id;
  final String title;
  final String status;
  final String priority;
  final String? assignedAgent;
  final DateTime createdAt;
  final DateTime? dueDate;

  Task({required this.id, required this.title, required this.status, required this.priority, this.assignedAgent, required this.createdAt, this.dueDate});

  factory Task.fromJson(Map<String, dynamic> json) {
    return Task(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      status: json['status'] ?? 'pending',
      priority: json['priority'] ?? 'medium',
      assignedAgent: json['assigned_agent'],
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
      dueDate: json['due_date'] != null ? DateTime.tryParse(json['due_date']) : null,
    );
  }
}

class Workflow {
  final String id;
  final String name;
  final String status;
  final String description;
  final int stepsCount;
  final DateTime createdAt;

  Workflow({required this.id, required this.name, required this.status, required this.description, required this.stepsCount, required this.createdAt});

  factory Workflow.fromJson(Map<String, dynamic> json) {
    return Workflow(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      status: json['status'] ?? 'draft',
      description: json['description'] ?? '',
      stepsCount: json['steps_count'] ?? 0,
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
    );
  }
}

class Goal {
  final String id;
  final String title;
  final String description;
  final String status;
  final String priority;
  final int progress;
  final List<GoalTask> tasks;

  Goal({required this.id, required this.title, required this.description, required this.status, required this.priority, required this.progress, this.tasks = const []});

  factory Goal.fromJson(Map<String, dynamic> json) {
    return Goal(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      description: json['description'] ?? '',
      status: json['status'] ?? 'active',
      priority: json['priority'] ?? 'medium',
      progress: json['progress'] ?? 0,
      tasks: (json['tasks'] as List<dynamic>? ?? []).map((t) => GoalTask.fromJson(t)).toList(),
    );
  }
}

class GoalTask {
  final String id;
  final String title;
  final bool completed;
  GoalTask({required this.id, required this.title, required this.completed});
  factory GoalTask.fromJson(Map<String, dynamic> json) {
    return GoalTask(id: json['id'] ?? '', title: json['title'] ?? '', completed: json['completed'] ?? false);
  }
}

class ChatMessage {
  final String role;
  final String content;
  final DateTime timestamp;
  final String? agentId;
  ChatMessage({required this.role, required this.content, required this.timestamp, this.agentId});
}

class MemoryEntry {
  final String id;
  final String content;
  final String category;
  final int importance;
  final List<String> tags;
  final DateTime createdAt;

  MemoryEntry({required this.id, required this.content, required this.category, required this.importance, this.tags = const [], required this.createdAt});

  factory MemoryEntry.fromJson(Map<String, dynamic> json) {
    return MemoryEntry(
      id: json['id'] ?? '',
      content: json['content'] ?? '',
      category: json['category'] ?? 'general',
      importance: json['importance'] ?? 5,
      tags: (json['tags'] as List<dynamic>? ?? []).cast<String>(),
      createdAt: DateTime.tryParse(json['created_at'] ?? '') ?? DateTime.now(),
    );
  }
}

class RAGCollection {
  final String id;
  final String name;
  final int documentCount;
  final int vectorCount;
  final String status;
  final String? description;

  RAGCollection({required this.id, required this.name, required this.documentCount, required this.vectorCount, required this.status, this.description});

  factory RAGCollection.fromJson(Map<String, dynamic> json) {
    return RAGCollection(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      documentCount: json['document_count'] ?? 0,
      vectorCount: json['vector_count'] ?? 0,
      status: json['status'] ?? 'active',
      description: json['description'],
    );
  }
}

class Plugin {
  final String id;
  final String name;
  final String description;
  final String version;
  final String status;
  final String author;
  final bool enabled;

  Plugin({required this.id, required this.name, required this.description, required this.version, required this.status, required this.author, required this.enabled});

  factory Plugin.fromJson(Map<String, dynamic> json) {
    return Plugin(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      description: json['description'] ?? '',
      version: json['version'] ?? '0.0.0',
      status: json['status'] ?? 'inactive',
      author: json['author'] ?? '',
      enabled: json['enabled'] ?? false,
    );
  }
}

class SystemEvent {
  final String id;
  final String type;
  final String source;
  final String message;
  final String severity;
  final DateTime timestamp;

  SystemEvent({required this.id, required this.type, required this.source, required this.message, required this.severity, required this.timestamp});

  factory SystemEvent.fromJson(Map<String, dynamic> json) {
    return SystemEvent(
      id: json['id'] ?? '',
      type: json['type'] ?? '',
      source: json['source'] ?? '',
      message: json['message'] ?? '',
      severity: json['severity'] ?? 'info',
      timestamp: DateTime.tryParse(json['timestamp'] ?? '') ?? DateTime.now(),
    );
  }
}

class ObservabilityData {
  final double requestsPerSecond;
  final double avgLatencyMs;
  final double errorRate;
  final int activeConnections;

  ObservabilityData({required this.requestsPerSecond, required this.avgLatencyMs, required this.errorRate, required this.activeConnections});

  factory ObservabilityData.fromJson(Map<String, dynamic> json) {
    return ObservabilityData(
      requestsPerSecond: (json['requests_per_second'] as num?)?.toDouble() ?? 0,
      avgLatencyMs: (json['avg_latency_ms'] as num?)?.toDouble() ?? 0,
      errorRate: (json['error_rate'] as num?)?.toDouble() ?? 0,
      activeConnections: json['active_connections'] ?? 0,
    );
  }
}

class ScheduleJob {
  final String id;
  final String name;
  final String cron;
  final String taskType;
  final String status;
  final bool enabled;
  final DateTime? lastRun;
  final DateTime nextRun;

  ScheduleJob({required this.id, required this.name, required this.cron, required this.taskType, required this.status, required this.enabled, this.lastRun, required this.nextRun});

  factory ScheduleJob.fromJson(Map<String, dynamic> json) {
    return ScheduleJob(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      cron: json['cron'] ?? '',
      taskType: json['task_type'] ?? '',
      status: json['status'] ?? 'active',
      enabled: json['enabled'] ?? true,
      lastRun: json['last_run'] != null ? DateTime.tryParse(json['last_run']) : null,
      nextRun: DateTime.tryParse(json['next_run'] ?? '') ?? DateTime.now(),
    );
  }
}

class Deployment {
  final String id;
  final String version;
  final String environment;
  final String status;
  final DateTime deployedAt;
  final String deployedBy;

  Deployment({required this.id, required this.version, required this.environment, required this.status, required this.deployedAt, required this.deployedBy});

  factory Deployment.fromJson(Map<String, dynamic> json) {
    return Deployment(
      id: json['id'] ?? '',
      version: json['version'] ?? '',
      environment: json['environment'] ?? '',
      status: json['status'] ?? 'pending',
      deployedAt: DateTime.tryParse(json['deployed_at'] ?? '') ?? DateTime.now(),
      deployedBy: json['deployed_by'] ?? '',
    );
  }
}
