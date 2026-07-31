import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../widgets/common_widgets.dart';

class SecurityScreen extends StatefulWidget {
  const SecurityScreen({super.key});
  @override
  State<SecurityScreen> createState() => _SecurityScreenState();
}

class _SecurityScreenState extends State<SecurityScreen> {
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
      _data = await repo.getSecurityStatus();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final score = (_data?['score'] ?? 0).toDouble();
    final failedLogins = _data?['failed_logins'] ?? 0;
    final auditLog = _data != null ? List<Map<String, dynamic>>.from((_data!['audit_log'] ?? []).map((e) => Map<String, dynamic>.from(e))) : <Map<String, dynamic>>[];
    final threats = _data?['threats_blocked'] ?? 0;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Security', description: 'Security audit and monitoring'),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _data == null
                        ? const EmptyState(title: 'No data', description: 'Security data unavailable', icon: Icons.shield_outlined)
                        : ListView(
                            children: [
                              Row(
                                children: [
                                  Expanded(child: MetricCard(title: 'Security Score', value: '${score.toStringAsFixed(0)}/100', icon: '🛡️')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Failed Logins', value: '$failedLogins', icon: '🔒')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Threats Blocked', value: '$threats', icon: '🚫')),
                                ],
                              ),
                              const SizedBox(height: 16),
                              Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          const Text('Security Score', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                          const Spacer(),
                                          Text('${score.toStringAsFixed(0)}%', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: _getScoreColor(score))),
                                        ],
                                      ),
                                      const SizedBox(height: 8),
                                      ClipRRect(
                                        borderRadius: BorderRadius.circular(4),
                                        child: LinearProgressIndicator(
                                          value: score / 100,
                                          backgroundColor: const Color(0xFF2A2A4A),
                                          valueColor: AlwaysStoppedAnimation(_getScoreColor(score)),
                                          minHeight: 8,
                                        ),
                                      ),
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
                                      const Text('Audit Log', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                      const SizedBox(height: 12),
                                      if (auditLog.isEmpty)
                                        const Text('No audit entries', style: TextStyle(fontSize: 13, color: Color(0xFF8888A8)))
                                      else
                                        ...auditLog.map((entry) => Padding(
                                              padding: const EdgeInsets.only(bottom: 8),
                                              child: Row(
                                                children: [
                                                  StatusBadge(status: entry['action'] ?? 'info'),
                                                  const SizedBox(width: 8),
                                                  Expanded(child: Text(entry['detail'] ?? '', style: const TextStyle(fontSize: 12, color: Color(0xFFE8E8F0)), maxLines: 1, overflow: TextOverflow.ellipsis)),
                                                  Text(entry['timestamp'] ?? '', style: const TextStyle(fontSize: 10, color: Color(0xFF8888A8))),
                                                ],
                                              ),
                                            )),
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

  Color _getScoreColor(double score) {
    if (score >= 80) return const Color(0xFF22C55E);
    if (score >= 50) return const Color(0xFFF59E0B);
    return const Color(0xFFEF4444);
  }
}
