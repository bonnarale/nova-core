import 'package:flutter_test/flutter_test.dart';
import 'package:nova_core_mobile/core/config/app_config.dart';
import 'package:nova_core_mobile/core/api/exceptions.dart';

void main() {
  group('AppConfig', () {
    test('creates from constructor', () {
      const config = AppConfig(apiBaseUrl: 'http://localhost:8000', wsBaseUrl: 'ws://localhost:8000');
      expect(config.apiBaseUrl, 'http://localhost:8000');
      expect(config.wsBaseUrl, 'ws://localhost:8000');
      expect(config.appName, 'NOVA CORE');
      expect(config.enableOfflineMode, true);
      expect(config.enablePushNotifications, true);
      expect(config.maxRetryAttempts, 3);
    });

    test('healthUrl constructs correct URL', () {
      const config = AppConfig(apiBaseUrl: 'http://localhost:8000', wsBaseUrl: 'ws://localhost:8000');
      expect(config.healthUrl, 'http://localhost:8000/api/v1/health');
    });

    test('chatWsUrl constructs correct URL', () {
      const config = AppConfig(apiBaseUrl: 'http://localhost:8000', wsBaseUrl: 'ws://localhost:8000');
      expect(config.chatWsUrl, 'ws://localhost:8000/api/v1/chat/ws');
    });

    test('custom cache timeout', () {
      const config = AppConfig(apiBaseUrl: '', wsBaseUrl: '', cacheTimeout: Duration(minutes: 10));
      expect(config.cacheTimeout.inMinutes, 10);
    });

    test('fromEnvironment uses defaults', () {
      final config = AppConfig.fromEnvironment();
      expect(config.apiBaseUrl, isNotEmpty);
      expect(config.wsBaseUrl, isNotEmpty);
    });
  });

  group('ApiException', () {
    test('stores statusCode and message', () {
      final e = ApiException(statusCode: 404, message: 'Not found');
      expect(e.statusCode, 404);
      expect(e.message, 'Not found');
    });

    test('toString formats correctly', () {
      final e = ApiException(statusCode: 500, message: 'Server error');
      expect(e.toString(), 'ApiException(500): Server error');
    });
  });

  group('NetworkException', () {
    test('default message', () {
      final e = NetworkException();
      expect(e.message, 'Network connection failed');
    });

    test('custom message', () {
      final e = NetworkException(message: 'Timeout');
      expect(e.message, 'Timeout');
    });
  });

  group('AuthException', () {
    test('default message', () {
      final e = AuthException();
      expect(e.message, 'Authentication failed');
    });

    test('custom message', () {
      final e = AuthException(message: 'Token expired');
      expect(e.message, 'Token expired');
    });
  });

  group('CacheException', () {
    test('default message', () {
      final e = CacheException();
      expect(e.message, 'Cache operation failed');
    });
  });
}
