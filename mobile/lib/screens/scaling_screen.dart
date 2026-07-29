import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../widgets/common_widgets.dart';

class ScalingScreen extends StatefulWidget {
  const ScalingScreen({super.key});
  @override
  State<ScalingScreen> createState() => _ScalingScreenState();
}

class _ScalingScreenState extends State<ScalingScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _error;

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
      _data = await repo.getScalingStatus();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final resources = _data != null ? Map<String, dynamic>.from(_data!['resources'] ?? {}) : <String, dynamic>{};
    final config = _data != null ? Map<String, dynamic>.from(_data!['config'] ?? {}) : <String, dynamic>{};

    final cpu = (resources['cpu'] ?? 0).toDouble();
    final memory = (resources['memory'] ?? 0).toDouble();
    final disk = (resources['disk'] ?? 0).toDouble();

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Scaling', description: 'Auto-scaling configuration and resource usage'),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _data == null
                        ? const EmptyState(title: 'No data', description: 'Scaling data unavailable', icon: Icons.speed_outlined)
                        : ListView(
                            children: [
                              Row(
                                children: [
                                  Expanded(child: MetricCard(title: 'CPU', value: '${cpu.toStringAsFixed(0)}%', icon: '💻')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Memory', value: '${memory.toStringAsFixed(0)}%', icon: '🧠')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Disk', value: '${disk.toStringAsFixed(0)}%', icon: '💾')),
                                ],
                              ),
                              const SizedBox(height: 16),
                              Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text('Resource Usage', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                      const SizedBox(height: 12),
                                      StatBar(label: 'CPU', value: cpu, color: _getColorForValue(cpu)),
                                      StatBar(label: 'Memory', value: memory, color: _getColorForValue(memory)),
                                      StatBar(label: 'Disk', value: disk, color: _getColorForValue(disk)),
                                    ],
                                  ),
                                ),
                              ),
                              const SizedBox(height: 8),
                              Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text('Scaling Configuration', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                      const SizedBox(height: 12),
                                      _configRow('Enabled', config['enabled'] == true ? 'Yes' : 'No'),
                                      _configRow('Min Instances', '${config['min_instances'] ?? 1}'),
                                      _configRow('Max Instances', '${config['max_instances'] ?? 10}'),
                                      _configRow('Scale Up Threshold', '${config['scale_up_threshold'] ?? 80}%'),
                                      _configRow('Scale Down Threshold', '${config['scale_down_threshold'] ?? 30}%'),
                                      _configRow('Cooldown Period', '${config['cooldown_seconds'] ?? 300}s'),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
          ),
        ],
      ),
    );
  }

  Color _getColorForValue(double value) {
    if (value >= 90) return const Color(0xFFEF4444);
    if (value >= 70) return const Color(0xFFF59E0B);
    return const Color(0xFF22C55E);
  }

  Widget _configRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Text(label, style: const TextStyle(fontSize: 13, color: Color(0xFF8888A8))),
          const Spacer(),
          Text(value, style: const TextStyle(fontSize: 13, color: Color(0xFFE8E8F0))),
        ],
      ),
    );
  }
}
