import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../api/api_client.dart';
import '../../models/nova_models.dart';

class NovaRepository {
  final NovaApiClient _client;
  final SharedPreferences? _prefs;

  NovaRepository({required NovaApiClient client, SharedPreferences? prefs})
      : _client = client,
        _prefs = prefs;

  void setToken(String? token) => _client.setToken(token);

  Future<HealthResponse> getHealth() async => _client.get<HealthResponse>('/api/v1/health', parser: (json) => HealthResponse.fromJson(json));

  Future<List<Agent>> getAgents() async => _client.get<List<Agent>>('/api/v1/agents', parser: (json) => (json as List).map((e) => Agent.fromJson(e)).toList());

  Future<List<Task>> getTasks() async => _client.get<List<Task>>('/api/v1/tasks', parser: (json) => (json as List).map((e) => Task.fromJson(e)).toList());

  Future<List<Workflow>> getWorkflows() async => _client.get<List<Workflow>>('/api/v1/workflows', parser: (json) => (json as List).map((e) => Workflow.fromJson(e)).toList());

  Future<List<Goal>> getGoals() async => _client.get<List<Goal>>('/api/v1/goals', parser: (json) => (json as List).map((e) => Goal.fromJson(e)).toList());

  Future<List<MemoryEntry>> getMemory() async => _client.get<List<MemoryEntry>>('/api/v1/memory', parser: (json) => (json as List).map((e) => MemoryEntry.fromJson(e)).toList());

  Future<List<RAGCollection>> getRAGCollections() async => _client.get<List<RAGCollection>>('/api/v1/rag/collections', parser: (json) => (json as List).map((e) => RAGCollection.fromJson(e)).toList());

  Future<List<Plugin>> getPlugins() async => _client.get<List<Plugin>>('/api/v1/plugins', parser: (json) => (json as List).map((e) => Plugin.fromJson(e)).toList());

  Future<List<SystemEvent>> getEvents() async => _client.get<List<SystemEvent>>('/api/v1/events', parser: (json) => (json as List).map((e) => SystemEvent.fromJson(e)).toList());

  Future<List<ScheduleJob>> getScheduleJobs() async => _client.get<List<ScheduleJob>>('/api/v1/scheduler/jobs', parser: (json) => (json as List).map((e) => ScheduleJob.fromJson(e)).toList());

  Future<List<Deployment>> getDeploymentHistory() async => _client.get<List<Deployment>>('/api/v1/deployment/history', parser: (json) => (json as List).map((e) => Deployment.fromJson(e)).toList());

  Future<Map<String, dynamic>> getModels() async => _client.get('/api/v1/models');

  Future<Map<String, dynamic>> getTools() async => _client.get('/api/v1/tools');

  Future<Map<String, dynamic>> getSecurityStatus() async => _client.get('/api/v1/security/health');

  Future<Map<String, dynamic>> getEnterpriseStatus() async => _client.get('/api/v1/enterprise/status');

  Future<Map<String, dynamic>> getScalingStatus() async => _client.get('/api/v1/system/scaling');

  Future<Map<String, dynamic>> getSystemStatus() async => _client.get('/api/v1/system/status');

  Future<Map<String, dynamic>> getObservabilityOverview() async => _client.get('/api/v1/observability/overview');

  Future<Map<String, dynamic>> getAutonomyStatus() async => _client.get('/api/v1/agents/autonomy');

  // Offline cache
  Future<void> cacheData(String key, dynamic data) async {
    if (_prefs == null) return;
    await _prefs!.setString('cache_$key', jsonEncode(data));
    await _prefs!.setInt('cache_${key}_time', DateTime.now().millisecondsSinceEpoch);
  }

  dynamic getCachedData(String key, {Duration maxAge = const Duration(minutes: 5)}) {
    if (_prefs == null) return null;
    final timeStr = _prefs!.getInt('cache_${key}_time');
    if (timeStr == null) return null;
    final cachedTime = DateTime.fromMillisecondsSinceEpoch(timeStr);
    if (DateTime.now().difference(cachedTime) > maxAge) return null;
    final data = _prefs!.getString('cache_$key');
    if (data == null) return null;
    return jsonDecode(data);
  }

  Future<void> clearCache() async {
    if (_prefs == null) return;
    final keys = _prefs!.getKeys().where((k) => k.startsWith('cache_'));
    for (final key in keys) {
      await _prefs!.remove(key);
    }
  }
}
