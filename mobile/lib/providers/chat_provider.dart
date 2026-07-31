import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../core/config/app_config.dart';
import '../core/api/websocket_client.dart';
import '../models/nova_models.dart';

class ChatProvider extends ChangeNotifier {
  final AppConfig config;
  late final NovaWebSocket _ws;
  final List<ChatMessage> _messages = [];
  bool _isConnected = false;
  bool _isStreaming = false;
  String? _activeAgentId;

  ChatProvider({required this.config}) {
    _ws = NovaWebSocket(config: config);
    _ws.stream.listen(
      (data) {
        try {
          final json = jsonDecode(data.toString());
          if (json['type'] == 'message') {
            _messages.add(ChatMessage(
              role: 'assistant',
              content: json['content'] ?? '',
              timestamp: DateTime.now(),
              agentId: json['agent_id'],
            ));
            _isStreaming = false;
            notifyListeners();
          } else if (json['type'] == 'stream_start') {
            _isStreaming = true;
            notifyListeners();
          }
        } catch (_) {}
      },
      onError: (_) {
        _isConnected = false;
        notifyListeners();
      },
      onDone: () {
        _isConnected = false;
        notifyListeners();
      },
    );
  }

  List<ChatMessage> get messages => List.unmodifiable(_messages);
  bool get isConnected => _isConnected;
  bool get isStreaming => _isStreaming;
  String? get activeAgentId => _activeAgentId;

  void connect({String? token}) {
    _ws.connect('/api/v1/chat/ws', token: token);
    _isConnected = true;
    notifyListeners();
  }

  void sendMessage(String content) {
    _messages.add(ChatMessage(role: 'user', content: content, timestamp: DateTime.now()));
    _isStreaming = true;
    notifyListeners();
    _ws.send({'content': content, 'agent_id': _activeAgentId});
  }

  void setActiveAgent(String? agentId) {
    _activeAgentId = agentId;
    notifyListeners();
  }

  void clearMessages() {
    _messages.clear();
    notifyListeners();
  }

  void disconnect() {
    _ws.disconnect();
    _isConnected = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _ws.dispose();
    super.dispose();
  }
}
