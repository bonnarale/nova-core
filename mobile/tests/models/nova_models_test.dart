import 'package:flutter_test/flutter_test.dart';
import 'package:nova_core_mobile/models/nova_models.dart';

void main() {
  group('HealthResponse', () {
    test('fromJson parses correctly', () {
      final json = {'status': 'healthy', 'version': '1.0.0', 'uptime': 3600, 'services': [{'name': 'db', 'status': 'ok', 'latency_ms': 5}]};
      final h = HealthResponse.fromJson(json);
      expect(h.status, 'healthy');
      expect(h.version, '1.0.0');
      expect(h.uptime, 3600.0);
      expect(h.services.length, 1);
      expect(h.services[0].name, 'db');
    });

    test('fromJson handles missing fields', () {
      final h = HealthResponse.fromJson({});
      expect(h.status, 'unknown');
      expect(h.version, '0.0.0');
      expect(h.services, isEmpty);
    });
  });

  group('Agent', () {
    test('fromJson parses correctly', () {
      final json = {'id': 'a1', 'name': 'Nova', 'role': 'assistant', 'status': 'active', 'capabilities': ['chat'], 'created_at': '2024-01-01T00:00:00Z'};
      final a = Agent.fromJson(json);
      expect(a.id, 'a1');
      expect(a.name, 'Nova');
      expect(a.role, 'assistant');
      expect(a.status, 'active');
      expect(a.capabilities, ['chat']);
    });

    test('fromJson handles empty', () {
      final a = Agent.fromJson({});
      expect(a.id, '');
      expect(a.name, '');
      expect(a.capabilities, isEmpty);
    });
  });

  group('Task', () {
    test('fromJson parses correctly', () {
      final json = {'id': 't1', 'title': 'Test Task', 'status': 'pending', 'priority': 'high', 'assigned_agent': 'agent-1'};
      final t = Task.fromJson(json);
      expect(t.id, 't1');
      expect(t.title, 'Test Task');
      expect(t.status, 'pending');
      expect(t.priority, 'high');
      expect(t.assignedAgent, 'agent-1');
    });
  });

  group('Workflow', () {
    test('fromJson parses correctly', () {
      final json = {'id': 'w1', 'name': 'Pipeline', 'status': 'active', 'description': 'Main workflow', 'steps_count': 5};
      final wf = Workflow.fromJson(json);
      expect(wf.id, 'w1');
      expect(wf.name, 'Pipeline');
      expect(wf.stepsCount, 5);
    });
  });

  group('Goal', () {
    test('fromJson parses correctly', () {
      final json = {'id': 'g1', 'title': 'Improve', 'description': 'Get better', 'status': 'active', 'priority': 'high', 'progress': 42, 'tasks': [{'id': 'gt1', 'title': 'Sub task', 'completed': true}]};
      final g = Goal.fromJson(json);
      expect(g.id, 'g1');
      expect(g.progress, 42);
      expect(g.tasks.length, 1);
      expect(g.tasks[0].completed, true);
    });
  });

  group('ChatMessage', () {
    test('creates correctly', () {
      final msg = ChatMessage(role: 'user', content: 'Hello', timestamp: DateTime(2024, 1, 1));
      expect(msg.role, 'user');
      expect(msg.content, 'Hello');
      expect(msg.agentId, isNull);
    });
  });

  group('MemoryEntry', () {
    test('fromJson parses correctly', () {
      final json = {'id': 'm1', 'content': 'Remember this', 'category': 'fact', 'importance': 8, 'tags': ['important']};
      final m = MemoryEntry.fromJson(json);
      expect(m.id, 'm1');
      expect(m.category, 'fact');
      expect(m.importance, 8);
      expect(m.tags, ['important']);
    });
  });

  group('RAGCollection', () {
    test('fromJson parses correctly', () {
      final json = {'id': 'r1', 'name': 'docs', 'document_count': 100, 'vector_count': 500, 'status': 'active'};
      final r = RAGCollection.fromJson(json);
      expect(r.name, 'docs');
      expect(r.documentCount, 100);
      expect(r.vectorCount, 500);
    });
  });

  group('Plugin', () {
    test('fromJson parses correctly', () {
      final json = {'id': 'p1', 'name': 'MyPlugin', 'description': 'Desc', 'version': '1.0', 'status': 'active', 'author': 'Me', 'enabled': true};
      final p = Plugin.fromJson(json);
      expect(p.name, 'MyPlugin');
      expect(p.enabled, true);
      expect(p.version, '1.0');
    });
  });

  group('SystemEvent', () {
    test('fromJson parses correctly', () {
      final json = {'id': 'e1', 'type': 'alert', 'source': 'system', 'message': 'CPU high', 'severity': 'warning'};
      final e = SystemEvent.fromJson(json);
      expect(e.type, 'alert');
      expect(e.severity, 'warning');
    });
  });

  group('ScheduleJob', () {
    test('fromJson parses correctly', () {
      final json = {'id': 'j1', 'name': 'cleanup', 'cron': '0 * * * *', 'task_type': 'maintenance', 'status': 'active', 'enabled': true, 'next_run': '2024-01-01T01:00:00Z'};
      final j = ScheduleJob.fromJson(json);
      expect(j.name, 'cleanup');
      expect(j.cron, '0 * * * *');
      expect(j.enabled, true);
    });
  });

  group('Deployment', () {
    test('fromJson parses correctly', () {
      final json = {'id': 'd1', 'version': '1.0.0', 'environment': 'production', 'status': 'active', 'deployed_at': '2024-01-01T00:00:00Z', 'deployed_by': 'admin'};
      final d = Deployment.fromJson(json);
      expect(d.version, '1.0.0');
      expect(d.environment, 'production');
    });
  });

  group('ObservabilityData', () {
    test('fromJson parses correctly', () {
      final json = {'requests_per_second': 10.5, 'avg_latency_ms': 45.2, 'error_rate': 0.01, 'active_connections': 42};
      final o = ObservabilityData.fromJson(json);
      expect(o.requestsPerSecond, 10.5);
      expect(o.activeConnections, 42);
    });
  });
}
