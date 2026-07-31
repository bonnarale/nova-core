import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class DeploymentScreen extends StatefulWidget {
  const DeploymentScreen({super.key});
  @override
  State<DeploymentScreen> createState() => _DeploymentScreenState();
}

class _DeploymentScreenState extends State<DeploymentScreen> {
  List<Deployment>? _deployments;
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
      _deployments = await repo.getDeploymentHistory();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final successCount = _deployments?.where((d) => d.status == 'completed').length ?? 0;
    final environments = _deployments?.map((d) => d.environment).toSet().toList() ?? [];

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Deployment', description: 'Deploy history and rollback management'),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _deployments == null || _deployments!.isEmpty
                        ? const EmptyState(title: 'No deployments', description: 'No deployment history found', icon: Icons.cloud_upload_outlined)
                        : ListView(
                            children: [
                              Row(
                                children: [
                                  Expanded(child: MetricCard(title: 'Total Deploys', value: '${_deployments!.length}', icon: '🚀')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Successful', value: '$successCount', icon: '✅')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Environments', value: '${environments.length}', icon: '🌐')),
                                ],
                              ),
                              const SizedBox(height: 16),
                              ..._deployments!.map((deploy) => Card(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    child: Padding(
                                      padding: const EdgeInsets.all(12),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Text('v${deploy.version}', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                              const Spacer(),
                                              StatusBadge(status: deploy.status),
                                            ],
                                          ),
                                          const SizedBox(height: 8),
                                          Row(
                                            children: [
                                              _infoChip(deploy.environment),
                                              const SizedBox(width: 8),
                                              Text('by ${deploy.deployedBy}', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                            ],
                                          ),
                                          const SizedBox(height: 8),
                                          Row(
                                            children: [
                                              const Icon(Icons.access_time, size: 12, color: Color(0xFF8888A8)),
                                              const SizedBox(width: 4),
                                              Text(_formatDate(deploy.deployedAt), style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                              const Spacer(),
                                              if (deploy.status == 'completed')
                                                TextButton(
                                                  onPressed: () {},
                                                  child: const Text('Rollback', style: TextStyle(fontSize: 11, color: Color(0xFFEF4444))),
                                                ),
                                            ],
                                          ),
                                        ],
                                      ),
                                    ),
                                  )),
                            ],
                          ),
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')} ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
  }

  Widget _infoChip(String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: const Color(0xFF2A2A4A), borderRadius: BorderRadius.circular(8)),
      child: Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
    );
  }
}
