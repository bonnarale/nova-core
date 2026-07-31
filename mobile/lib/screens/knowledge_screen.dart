import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class KnowledgeScreen extends StatefulWidget {
  const KnowledgeScreen({super.key});
  @override
  State<KnowledgeScreen> createState() => _KnowledgeScreenState();
}

class _KnowledgeScreenState extends State<KnowledgeScreen> {
  List<MemoryEntry>? _entries;
  bool _loading = true;
  String? _error;
  String _category = 'all';

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try { _entries = await context.read<AppProvider>().repository.getMemory(); }
    catch (e) { _error = e.toString(); }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _entries?.where((e) => _category == 'all' || e.category == _category).toList();
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Memory', description: 'Explore agent long-term memory'),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: ['all', 'conversation', 'fact', 'preference', 'task'].map((c) => Padding(
                padding: const EdgeInsets.only(right: 8),
                child: FilterChip(
                  label: Text(c[0].toUpperCase() + c.substring(1), style: TextStyle(fontSize: 12, color: _category == c ? Colors.white : const Color(0xFF8888A8))),
                  selected: _category == c,
                  onSelected: (_) => setState(() => _category = c),
                  selectedColor: const Color(0xFF6366F1),
                  backgroundColor: const Color(0xFF1A1A2E),
                ),
              )).toList(),
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: _loading ? const LoadingView() : _error != null ? ErrorView(message: _error!, onRetry: _load) : filtered == null || filtered.isEmpty
                ? const EmptyState(title: 'No memory entries', icon: Icons.memory_outlined)
                : ListView.builder(
                    itemCount: filtered.length,
                    itemBuilder: (context, i) {
                      final entry = filtered[i];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(children: [
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                  decoration: BoxDecoration(color: const Color(0xFF3B82F6).withOpacity(0.15), borderRadius: BorderRadius.circular(8)),
                                  child: Text(entry.category, style: const TextStyle(fontSize: 10, color: Color(0xFF3B82F6))),
                                ),
                                const SizedBox(width: 8),
                                Text('Importance: ${entry.importance}/10', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                              ]),
                              const SizedBox(height: 8),
                              Text(entry.content, style: const TextStyle(fontSize: 13, color: Color(0xFFE8E8F0)), maxLines: 3, overflow: TextOverflow.ellipsis),
                              if (entry.tags.isNotEmpty) ...[
                                const SizedBox(height: 8),
                                Wrap(
                                  spacing: 4,
                                  children: entry.tags.map((t) => Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                    decoration: BoxDecoration(color: const Color(0xFF2A2A4A), borderRadius: BorderRadius.circular(8)),
                                    child: Text(t, style: const TextStyle(fontSize: 10, color: Color(0xFF8888A8))),
                                  )).toList(),
                                ),
                              ],
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
