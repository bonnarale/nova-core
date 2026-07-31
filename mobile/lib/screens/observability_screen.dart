import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../widgets/common_widgets.dart';

class ObservabilityScreen extends StatefulWidget {
  const ObservabilityScreen({super.key});
  @override
  State<ObservabilityScreen> createState() => _ObservabilityScreenState();
}

class _ObservabilityScreenState extends State<ObservabilityScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _error;
  int _selectedTab = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repo = context.read<AppProvider>().repository;
      _data = await repo.getObservabilityOverview();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final metrics = _data != null ? Map<String, dynamic>.from(_data!['metrics'] ?? {}) : <String, dynamic>{};
    final traces = _data != null ? List<Map<String, dynamic>>.from((_data!['traces'] ?? []).map((t) => Map<String, dynamic>.from(t))) : <Map<String, dynamic>>[];
    final logs = _data != null ? List<Map<String, dynamic>>.from((_data!['logs'] ?? []).map((l) => Map<String, dynamic>.from(l))) : <Map<String, dynamic>>[];

    final rps = (metrics['requests_per_second'] ?? 0).toDouble();
    final latency = (metrics['avg_latency_ms'] ?? 0).toDouble();
    final errorRate = (metrics['error_rate'] ?? 0).toDouble();
    final connections = metrics['active_connections'] ?? 0;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Observability', description: 'Metrics, traces, and logs'),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _data == null
                        ? const EmptyState(title: 'No data', description: 'Observability data unavailable', icon: Icons.monitoring_outlined)
                        : ListView(
                            children: [
                              Row(
                                children: [
                                  Expanded(child: MetricCard(title: 'Req/s', value: rps.toStringAsFixed(1), icon: '📈')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Avg Latency', value: '${latency.toStringAsFixed(0)}ms', icon: '⚡')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Error Rate', value: '${errorRate.toStringAsFixed(2)}%', icon: '❌')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Connections', value: '$connections', icon: '🔗')),
                                ],
                              ),
                              const SizedBox(height: 16),
                              Container(
                                decoration: BoxDecoration(color: const Color(0xFF1A1A2E), borderRadius: BorderRadius.circular(8)),
                                child: Row(
                                  children: [
                                    _tabButton('Traces', 0),
                                    _tabButton('Logs', 1),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 8),
                              if (_selectedTab == 0) ...[
                                if (traces.isEmpty)
                                  const Padding(
                                    padding: EdgeInsets.all(32),
                                    child: EmptyState(title: 'No traces', icon: Icons.account_tree_outlined),
                                  )
                                else
                                  ...traces.map((trace) => Card(
                                        margin: const EdgeInsets.only(bottom: 8),
                                        child: Padding(
                                          padding: const EdgeInsets.all(12),
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Row(
                                                children: [
                                                  Expanded(child: Text(trace['operation'] ?? 'Unknown', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0)))),
                                                  Text('${trace['duration_ms'] ?? 0}ms', style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8))),
                                                ],
                                              ),
                                              const SizedBox(height: 4),
                                              Row(
                                                children: [
                                                  StatusBadge(status: trace['status'] ?? 'unknown'),
                                                  const SizedBox(width: 8),
                                                  Text(trace['service'] ?? '', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                                ],
                                              ),
                                            ],
                                          ),
                                        ),
                                      )),
                              ],
                              if (_selectedTab == 1) ...[
                                if (logs.isEmpty)
                                  const Padding(
                                    padding: EdgeInsets.all(32),
                                    child: EmptyState(title: 'No logs', icon: Icons.article_outlined),
                                  )
                                else
                                  ...logs.map((log) => Card(
                                        margin: const EdgeInsets.only(bottom: 8),
                                        child: Padding(
                                          padding: const EdgeInsets.all(12),
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Row(
                                                children: [
                                                  StatusBadge(status: log['level'] ?? 'info'),
                                                  const SizedBox(width: 8),
                                                  Text(log['service'] ?? '', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                                  const Spacer(),
                                                  Text(log['timestamp'] ?? '', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                                ],
                                              ),
                                              const SizedBox(height: 4),
                                              Text(log['message'] ?? '', style: const TextStyle(fontSize: 12, color: Color(0xFFE8E8F0)), maxLines: 3, overflow: TextOverflow.ellipsis),
                                            ],
                                          ),
                                        ),
                                      )),
                              ],
                            ],
                          ),
          ),
        ],
      ),
    );
  }

  Widget _tabButton(String label, int index) {
    final selected = _selectedTab == index;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _selectedTab = index),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: selected ? const Color(0xFF6366F1) : Colors.transparent,
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(label, textAlign: TextAlign.center, style: TextStyle(fontSize: 13, color: selected ? Colors.white : const Color(0xFF8888A8), fontWeight: FontWeight.w500)),
        ),
      ),
    );
  }
}
