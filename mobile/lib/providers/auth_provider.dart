import 'package:flutter/material.dart';
import '../core/config/app_config.dart';
import '../core/api/api_client.dart';
import '../repositories/nova_repository.dart';

class AuthProvider extends ChangeNotifier {
  final AppConfig config;
  late final NovaApiClient _client;
  late final NovaRepository repository;
  String? _token;
  String? _userId;
  bool _isAuthenticated = false;
  bool _isLoading = false;

  AuthProvider({required this.config}) {
    _client = NovaApiClient(config: config);
    repository = NovaRepository(client: _client);
  }

  String? get token => _token;
  bool get isAuthenticated => _isAuthenticated;
  bool get isLoading => _isLoading;

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await _client.post('/api/v1/auth/login', body: {'email': email, 'password': password});
      _token = response['access_token'] as String?;
      _userId = response['user_id'] as String?;
      _client.setToken(_token);
      repository.setToken(_token);
      _isAuthenticated = _token != null;
      return _isAuthenticated;
    } catch (e) {
      _isAuthenticated = false;
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  void setToken(String? token) {
    _token = token;
    _isAuthenticated = token != null;
    _client.setToken(token);
    repository.setToken(token);
    notifyListeners();
  }

  void logout() {
    _token = null;
    _userId = null;
    _isAuthenticated = false;
    _client.setToken(null);
    repository.setToken(null);
    notifyListeners();
  }
}
