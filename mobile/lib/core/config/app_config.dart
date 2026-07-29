class AppConfig {
  final String apiBaseUrl;
  final String wsBaseUrl;
  final String appName;
  final bool enableOfflineMode;
  final bool enablePushNotifications;
  final Duration cacheTimeout;
  final int maxRetryAttempts;

  const AppConfig({
    required this.apiBaseUrl,
    required this.wsBaseUrl,
    this.appName = 'NOVA CORE',
    this.enableOfflineMode = true,
    this.enablePushNotifications = true,
    this.cacheTimeout = const Duration(minutes: 5),
    this.maxRetryAttempts = 3,
  });

  factory AppConfig.fromEnvironment() {
    const apiBase = String.fromEnvironment('API_BASE_URL', defaultValue: 'http://localhost:8000');
    const wsBase = String.fromEnvironment('WS_BASE_URL', defaultValue: 'ws://localhost:8000');
    return AppConfig(
      apiBaseUrl: apiBase,
      wsBaseUrl: wsBase,
    );
  }

  String get healthUrl => '$apiBaseUrl/api/v1/health';
  String get chatWsUrl => '$wsBaseUrl/api/v1/chat/ws';
}
