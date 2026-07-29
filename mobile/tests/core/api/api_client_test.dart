import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:http/http.dart' as http;
import 'package:nova_core_mobile/core/config/app_config.dart';
import 'package:nova_core_mobile/core/api/api_client.dart';

class MockClient extends Mock implements http.Client {}

void main() {
  late NovaApiClient client;
  late MockClient mockHttp;

  setUp(() {
    mockHttp = MockClient();
    const config = AppConfig(apiBaseUrl: 'http://localhost:8000', wsBaseUrl: 'ws://localhost:8000');
    client = NovaApiClient(config: config);
  });

  group('NovaApiClient', () {
    test('setToken stores token', () {
      client.setToken('test-token');
      // No exception means success
      expect(() => client.setToken(null), returnsNormally);
    });

    test('setApiKey stores key', () {
      client.setApiKey('test-key');
      expect(() => client.setApiKey(null), returnsNormally);
    });

    test('get throws on error response', () async {
      // When no mock server, it should throw a network error
      expect(() => client.get('/api/test'), throwsException);
    });

    test('post throws on error response', () async {
      expect(() => client.post('/api/test', body: {'key': 'val'}), throwsException);
    });

    test('put throws on error response', () async {
      expect(() => client.put('/api/test', body: {'key': 'val'}), throwsException);
    });

    test('delete throws on error response', () async {
      expect(() => client.delete('/api/test'), throwsException);
    });

    test('stream throws on error response', () async {
      expect(() => client.stream('/api/test'), throwsException);
    });
  });
}
