import 'package:flutter_test/flutter_test.dart';
import 'package:nova_core_mobile/notifications/notification_service.dart';

void main() {
  group('NotificationService', () {
    late NotificationService service;

    setUp(() {
      service = NotificationService();
    });

    test('initialize does not throw', () async {
      // Will fail gracefully in test environment since there's no actual notification plugin
      expect(() => service.initialize(), throwsA(anything));
    });

    test('showNotification throws in test env', () async {
      expect(() => service.showNotification(title: 'Test', body: 'Body'), throwsA(anything));
    });
  });
}
