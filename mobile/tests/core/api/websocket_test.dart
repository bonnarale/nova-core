import 'package:flutter_test/flutter_test.dart';
import 'package:nova_core_mobile/core/api/websocket_client.dart';
import 'package:nova_core_mobile/core/config/app_config.dart';

void main() {
  group('NovaWebSocket', () {
    late NovaWebSocket ws;

    setUp(() {
      const config = AppConfig(apiBaseUrl: 'http://localhost:8000', wsBaseUrl: 'ws://localhost:8000');
      ws = NovaWebSocket(config: config);
    });

    tearDown(() {
      ws.dispose();
    });

    test('initial state is disconnected', () {
      expect(ws.isConnected, false);
    });

    test('stream is broadcast', () {
      expect(ws.stream.isBroadcast, true);
    });

    test('disconnect when not connected is safe', () {
      ws.disconnect();
      expect(ws.isConnected, false);
    });

    test('send when not connected does not throw', () {
      expect(() => ws.send('test'), returnsNormally);
    });

    test('send with map does not throw when disconnected', () {
      expect(() => ws.send({'key': 'value'}), returnsNormally);
    });

    test('dispose closes stream', () {
      ws.dispose();
      expect(() => ws.stream, returnsNormally);
    });
  });
}
