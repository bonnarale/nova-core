import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class EventsScreen extends StatefulWidget {
  const EventsScreen({super.key});
  @override
  State<EventsScreen> createState() => _EventsScreenState();
}

class _EventsScreenState extends State<EventsScreen> {
  List<SystemEvent>? _events;
  bool _loading = true;
  String? _error;
  String _severityFilter = 'all';

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
      _events = await repo.getEvents();
    } catch (e) {
      _error = e.toString();
    }
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _events?.where((e) => _severityFilter == 'all' || e.severity == _severityFilter).toList();

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Events', description: 'Real-time system event feed'),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: ['all', 'info', 'warning', 'error', 'critical'].map((s) => Padding(
                padding: const EdgeInsets.only(right: 8),
                child: FilterChip(
                  label: Text(s[0].toUpperCase() + s.substring(1), style: TextStyle(fontSize: 12, color: _severityFilter == s ? Colors.white : const Color(0xFF8888A8))),
                  selected: _severityFilter == s,
                  onSelected: (_) => setState(() => _severityFilter = s),
                  selectedColor: const Color(0xFF6366F1),
                  backgroundColor: const Color(0xFF1A1A2E),
                ),
              )).toList(),
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : filtered == null || filtered.isEmpty
                        ? const EmptyState(title: 'No events', description: 'No events match the current filter', icon: Icons.event_outlined)
                        : ListView.builder(
                            itemCount: filtered.length,
                            itemBuilder: (context, i) {
                              final event = filtered[i];
                              return Card(
                                margin: const EdgeInsets.only(bottom: 8),
                                child: Padding(
                                  padding: const EdgeInsets.all(12),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          StatusBadge(status: event.severity),
                                          const SizedBox(width: 8),
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                                            decoration: BoxDecoration(color: const Color(0xFF3B82F6).withOpacity(0.15), borderRadius: BorderRadius.circular(8)),
                                            child: Text(event.type, style: const TextStyle(fontSize: 10, color: Color(0xFF3B82F6))),
                                          ),
                                          const Spacer(),
                                          Text(_formatTimestamp(event.timestamp), style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
                                        ],
                                      ),
                                      const SizedBox(height: 8),
                                      Text(event.message, style: const TextStyle(fontSize: 13, color: Color(0xFFE8E8F0)), maxLines: 3, overflow: TextOverflow.ellipsis),
                                      const SizedBox(height: 4),
                                      Text('Source: ${event.source}', style: const TextStyle(fontSize: 11, color: Color(0xFF8888A8))),
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

  String _formatTimestamp(DateTime ts) {
    return '${ts.month}/${ts.day} ${ts.hour}:${ts.minute.toString().padLeft(2, '0')}:${ts.second.toString().padLeft(2, '0')}';
  }
}
