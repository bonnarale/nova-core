import 'dart:async';
import 'package:flutter/material.dart';
import '../core/config/app_config.dart';
import '../repositories/nova_repository.dart';
import '../core/api/api_client.dart';
import '../models/nova_models.dart';

class AppProvider extends ChangeNotifier {
  final AppConfig config;
  late final NovaApiClient _client;
  late final NovaRepository repository;

  HealthResponse? _health;
  bool _isLoading = false;
  String? _error;
  bool _isOffline = false;

  AppProvider({required this.config}) {
    _client = NovaApiClient(config: config);
    repository = NovaRepository(client: _client);
  }

  HealthResponse? get health => _health;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isOffline => _isOffline;

  Future<void> loadHealth() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _health = await repository.getHealth();
      _isOffline = false;
    } catch (e) {
      _error = e.toString();
      _isOffline = true;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void setOffline(bool offline) {
    _isOffline = offline;
    notifyListeners();
  }
}
