import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class WorkflowsScreen extends StatefulWidget {
  const WorkflowsScreen({super.key});
  @override
  State<WorkflowsScreen> createState() => _WorkflowsScreenState();
}

class _WorkflowsScreenState extends State<WorkflowsScreen> {
  List<Workflow>? _workflows;
  bool _loading = true;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try { _workflows = await context.read<AppProvider>().repository.getWorkflows(); }
    catch (e) { _error = e.toString(); }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Workflows', description: 'Design and manage autonomous workflows'),
          Expanded(
            child: _loading ? const LoadingView() : _error != null ? ErrorView(message: _error!, onRetry: _load) : _workflows == null || _workflows!.isEmpty
                ? const EmptyState(title: 'No workflows', icon: Icons.account_tree_outlined)
                : ListView.builder(
                    itemCount: _workflows!.length,
                    itemBuilder: (context, i) {
                      final wf = _workflows![i];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          title: Row(children: [Text(wf.name, style: const TextStyle(color: Color(0xFFE8E8F0))), const SizedBox(width: 8), StatusBadge(status: wf.status)]),
                          subtitle: Text(wf.description, style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8))),
                          trailing: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(color: const Color(0xFF6366F1).withOpacity(0.15), borderRadius: BorderRadius.circular(8)),
                            child: Text('${wf.stepsCount} steps', style: const TextStyle(fontSize: 11, color: Color(0xFF6366F1))),
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
