import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'app_drawer.dart';

class AppScaffold extends StatelessWidget {
  final Widget child;
  const AppScaffold({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final isWide = MediaQuery.of(context).size.width > 800;
    final currentPath = GoRouterState.of(context).uri.path;
    if (isWide) {
      return Scaffold(
        body: Row(
          children: [
            AppDrawer(currentPath: currentPath, isWide: true),
            Expanded(child: child),
          ],
        ),
      );
    }
    return Scaffold(
      body: child,
      bottomNavigationBar: AppBottomNav(currentPath: currentPath),
      drawer: AppDrawer(currentPath: currentPath, isWide: false),
    );
  }
}

class AppBottomNav extends StatelessWidget {
  final String currentPath;
  const AppBottomNav({super.key, required this.currentPath});

  @override
  Widget build(BuildContext context) {
    final items = [
      _Nav('/dashboard', Icons.dashboard, 'Home'),
      _Nav('/chat', Icons.chat, 'Chat'),
      _Nav('/tasks', Icons.task_alt, 'Tasks'),
      _Nav('/agents', Icons.smart_toy, 'Agents'),
      _Nav('/settings', Icons.settings, 'Settings'),
    ];
    int currentIndex = items.indexWhere((n) => n.path == currentPath);
    if (currentIndex < 0) currentIndex = 0;

    return BottomNavigationBar(
      currentIndex: currentIndex,
      onTap: (i) => context.go(items[i].path),
      items: items.map((n) => BottomNavigationBarItem(icon: Icon(n.icon), label: n.label)).toList(),
      type: BottomNavigationBarType.fixed,
    );
  }
}

class _Nav {
  final String path;
  final IconData icon;
  final String label;
  _Nav(this.path, this.icon, this.label);
}
