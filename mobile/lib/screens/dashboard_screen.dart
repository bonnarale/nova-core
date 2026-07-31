import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../widgets/common_widgets.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});
  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => context.read<AppProvider>().loadHealth());
  }

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();
    return Padding(
      padding: const EdgeInsets.all(16),
      child: ListView(
        children: [
          const PageHeader(title: 'Dashboard', description: 'NOVA CORE system overview'),
          if (app.isLoading) const LoadingView() else if (app.error != null) ErrorView(message: app.error!, onRetry: () => app.loadHealth()) else ...[
            if (app.health != null) ...[
              Row(
                children: [
                  Expanded(child: MetricCard(title: 'Status', value: app.health!.status, icon: '\u2714')),
                  const SizedBox(width: 8),
                  Expanded(child: MetricCard(title: 'Version', value: 'v${app.health!.version}')),
                  const SizedBox(width: 8),
                  Expanded(child: MetricCard(title: 'Services', value: '${app.health!.services.length}')),
                  const SizedBox(width: 8),
                  Expanded(child: MetricCard(title: 'Uptime', value: '${(app.health!.uptime / 3600).toStringAsFixed(1)}h')),
                ],
              ),
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text('Services', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                      const SizedBox(height: 12),
                      ...app.health!.services.map((s) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 4),
                        child: Row(
                          children: [
                            StatusBadge(status: s.status),
                            const SizedBox(width: 12),
                            Text(s.name, style: const TextStyle(color: Color(0xFFE8E8F0))),
                            const Spacer(),
                            if (s.latencyMs != null) Text('${s.latencyMs!.toStringAsFixed(0)}ms', style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8))),
                          ],
                        ),
                      )),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ],
      ),
    );
  }
}
