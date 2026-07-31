import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config/app_config.dart';

class NovaWebSocket {
  final AppConfig config;
  WebSocketChannel? _channel;
  final _controller = StreamController<dynamic>.broadcast();
  String? _token;
  Timer? _reconnectTimer;
  bool _shouldReconnect = true;
  int _reconnectAttempts = 0;

  NovaWebSocket({required this.config});

  Stream<dynamic> get stream => _controller.stream;
  bool get isConnected => _channel != null;

  void connect(String path, {String? token}) {
    _token = token;
    _shouldReconnect = true;
    _reconnectAttempts = 0;
    _doConnect(path);
  }

  void _doConnect(String path) {
    try {
      final uri = Uri.parse('${config.wsBaseUrl}$path');
      final headers = <String, String>{};
      if (_token != null) headers['Authorization'] = 'Bearer $_token';
      _channel = WebSocketChannel.connect(uri);
      _channel!.stream.listen(
        (data) => _controller.add(data),
        onError: (error) {
          _controller.addError(error);
          _scheduleReconnect(path);
        },
        onDone: () {
          if (_shouldReconnect) _scheduleReconnect(path);
        },
      );
    } catch (e) {
      _scheduleReconnect(path);
    }
  }

  void _scheduleReconnect(String path) {
    if (!_shouldReconnect || _reconnectAttempts >= config.maxRetryAttempts) return;
    _reconnectAttempts++;
    final delay = Duration(seconds: _reconnectAttempts * 2);
    _reconnectTimer = Timer(delay, () => _doConnect(path));
  }

  void send(dynamic data) {
    if (_channel != null) {
      final message = data is String ? data : jsonEncode(data);
      _channel!.sink.add(message);
    }
  }

  void disconnect() {
    _shouldReconnect = false;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _channel = null;
  }

  void dispose() {
    disconnect();
    _controller.close();
  }
}
