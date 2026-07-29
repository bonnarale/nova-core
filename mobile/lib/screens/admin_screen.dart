import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../widgets/common_widgets.dart';

class AdminScreen extends StatefulWidget {
  const AdminScreen({super.key});
  @override
  State<AdminScreen> createState() => _AdminScreenState();
}

class _AdminScreenState extends State<AdminScreen> {
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
      _data = await repo.getSystemStatus();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final system = _data != null ? Map<String, dynamic>.from(_data!['system'] ?? {}) : <String, dynamic>{};
    final version = system['version'] ?? _data?['version'] ?? 'Unknown';
    final uptime = (system['uptime'] ?? _data?['uptime'] ?? 0).toDouble();
    final platform = system['platform'] ?? 'Unknown';
    final dartVersion = system['dart_version'] ?? 'Unknown';

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Admin', description: 'System administration and quick actions'),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _data == null
                        ? const EmptyState(title: 'No data', description: 'System data unavailable', icon: Icons.admin_panel_settings_outlined)
                        : ListView(
                            children: [
                              Row(
                                children: [
                                  Expanded(child: MetricCard(title: 'Version', value: '$version', icon: '📋')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Uptime', value: '${(uptime / 3600).toStringAsFixed(1)}h', icon: '⏱️')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Platform', value: '$platform', icon: '💻')),
                                ],
                              ),
                              const SizedBox(height: 16),
                              Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text('System Information', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                      const SizedBox(height: 12),
                                      _infoRow('Version', '$version'),
                                      _infoRow('Platform', '$platform'),
                                      _infoRow('Dart Version', '$dartVersion'),
                                      _infoRow('Uptime', '${(uptime / 3600).toStringAsFixed(1)} hours'),
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
                                      const Text('Quick Actions', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                      const SizedBox(height: 12),
                                      _actionButton(Icons.refresh, 'Refresh System', const Color(0xFF3B82F6), _load),
                                      const SizedBox(height: 8),
                                      _actionButton(Icons.restart_alt, 'Restart Services', const Color(0xFFF59E0B), () {}),
                                      const SizedBox(height: 8),
                                      _actionButton(Icons.update, 'Check Updates', const Color(0xFF22C55E), () {}),
                                      const SizedBox(height: 8),
                                      _actionButton(Icons.delete_sweep, 'Purge Cache', const Color(0xFFEF4444), () async {
                                        await context.read<AppProvider>().repository.clearCache();
                                        if (context.mounted) {
                                          ScaffoldMessenger.of(context).showSnackBar(
                                            const SnackBar(content: Text('Cache purged')),
                                          );
                                        }
                                      }),
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

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Text(label, style: const TextStyle(fontSize: 13, color: Color(0xFF8888A8))),
          const Spacer(),
          Text(value.toString(), style: const TextStyle(fontSize: 13, color: Color(0xFFE8E8F0))),
        ],
      ),
    );
  }

  Widget _actionButton(IconData icon, String label, Color color, VoidCallback onTap) {
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 0),
      leading: CircleAvatar(
        backgroundColor: color.withOpacity(0.15),
        child: Icon(icon, size: 20, color: color),
      ),
      title: Text(label, style: const TextStyle(color: Color(0xFFE8E8F0))),
      trailing: const Icon(Icons.chevron_right, color: Color(0xFF8888A8)),
      onTap: onTap,
    );
  }
}
