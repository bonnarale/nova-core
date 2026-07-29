import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../screens/dashboard_screen.dart';
import '../../screens/chat_screen.dart';
import '../../screens/agents_screen.dart';
import '../../screens/workflows_screen.dart';
import '../../screens/goals_screen.dart';
import '../../screens/tasks_screen.dart';
import '../../screens/knowledge_screen.dart';
import '../../screens/rag_screen.dart';
import '../../screens/models_screen.dart';
import '../../screens/tools_screen.dart';
import '../../screens/plugins_screen.dart';
import '../../screens/scheduler_screen.dart';
import '../../screens/events_screen.dart';
import '../../screens/observability_screen.dart';
import '../../screens/deployment_screen.dart';
import '../../screens/scaling_screen.dart';
import '../../screens/security_screen.dart';
import '../../screens/enterprise_screen.dart';
import '../../screens/settings_screen.dart';
import '../../screens/auth_screen.dart';
import '../../screens/admin_screen.dart';
import '../../screens/system_screen.dart';
import '../../widgets/app_scaffold.dart';

final appRouter = GoRouter(
  initialLocation: '/dashboard',
  routes: [
    GoRoute(path: '/auth', builder: (context, state) => const AuthScreen()),
    ShellRoute(
      builder: (context, state, child) => AppScaffold(child: child),
      routes: [
        GoRoute(path: '/dashboard', builder: (_, __) => const DashboardScreen()),
        GoRoute(path: '/chat', builder: (_, __) => const ChatScreen()),
        GoRoute(path: '/agents', builder: (_, __) => const AgentsScreen()),
        GoRoute(path: '/workflows', builder: (_, __) => const WorkflowsScreen()),
        GoRoute(path: '/goals', builder: (_, __) => const GoalsScreen()),
        GoRoute(path: '/tasks', builder: (_, __) => const TasksScreen()),
        GoRoute(path: '/knowledge', builder: (_, __) => const KnowledgeScreen()),
        GoRoute(path: '/rag', builder: (_, __) => const RAGScreen()),
        GoRoute(path: '/models', builder: (_, __) => const ModelsScreen()),
        GoRoute(path: '/tools', builder: (_, __) => const ToolsScreen()),
        GoRoute(path: '/plugins', builder: (_, __) => const PluginsScreen()),
        GoRoute(path: '/scheduler', builder: (_, __) => const SchedulerScreen()),
        GoRoute(path: '/events', builder: (_, __) => const EventsScreen()),
        GoRoute(path: '/observability', builder: (_, __) => const ObservabilityScreen()),
        GoRoute(path: '/deployment', builder: (_, __) => const DeploymentScreen()),
        GoRoute(path: '/scaling', builder: (_, __) => const ScalingScreen()),
        GoRoute(path: '/security', builder: (_, __) => const SecurityScreen()),
        GoRoute(path: '/enterprise', builder: (_, __) => const EnterpriseScreen()),
        GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
        GoRoute(path: '/admin', builder: (_, __) => const AdminScreen()),
        GoRoute(path: '/system', builder: (_, __) => const SystemScreen()),
      ],
    ),
  ],
);
