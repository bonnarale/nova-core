import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class PluginsScreen extends StatefulWidget {
  const PluginsScreen({super.key});
  @override
  State<PluginsScreen> createState() => _PluginsScreenState();
}

class _PluginsScreenState extends State<PluginsScreen> {
  List<Plugin>? _plugins;
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
      _plugins = await repo.getPlugins();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final enabledCount = _plugins?.where((p) => p.enabled).length ?? 0;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          PageHeader(
            title: 'Plugins',
            description: 'Manage installed plugins',
            action: MetricCard(title: 'Enabled', value: '$enabledCount/${_plugins?.length ?? 0}', icon: '🔌'),
          ),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _plugins == null || _plugins!.isEmpty
                        ? const EmptyState(title: 'No plugins', description: 'No plugins installed', icon: Icons.extension_outlined)
                        : ListView.builder(
                            itemCount: _plugins!.length,
                            itemBuilder: (context, i) {
                              final plugin = _plugins![i];
                              return Card(
                                margin: const EdgeInsets.only(bottom: 8),
                                child: Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: Row(
                                    children: [
                                      CircleAvatar(
                                        backgroundColor: const Color(0xFF6366F1).withOpacity(0.2),
                                        child: Text(
                                          plugin.name.isNotEmpty ? plugin.name[0].toUpperCase() : '?',
                                          style: const TextStyle(color: Color(0xFF6366F1)),
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Row(
                                              children: [
                                                Text(plugin.name, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                                const SizedBox(width: 8),
                                                Text('v${plugin.version}', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                              ],
                                            ),
                                            const SizedBox(height: 2),
                                            Text('by ${plugin.author}', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                            if (plugin.description.isNotEmpty) ...[
                                              const SizedBox(height: 4),
                                              Text(plugin.description, style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8)), maxLines: 2, overflow: TextOverflow.ellipsis),
                                            ],
                                          ],
                                        ),
                                      ),
                                      Switch(
                                        value: plugin.enabled,
                                        onChanged: (val) {
                                          setState(() {
                                            _plugins![i] = Plugin(
                                              id: plugin.id,
                                              name: plugin.name,
                                              description: plugin.description,
                                              version: plugin.version,
                                              status: plugin.status,
                                              author: plugin.author,
                                              enabled: val,
                                            );
                                          });
                                        },
                                        activeColor: const Color(0xFF6366F1),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
          ),
        ],
      ),
    );
  }
}
