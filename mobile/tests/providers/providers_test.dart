import 'package:flutter_test/flutter_test.dart';
import 'package:nova_core_mobile/core/config/app_config.dart';
import 'package:nova_core_mobile/core/api/api_client.dart';
import 'package:nova_core_mobile/providers/theme_provider.dart';
import 'package:nova_core_mobile/providers/chat_provider.dart';
import 'package:flutter/material.dart';

void main() {
  group('ThemeProvider', () {
    late ThemeProvider provider;

    setUp(() {
      provider = ThemeProvider();
    });

    test('initial theme is dark', () {
      expect(provider.themeMode, ThemeMode.dark);
    });

    test('toggleTheme switches to light', () {
      provider.toggleTheme();
      expect(provider.themeMode, ThemeMode.light);
    });

    test('toggleTheme switches back to dark', () {
      provider.toggleTheme();
      provider.toggleTheme();
      expect(provider.themeMode, ThemeMode.dark);
    });

    test('setThemeMode sets specified mode', () {
      provider.setThemeMode(ThemeMode.light);
      expect(provider.themeMode, ThemeMode.light);
      provider.setThemeMode(ThemeMode.system);
      expect(provider.themeMode, ThemeMode.system);
    });

    test('notifyListeners is called', () {
      int notifyCount = 0;
      provider.addListener(() => notifyCount++);
      provider.toggleTheme();
      expect(notifyCount, 1);
    });
  });

  group('ChatProvider', () {
    late ChatProvider provider;

    setUp(() {
      const config = AppConfig(apiBaseUrl: 'http://localhost:8000', wsBaseUrl: 'ws://localhost:8000');
      provider = ChatProvider(config: config);
    });

    test('initial state is empty', () {
      expect(provider.messages, isEmpty);
      expect(provider.isConnected, false);
      expect(provider.isStreaming, false);
      expect(provider.activeAgentId, isNull);
    });

    test('setActiveAgent updates agent', () {
      provider.setActiveAgent('agent-1');
      expect(provider.activeAgentId, 'agent-1');
    });

    test('clearMessages empties list', () {
      provider.clearMessages();
      expect(provider.messages, isEmpty);
    });

    test('dispose does not throw', () {
      expect(() => provider.dispose(), returnsNormally);
    });
  });

  group('AppConfig', () {
    test('equality', () {
      const c1 = AppConfig(apiBaseUrl: 'http://a', wsBaseUrl: 'ws://a');
      const c2 = AppConfig(apiBaseUrl: 'http://a', wsBaseUrl: 'ws://a');
      expect(c1.apiBaseUrl, c2.apiBaseUrl);
      expect(c1.wsBaseUrl, c2.wsBaseUrl);
    });

    test('defaults', () {
      const config = AppConfig(apiBaseUrl: '', wsBaseUrl: '');
      expect(config.appName, 'NOVA CORE');
      expect(config.enableOfflineMode, true);
      expect(config.cacheTimeout.inMinutes, 5);
    });
  });
}
