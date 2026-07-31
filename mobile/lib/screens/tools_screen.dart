import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../widgets/common_widgets.dart';

class ToolsScreen extends StatefulWidget {
  const ToolsScreen({super.key});
  @override
  State<ToolsScreen> createState() => _ToolsScreenState();
}

class _ToolsScreenState extends State<ToolsScreen> {
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
      _data = await repo.getTools();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final tools = _data != null ? List<Map<String, dynamic>>.from((_data!['tools'] ?? []).map((t) => Map<String, dynamic>.from(t))) : <Map<String, dynamic>>[];
    final categories = tools.map((t) => t['category'] ?? 'uncategorized').toSet().toList();

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Tools', description: 'Registry of available tools and functions'),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _data == null
                        ? const EmptyState(title: 'No tools', description: 'No tools registered', icon: Icons.build_outlined)
                        : ListView(
                            children: [
                              Row(
                                children: [
                                  Expanded(child: MetricCard(title: 'Total Tools', value: '${tools.length}', icon: '🔧')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Categories', value: '${categories.length}', icon: '📂')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Total Usage', value: '${tools.fold<int>(0, (sum, t) => sum + ((t['usage_count'] ?? 0) as int))}', icon: '📊')),
                                ],
                              ),
                              const SizedBox(height: 16),
                              ...tools.map((tool) => Card(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    child: Padding(
                                      padding: const EdgeInsets.all(12),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Expanded(
                                                child: Text(tool['name'] ?? 'Unknown', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                              ),
                                              Text('${tool['usage_count'] ?? 0} uses', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                            ],
                                          ),
                                          if (tool['description'] != null) ...[
                                            const SizedBox(height: 4),
                                            Text(tool['description'], style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8)), maxLines: 2, overflow: TextOverflow.ellipsis),
                                          ],
                                          const SizedBox(height: 8),
                                          Row(
                                            children: [
                                              _infoChip(tool['category'] ?? 'uncategorized'),
                                              if (tool['type'] != null) ...[
                                                const SizedBox(width: 8),
                                                _infoChip(tool['type']),
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

  Widget _infoChip(String label) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: const Color(0xFF2A2A4A), borderRadius: BorderRadius.circular(8)),
      child: Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
    );
  }
}
