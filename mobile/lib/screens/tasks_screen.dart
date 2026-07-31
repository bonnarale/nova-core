import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class TasksScreen extends StatefulWidget {
  const TasksScreen({super.key});
  @override
  State<TasksScreen> createState() => _TasksScreenState();
}

class _TasksScreenState extends State<TasksScreen> {
  List<Task>? _tasks;
  bool _loading = true;
  String? _error;
  String _search = '';

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try { _tasks = await context.read<AppProvider>().repository.getTasks(); }
    catch (e) { _error = e.toString(); }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _tasks?.where((t) => _search.isEmpty || t.title.toLowerCase().contains(_search.toLowerCase())).toList();
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Tasks', description: 'Manage and track tasks across agents'),
          TextField(
            onChanged: (v) => setState(() => _search = v),
            decoration: const InputDecoration(hintText: 'Search tasks...', prefixIcon: Icon(Icons.search, size: 18)),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: _loading ? const LoadingView() : _error != null ? ErrorView(message: _error!, onRetry: _load) : filtered == null || filtered.isEmpty
                ? const EmptyState(title: 'No tasks', icon: Icons.task_alt_outlined)
                : ListView.builder(
                    itemCount: filtered.length,
                    itemBuilder: (context, i) {
                      final task = filtered[i];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          leading: Icon(task.status == 'completed' ? Icons.check_circle : Icons.radio_button_unchecked, color: task.status == 'completed' ? const Color(0xFF22C55E) : const Color(0xFF8888A8)),
                          title: Text(task.title, style: TextStyle(color: const Color(0xFFE8E8F0), decoration: task.status == 'completed' ? TextDecoration.lineThrough : null)),
                          subtitle: Text(task.assignedAgent ?? 'Unassigned', style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8))),
                          trailing: StatusBadge(status: task.status),
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
