import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/config/app_config.dart';
import 'core/theme/app_theme.dart';
import 'core/router/app_router.dart';
import 'providers/auth_provider.dart';
import 'providers/app_provider.dart';
import 'providers/chat_provider.dart';
import 'providers/theme_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final config = AppConfig.fromEnvironment();
  runApp(NovaCoreApp(config: config));
}

class NovaCoreApp extends StatelessWidget {
  final AppConfig config;
  const NovaCoreApp({super.key, required this.config});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        ChangeNotifierProvider(create: (_) => AuthProvider(config: config)),
        ChangeNotifierProvider(create: (_) => AppProvider(config: config)),
        ChangeNotifierProvider(create: (_) => ChatProvider(config: config)),
      ],
      child: Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) {
          return MaterialApp.router(
            title: 'NOVA CORE',
            theme: AppTheme.light,
            darkTheme: AppTheme.dark,
            themeMode: themeProvider.themeMode,
            routerConfig: appRouter,
            debugShowCheckedModeBanner: false,
          );
        },
      ),
    );
  }
}
