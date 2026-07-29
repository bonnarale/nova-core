import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/app_config.dart';
import 'exceptions.dart';

class NovaApiClient {
  final AppConfig config;
  String? _token;
  String? _apiKey;

  NovaApiClient({required this.config});

  void setToken(String? token) => _token = token;
  void setApiKey(String? key) => _apiKey = key;

  Map<String, String> get _headers {
    final h = <String, String>{'Content-Type': 'application/json'};
    if (_token != null) h['Authorization'] = 'Bearer $_token';
    if (_apiKey != null) h['X-API-Key'] = _apiKey!;
    return h;
  }

  Uri _uri(String path, [Map<String, String>? params]) {
    final base = Uri.parse(config.apiBaseUrl);
    final uri = base.resolve(path);
    if (params != null && params.isNotEmpty) {
      return uri.replace(queryParameters: params);
    }
    return uri;
  }

  Future<T> get<T>(String path, {Map<String, String>? params, T Function(dynamic)? parser}) async {
    final response = await http.get(_uri(path, params), headers: _headers);
    return _handleResponse<T>(response, parser);
  }

  Future<T> post<T>(String path, {Object? body, T Function(dynamic)? parser}) async {
    final response = await http.post(_uri(path), headers: _headers, body: body != null ? jsonEncode(body) : null);
    return _handleResponse<T>(response, parser);
  }

  Future<T> put<T>(String path, {Object? body, T Function(dynamic)? parser}) async {
    final response = await http.put(_uri(path), headers: _headers, body: body != null ? jsonEncode(body) : null);
    return _handleResponse<T>(response, parser);
  }

  Future<T> delete<T>(String path, {T Function(dynamic)? parser}) async {
    final response = await http.delete(_uri(path), headers: _headers);
    return _handleResponse<T>(response, parser);
  }

  Future<http.StreamedResponse> stream(String path, {Object? body}) async {
    final request = http.Request('POST', _uri(path));
    request.headers.addAll(_headers);
    request.headers['Accept'] = 'text/event-stream';
    if (body != null) request.body = jsonEncode(body);
    return http.Client().send(request);
  }

  T _handleResponse<T>(http.Response response, T Function(dynamic)? parser) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (T == dynamic && parser == null) {
        return jsonDecode(response.body) as T;
      }
      final json = jsonDecode(response.body);
      if (parser != null) return parser(json);
      return json as T;
    }
    throw ApiException(
      statusCode: response.statusCode,
      message: _extractError(response.body),
    );
  }

  String _extractError(String body) {
    try {
      final json = jsonDecode(body);
      return json['detail'] as String? ?? 'Unknown error';
    } catch (_) {
      return body.isNotEmpty ? body : 'Unknown error';
    }
  }
}
