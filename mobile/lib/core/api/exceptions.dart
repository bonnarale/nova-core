class ApiException implements Exception {
  final int statusCode;
  final String message;
  ApiException({required this.statusCode, required this.message});
  @override
  String toString() => 'ApiException($statusCode): $message';
}

class NetworkException implements Exception {
  final String message;
  NetworkException({this.message = 'Network connection failed'});
  @override
  String toString() => 'NetworkException: $message';
}

class AuthException implements Exception {
  final String message;
  AuthException({this.message = 'Authentication failed'});
  @override
  String toString() => 'AuthException: $message';
}

class CacheException implements Exception {
  final String message;
  CacheException({this.message = 'Cache operation failed'});
  @override
  String toString() => 'CacheException: $message';
}
