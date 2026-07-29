import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/chat_provider.dart';
import '../models/nova_models.dart';
import '../widgets/common_widgets.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});
  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    final chat = context.read<ChatProvider>();
    if (!chat.isConnected) chat.connect();
  }

  void _sendMessage() {
    final text = _inputController.text.trim();
    if (text.isEmpty) return;
    context.read<ChatProvider>().sendMessage(text);
    _inputController.clear();
  }

  @override
  Widget build(BuildContext context) {
    final chat = context.watch<ChatProvider>();
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          const PageHeader(title: 'Chat', description: 'Communicate with NOVA agents'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  Icon(chat.isConnected ? Icons.wifi : Icons.wifi_off, size: 16, color: chat.isConnected ? const Color(0xFF22C55E) : const Color(0xFFEF4444)),
                  const SizedBox(width: 8),
                  Text(chat.isConnected ? 'Connected' : 'Disconnected', style: const TextStyle(fontSize: 13, color: Color(0xFF8888A8))),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Expanded(
            child: chat.messages.isEmpty
                ? const EmptyState(title: 'Start a conversation', description: 'Send a message to an agent', icon: Icons.chat_bubble_outline)
                : ListView.builder(
                    controller: _scrollController,
                    itemCount: chat.messages.length,
                    itemBuilder: (context, i) => _MessageBubble(message: chat.messages[i]),
                  ),
          ),
          if (chat.isStreaming)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 8),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text('Thinking...', style: TextStyle(fontSize: 13, color: Color(0xFF8888A8), fontStyle: FontStyle.italic)),
              ),
            ),
          Card(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _inputController,
                      onSubmitted: (_) => _sendMessage(),
                      decoration: const InputDecoration(hintText: 'Type a message...', border: InputBorder.none, isDense: true),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.send, color: Color(0xFF6366F1)),
                    onPressed: chat.isStreaming ? null : _sendMessage,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final ChatMessage message;
  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.role == 'user';
    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
        decoration: BoxDecoration(
          color: isUser ? const Color(0xFF6366F1) : const Color(0xFF1A1A2E),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(message.content, style: TextStyle(color: isUser ? Colors.white : const Color(0xFFE8E8F0), fontSize: 14)),
            const SizedBox(height: 4),
            Text(
              '${message.timestamp.hour.toString().padLeft(2, '0')}:${message.timestamp.minute.toString().padLeft(2, '0')}',
              style: TextStyle(color: (isUser ? Colors.white : const Color(0xFF8888A8)).withOpacity(0.6), fontSize: 10),
            ),
          ],
        ),
      ),
    );
  }
}
