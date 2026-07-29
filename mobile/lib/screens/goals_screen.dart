import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class GoalsScreen extends StatefulWidget {
  const GoalsScreen({super.key});
  @override
  State<GoalsScreen> createState() => _GoalsScreenState();
}

class _GoalsScreenState extends State<GoalsScreen> {
  List<Goal>? _goals;
  bool _loading = true;
  String? _error;
  String _filter = 'all';

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try { _goals = await context.read<AppProvider>().repository.getGoals(); }
    catch (e) { _error = e.toString(); }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _goals?.where((g) => _filter == 'all' || g.status == _filter).toList();
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Goals', description: 'Track and manage strategic objectives'),
          Row(
            children: ['all', 'active', 'completed'].map((f) => Padding(
              padding: const EdgeInsets.only(right: 8),
              child: FilterChip(
                label: Text(f[0].toUpperCase() + f.substring(1), style: TextStyle(fontSize: 12, color: _filter == f ? Colors.white : const Color(0xFF8888A8))),
                selected: _filter == f,
                onSelected: (_) => setState(() => _filter = f),
                selectedColor: const Color(0xFF6366F1),
                backgroundColor: const Color(0xFF1A1A2E),
              ),
            )).toList(),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: _loading ? const LoadingView() : _error != null ? ErrorView(message: _error!, onRetry: _load) : filtered == null || filtered.isEmpty
                ? const EmptyState(title: 'No goals', icon: Icons.flag_outlined)
                : ListView.builder(
                    itemCount: filtered.length,
                    itemBuilder: (context, i) {
                      final goal = filtered[i];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(children: [
                                Expanded(child: Text(goal.title, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0)))),
                                StatusBadge(status: goal.status),
                              ]),
                              const SizedBox(height: 4),
                              Text(goal.description, style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8))),
                              const SizedBox(height: 8),
                              Row(children: [
                                Expanded(
                                  child: ClipRRect(
                                    borderRadius: BorderRadius.circular(4),
                                    child: LinearProgressIndicator(value: goal.progress / 100, backgroundColor: const Color(0xFF2A2A4A), valueColor: const AlwaysStoppedAnimation(Color(0xFF6366F1)), minHeight: 6),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Text('${goal.progress}%', style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8))),
                              ]),
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
