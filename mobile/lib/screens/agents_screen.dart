import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class AgentsScreen extends StatefulWidget {
  const AgentsScreen({super.key});
  @override
  State<AgentsScreen> createState() => _AgentsScreenState();
}

class _AgentsScreenState extends State<AgentsScreen> {
  List<Agent>? _agents;
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final repo = context.read<AppProvider>().repository;
      _agents = await repo.getAgents();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Agents', description: 'Manage autonomous AI agents'),
          Expanded(
            child: _loading ? const LoadingView() : _error != null ? ErrorView(message: _error!, onRetry: _load) : _agents == null || _agents!.isEmpty
                ? const EmptyState(title: 'No agents', description: 'No agents are currently registered')
                : ListView.builder(
                    itemCount: _agents!.length,
                    itemBuilder: (context, i) {
                      final agent = _agents![i];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 8),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: const Color(0xFF6366F1).withOpacity(0.2),
                            child: Text(agent.name.isNotEmpty ? agent.name[0].toUpperCase() : '?', style: const TextStyle(color: Color(0xFF6366F1))),
                          ),
                          title: Text(agent.name, style: const TextStyle(color: Color(0xFFE8E8F0))),
                          subtitle: Text(agent.role, style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8))),
                          trailing: StatusBadge(status: agent.status),
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
