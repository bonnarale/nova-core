import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/app_provider.dart';
import '../providers/theme_provider.dart';
import '../widgets/common_widgets.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _notificationsEnabled = true;

  @override
  Widget build(BuildContext context) {
    final app = context.watch<AppProvider>();
    final theme = context.watch<ThemeProvider>();
    final isDark = theme.themeMode == ThemeMode.dark;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: ListView(
        children: [
          const PageHeader(title: 'Settings', description: 'Application configuration and preferences'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Appearance', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      const Icon(Icons.dark_mode, size: 20, color: Color(0xFF8888A8)),
                      const SizedBox(width: 12),
                      const Expanded(child: Text('Dark Mode', style: TextStyle(color: Color(0xFFE8E8F0)))),
                      Switch(
                        value: isDark,
                        onChanged: (_) => theme.toggleTheme(),
                        activeColor: const Color(0xFF6366F1),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('API Configuration', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                  const SizedBox(height: 12),
                  _infoRow('Base URL', app.config.baseUrl),
                  _infoRow('Timeout', '${app.config.timeout.inSeconds}s'),
                  _infoRow('Offline Mode', app.isOffline ? 'Yes' : 'No'),
                  _infoRow('Version', app.health?.version ?? 'Unknown'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Notifications', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      const Icon(Icons.notifications, size: 20, color: Color(0xFF8888A8)),
                      const SizedBox(width: 12),
                      const Expanded(child: Text('Push Notifications', style: TextStyle(color: Color(0xFFE8E8F0)))),
                      Switch(
                        value: _notificationsEnabled,
                        onChanged: (val) => setState(() => _notificationsEnabled = val),
                        activeColor: const Color(0xFF6366F1),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Data Management', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Color(0xFFE8E8F0))),
                  const SizedBox(height: 12),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.delete_outline, color: Color(0xFFEF4444)),
                    title: const Text('Clear Cache', style: TextStyle(color: Color(0xFFE8E8F0))),
                    subtitle: const Text('Remove all cached data', style: TextStyle(fontSize: 12, color: Color(0xFF8888A8))),
                    onTap: () async {
                      await app.repository.clearCache();
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Cache cleared')),
                        );
                      }
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _infoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Text(label, style: const TextStyle(fontSize: 13, color: Color(0xFF8888A8))),
          const Spacer(),
          Text(value, style: const TextStyle(fontSize: 13, color: Color(0xFFE8E8F0))),
        ],
      ),
    );
  }
}
