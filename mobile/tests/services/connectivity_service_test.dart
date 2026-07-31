import 'package:flutter_test/flutter_test.dart';
import 'package:nova_core_mobile/services/connectivity_service.dart';

void main() {
  group('ConnectivityService', () {
    late ConnectivityService service;

    setUp(() {
      service = ConnectivityService();
    });

    tearDown(() {
      service.dispose();
    });

    test('isConnected stream is broadcast', () {
      expect(service.isConnected.isBroadcast, true);
    });

    test('dispose does not throw', () {
      expect(() => service.dispose(), returnsNormally);
    });

    test('checkConnection returns a boolean', () async {
      final result = await service.checkConnection();
      expect(result, isA<bool>());
    });
  });
}
