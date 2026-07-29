import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';

class ConnectivityService {
  final _controller = StreamController<bool>.broadcast();
  final Connectivity _connectivity = Connectivity();
  StreamSubscription? _subscription;

  Stream<bool> get isConnected => _controller.stream;

  void initialize() {
    _subscription = _connectivity.onConnectivityChanged.listen((results) {
      final connected = results.any((r) => r != ConnectivityResult.none);
      _controller.add(connected);
    });
  }

  Future<bool> checkConnection() async {
    final results = await _connectivity.checkConnectivity();
    return results.any((r) => r != ConnectivityResult.none);
  }

  void dispose() {
    _subscription?.cancel();
    _controller.close();
  }
}
