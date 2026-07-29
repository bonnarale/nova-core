import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  final FlutterLocalNotificationsPlugin _plugin = FlutterLocalNotificationsPlugin();
  bool _initialized = false;

  Future<void> initialize() async {
    if (_initialized) return;
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings();
    const settings = InitializationSettings(android: androidSettings, iOS: iosSettings);
    await _plugin.initialize(settings);
    _initialized = true;
  }

  Future<void> showNotification({required String title, required String body, String? payload}) async {
    if (!_initialized) await initialize();
    const androidDetails = AndroidNotificationDetails('nova_core', 'NOVA CORE', importance: Importance.high, priority: Priority.high);
    const details = NotificationDetails(android: androidDetails);
    await _plugin.show(0, title, body, details, payload: payload);
  }

  Future<void> showWorkflowNotification(String workflowName, String status) => showNotification(title: 'Workflow: $workflowName', body: 'Status changed to $status');

  Future<void> showGoalNotification(String goalTitle, int progress) => showNotification(title: 'Goal Update', body: '$goalTitle is now at $progress%');

  Future<void> showTaskNotification(String taskTitle, String status) => showNotification(title: 'Task: $taskTitle', body: 'Status: $status');

  Future<void> showSystemAlert(String message) => showNotification(title: 'System Alert', body: message);

  Future<void> cancelAll() => _plugin.cancelAll();
}
