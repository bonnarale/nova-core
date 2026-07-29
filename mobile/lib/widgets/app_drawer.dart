import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class AppDrawer extends StatelessWidget {
  final String currentPath;
  final bool isWide;
  const AppDrawer({super.key, required this.currentPath, required this.isWide});

  static const _items = [
    _DrawerItem('/dashboard', Icons.dashboard, 'Dashboard'),
    _DrawerItem('/chat', Icons.chat, 'Chat'),
    _DrawerItem('/agents', Icons.smart_toy, 'Agents'),
    _DrawerItem('/workflows', Icons.account_tree, 'Workflows'),
    _DrawerItem('/goals', Icons.flag, 'Goals'),
    _DrawerItem('/tasks', Icons.task_alt, 'Tasks'),
    _DrawerItem('/knowledge', Icons.memory, 'Memory'),
    _DrawerItem('/rag', Icons.search, 'RAG'),
    _DrawerItem('/models', Icons.psychology, 'Models'),
    _DrawerItem('/tools', Icons.build, 'Tools'),
    _DrawerItem('/plugins', Icons.extension, 'Plugins'),
    _DrawerItem('/scheduler', Icons.schedule, 'Scheduler'),
    _DrawerItem('/events', Icons.bolt, 'Events'),
    _DrawerItem('/observability', Icons.monitor_heart, 'Observability'),
    _DrawerItem('/deployment', Icons.cloud_upload, 'Deployment'),
    _DrawerItem('/scaling', Icons.tune, 'Scaling'),
    _DrawerItem('/security', Icons.shield, 'Security'),
    _DrawerItem('/enterprise', Icons.business, 'Enterprise'),
    _DrawerItem('/admin', Icons.admin_panel_settings, 'Admin'),
    _DrawerItem('/system', Icons.computer, 'System'),
    _DrawerItem('/settings', Icons.settings, 'Settings'),
  ];

  @override
  Widget build(BuildContext context) {
    if (isWide) {
      return Container(
        width: 240,
        color: Theme.of(context).colorScheme.surface,
        child: Column(
          children: [
            const SizedBox(height: 16),
            const Text('NOVA CORE', style: TextStyle(color: Color(0xFF6366F1), fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                itemCount: _items.length,
                itemBuilder: (ctx, i) {
                  final item = _items[i];
                  final active = currentPath == item.path;
                  return ListTile(
                    leading: Icon(item.icon, size: 20, color: active ? const Color(0xFF6366F1) : const Color(0xFF8888A8)),
                    title: Text(item.label, style: TextStyle(fontSize: 13, color: active ? const Color(0xFF6366F1) : const Color(0xFF8888A8), fontWeight: active ? FontWeight.w600 : FontWeight.normal)),
                    dense: true,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    selected: active,
                    selectedTileColor: const Color(0xFF6366F1).withOpacity(0.1),
                    onTap: () => context.go(item.path),
                  );
                },
              ),
            ),
          ],
        ),
      );
    }

    return Drawer(
      child: SafeArea(
        child: Column(
          children: [
            const Padding(
              padding: EdgeInsets.all(16),
              child: Text('NOVA CORE', style: TextStyle(color: Color(0xFF6366F1), fontSize: 20, fontWeight: FontWeight.bold)),
            ),
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                itemCount: _items.length,
                itemBuilder: (ctx, i) {
                  final item = _items[i];
                  final active = currentPath == item.path;
                  return ListTile(
                    leading: Icon(item.icon, size: 20, color: active ? const Color(0xFF6366F1) : const Color(0xFF8888A8)),
                    title: Text(item.label, style: TextStyle(fontSize: 13, color: active ? const Color(0xFF6366F1) : const Color(0xFF8888A8))),
                    dense: true,
                    onTap: () { Navigator.pop(context); context.go(item.path); },
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DrawerItem {
  final String path;
  final IconData icon;
  final String label;
  const _DrawerItem(this.path, this.icon, this.label);
}
