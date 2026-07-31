import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class SchedulerScreen extends StatefulWidget {
  const SchedulerScreen({super.key});
  @override
  State<SchedulerScreen> createState() => _SchedulerScreenState();
}

class _SchedulerScreenState extends State<SchedulerScreen> {
  List<ScheduleJob>? _jobs;
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
      _jobs = await repo.getScheduleJobs();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final activeCount = _jobs?.where((j) => j.enabled).length ?? 0;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Scheduler', description: 'Manage cron jobs and scheduled tasks'),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _jobs == null || _jobs!.isEmpty
                        ? const EmptyState(title: 'No jobs', description: 'No scheduled jobs found', icon: Icons.schedule_outlined)
                        : ListView(
                            children: [
                              Row(
                                children: [
                                  Expanded(child: MetricCard(title: 'Total Jobs', value: '${_jobs!.length}', icon: '⏰')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Active', value: '$activeCount', icon: '▶')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Disabled', value: '${_jobs!.length - activeCount}', icon: '⏸')),
                                ],
                              ),
                              const SizedBox(height: 16),
                              ..._jobs!.map((job) => Card(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    child: Padding(
                                      padding: const EdgeInsets.all(12),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Expanded(
                                                child: Text(job.name, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                              ),
                                              StatusBadge(status: job.status),
                                            ],
                                          ),
                                          const SizedBox(height: 8),
                                          Row(
                                            children: [
                                              _infoChip(job.cron),
                                              const SizedBox(width: 8),
                                              _infoChip(job.taskType),
                                              const SizedBox(width: 8),
                                              Container(
                                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                                decoration: BoxDecoration(
                                                  color: job.enabled ? const Color(0xFF22C55E).withOpacity(0.15) : const Color(0xFFEF4444).withOpacity(0.15),
                                                  borderRadius: BorderRadius.circular(8),
                                                ),
                                                child: Text(
                                                  job.enabled ? 'Enabled' : 'Disabled',
                                                  style: TextStyle(fontSize: 11, color: job.enabled ? const Color(0xFF22C55E) : const Color(0xFFEF4444)),
                                                ),
                                              ),
                                            ],
                                          ),
                                          const SizedBox(height: 8),
                                          Row(
                                            children: [
                                              const Icon(Icons.access_time, size: 12, color: Color(0xFF8888A8)),
                                              const SizedBox(width: 4),
                                              Text('Next: ${_formatDate(job.nextRun)}', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                              if (job.lastRun != null) ...[
                                                const SizedBox(width: 12),
                                                const Icon(Icons.history, size: 12, color: Color(0xFF8888A8)),
                                                const SizedBox(width: 4),
                                                Text('Last: ${_formatDate(job.lastRun!)}', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                              ],
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
    return '${date.month}/${date.day} ${date.hour}:${date.minute.toString().padLeft(2, '0')}';
  }

  Widget _infoChip(String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: const Color(0xFF2A2A4A), borderRadius: BorderRadius.circular(8)),
      child: Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
    );
  }
}
