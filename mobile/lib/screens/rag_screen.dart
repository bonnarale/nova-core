import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class RAGScreen extends StatefulWidget {
  const RAGScreen({super.key});
  @override
  State<RAGScreen> createState() => _RAGScreenState();
}

class _RAGScreenState extends State<RAGScreen> {
  List<RAGCollection>? _collections;
  bool _loading = true;
  String? _error;
  final _queryController = TextEditingController();
  String? _queryResult;

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
      _collections = await repo.getRAGCollections();
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
          const PageHeader(title: 'RAG Collections', description: 'Manage retrieval-augmented generation collections'),
          Expanded(
            child: _loading
                ? const LoadingView()
                : _error != null
                    ? ErrorView(message: _error!, onRetry: _load)
                    : _collections == null || _collections!.isEmpty
                        ? const EmptyState(title: 'No collections', description: 'No RAG collections found', icon: Icons.storage_outlined)
                        : ListView(
                            children: [
                              Row(
                                children: [
                                  Expanded(child: MetricCard(title: 'Collections', value: '${_collections!.length}', icon: '📚')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Total Docs', value: '${_collections!.fold<int>(0, (sum, c) => sum + c.documentCount)}', icon: '📄')),
                                  const SizedBox(width: 8),
                                  Expanded(child: MetricCard(title: 'Total Vectors', value: '${_collections!.fold<int>(0, (sum, c) => sum + c.vectorCount)}', icon: '🔢')),
                                ],
                              ),
                              const SizedBox(height: 16),
                              ..._collections!.map((col) => Card(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    child: Padding(
                                      padding: const EdgeInsets.all(12),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Expanded(
                                                child: Text(col.name, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                              ),
                                              StatusBadge(status: col.status),
                                            ],
                                          ),
                                          if (col.description != null) ...[
                                            const SizedBox(height: 4),
                                            Text(col.description!, style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8)), maxLines: 2, overflow: TextOverflow.ellipsis),
                                          ],
                                          const SizedBox(height: 8),
                                          Row(
                                            children: [
                                              _infoChip('Docs: ${col.documentCount}'),
                                              const SizedBox(width: 8),
                                              _infoChip('Vectors: ${col.vectorCount}'),
                                            ],
                                          ),
                                        ],
                                      ),
                                    ),
                                  )),
                              const SizedBox(height: 16),
                              Card(
                                child: Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      const Text('Query Test', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                                      const SizedBox(height: 12),
                                      TextField(
                                        controller: _queryController,
                                        style: const TextStyle(color: Color(0xFFE8E8F0), fontSize: 13),
                                        decoration: InputDecoration(
                                          hintText: 'Enter a test query...',
                                          hintStyle: const TextStyle(color: Color(0xFF8888A8)),
                                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF2A2A4A))),
                                          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF2A2A4A))),
                                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                                        ),
                                        maxLines: 3,
                                      ),
                                      const SizedBox(height: 8),
                                      ElevatedButton(
                                        onPressed: () {
                                          setState(() => _queryResult = 'Query results would appear here for: "${_queryController.text}"');
                                        },
                                        child: const Text('Run Query'),
                                      ),
                                      if (_queryResult != null) ...[
                                        const SizedBox(height: 12),
                                        Container(
                                          width: double.infinity,
                                          padding: const EdgeInsets.all(12),
                                          decoration: BoxDecoration(color: const Color(0xFF1A1A2E), borderRadius: BorderRadius.circular(8)),
                                          child: Text(_queryResult!, style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8))),
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                              ),
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
