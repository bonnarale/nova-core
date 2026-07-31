import 'package:flutter_test/flutter_test.dart';
import 'package:nova_core_mobile/localization/localization.dart';

void main() {
  group('EnglishLocalization', () {
    late EnglishLocalization loc;

    setUp(() {
      loc = EnglishLocalization();
    });

    test('appTitle returns NOVA CORE', () {
      expect(loc.appTitle, 'NOVA CORE');
    });

    test('all labels are non-empty', () {
      expect(loc.dashboard, isNotEmpty);
      expect(loc.chat, isNotEmpty);
      expect(loc.agents, isNotEmpty);
      expect(loc.workflows, isNotEmpty);
      expect(loc.goals, isNotEmpty);
      expect(loc.tasks, isNotEmpty);
      expect(loc.memory, isNotEmpty);
      expect(loc.rag, isNotEmpty);
      expect(loc.models, isNotEmpty);
      expect(loc.tools, isNotEmpty);
      expect(loc.plugins, isNotEmpty);
      expect(loc.scheduler, isNotEmpty);
      expect(loc.events, isNotEmpty);
      expect(loc.observability, isNotEmpty);
      expect(loc.deployment, isNotEmpty);
      expect(loc.scaling, isNotEmpty);
      expect(loc.security, isNotEmpty);
      expect(loc.enterprise, isNotEmpty);
      expect(loc.settings, isNotEmpty);
      expect(loc.admin, isNotEmpty);
      expect(loc.system, isNotEmpty);
      expect(loc.login, isNotEmpty);
      expect(loc.logout, isNotEmpty);
      expect(loc.search, isNotEmpty);
      expect(loc.loading, isNotEmpty);
      expect(loc.error, isNotEmpty);
      expect(loc.retry, isNotEmpty);
      expect(loc.noData, isNotEmpty);
      expect(loc.send, isNotEmpty);
      expect(loc.connect, isNotEmpty);
      expect(loc.disconnect, isNotEmpty);
    });
  });
}
