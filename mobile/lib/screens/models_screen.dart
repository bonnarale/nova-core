import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../widgets/common_widgets.dart';

class ModelsScreen extends StatefulWidget {
  const ModelsScreen({super.key});
  @override
  State<ModelsScreen> createState() => _ModelsScreenState();
}

class _ModelsScreenState extends State<ModelsScreen> {
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
      _data = await repo.getModels();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final providers = _data != null ? Map<String, dynamic>.from(_data!['providers'] ?? {}) : <String, dynamic>{};
    final models = _data != null ? List<Map<String, dynamic>>.from((_data!['models'] ?? []).map((m) => Map<String, dynamic>.from(m))) : <Map<String, dynamic>>[];

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Models', description: 'Manage model providers and configurations'),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _data == null
                        ? const EmptyState(title: 'No models', description: 'No model configurations found', icon: Icons.smart_toy_outlined)
                        : ListView(
                            children: [
                              Row(
                                children: [
                                  Expanded(child: MetricCard(title: 'Providers', value: '${providers.length}', icon: '🏢')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Models', value: '${models.length}', icon: '🤖')),
                                ],
                              ),
                              const SizedBox(height: 16),
                              ...providers.entries.map((entry) => Card(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    child: Padding(
                                      padding: const EdgeInsets.all(12),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Text(entry.key, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                              const Spacer(),
                                              StatusBadge(status: '${entry.value}'),
                                            ],
                                          ),
                                        ],
                                      ),
                                    ),
                                  )),
                              const SizedBox(height: 8),
                              ...models.map((model) => Card(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    child: Padding(
                                      padding: const EdgeInsets.all(12),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Expanded(
                                                child: Text(model['name'] ?? 'Unknown', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                              ),
                                              StatusBadge(status: model['status'] ?? 'unknown'),
                                            ],
                                          ),
                                          const SizedBox(height: 8),
                                          Row(
                                            children: [
                                              _infoChip('Type: ${model['type'] ?? 'N/A'}'),
                                              const SizedBox(width: 8),
                                              if (model['max_tokens'] != null) _infoChip('Max Tokens: ${model['max_tokens']}'),
                                              if (model['context_window'] != null) ...[
                                                const SizedBox(width: 8),
                                                _infoChip('Context: ${model['context_window']}'),
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
