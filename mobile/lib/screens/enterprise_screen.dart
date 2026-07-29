import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../widgets/common_widgets.dart';

class EnterpriseScreen extends StatefulWidget {
  const EnterpriseScreen({super.key});
  @override
  State<EnterpriseScreen> createState() => _EnterpriseScreenState();
}

class _EnterpriseScreenState extends State<EnterpriseScreen> {
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
      _data = await repo.getEnterpriseStatus();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final features = _data != null ? Map<String, dynamic>.from(_data!['features'] ?? {}) : <String, dynamic>{};
    final enabledCount = features.values.where((v) => v == true).length;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Enterprise', description: 'Enterprise features and capabilities'),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _data == null
                        ? const EmptyState(title: 'No data', description: 'Enterprise status unavailable', icon: Icons.business_outlined)
                        : ListView(
                            children: [
                              Row(
                                children: [
                                  Expanded(child: MetricCard(title: 'Features', value: '${features.length}', icon: '🏢')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Enabled', value: '$enabledCount', icon: '✅')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Disabled', value: '${features.length - enabledCount}', icon: '⏸')),
                                ],
                              ),
                              const SizedBox(height: 16),
                              ...features.entries.map((entry) => Card(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    child: ListTile(
                                      leading: Icon(
                                        _getFeatureIcon(entry.key),
                                        color: entry.value == true ? const Color(0xFF22C55E) : const Color(0xFF8888A8),
                                      ),
                                      title: Text(
                                        _formatFeatureName(entry.key),
                                        style: const TextStyle(color: Color(0xFFE8E8F0)),
                                      ),
                                      subtitle: Text(
                                        entry.value == true ? 'Enabled' : 'Disabled',
                                        style: TextStyle(fontSize: 12, color: entry.value == true ? const Color(0xFF22C55E) : const Color(0xFF8888A8)),
                                      ),
                                      trailing: StatusBadge(status: entry.value == true ? 'active' : 'inactive'),
                                    ),
                                  )),
                            ],
                          ),
          ),
        ],
      ),
    );
  }

  String _formatFeatureName(String key) {
    return key.split('_').map((w) => w[0].toUpperCase() + w.substring(1)).join(' ');
  }

  IconData _getFeatureIcon(String key) {
    if (key.contains('sso')) return Icons.key;
    if (key.contains('audit')) return Icons.history;
    if (key.contains('rbac') || key.contains('role')) return Icons.admin_panel_settings;
    if (key.contains('compliance')) return Icons.verified;
    if (key.contains('backup')) return Icons.backup;
    if (key.contains('sla')) return Icons.timer;
    return Icons.extension;
  }
}
