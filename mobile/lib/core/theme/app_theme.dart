import 'package:flutter/material.dart';

class AppTheme {
  static final dark = ThemeData(
    brightness: Brightness.dark,
    scaffoldBackgroundColor: const Color(0xFF0A0A0F),
    colorScheme: const ColorScheme.dark(
      primary: Color(0xFF6366F1),
      secondary: Color(0xFF818CF8),
      surface: Color(0xFF12121A),
      error: Color(0xFFEF4444),
      onPrimary: Colors.white,
      onSurface: Color(0xFFE8E8F0),
    ),
    cardTheme: CardTheme(
      color: const Color(0xFF1A1A2E),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      elevation: 0,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Color(0xFF0A0A0F),
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(color: Color(0xFFE8E8F0), fontSize: 18, fontWeight: FontWeight.w600),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: Color(0xFF12121A),
      selectedItemColor: Color(0xFF6366F1),
      unselectedItemColor: Color(0xFF8888A8),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: const Color(0xFF1A1A2E),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF2A2A4A))),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF2A2A4A))),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF6366F1))),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF6366F1),
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      ),
    ),
  );

  static final light = ThemeData(
    brightness: Brightness.light,
    scaffoldBackgroundColor: const Color(0xFFF8F9FC),
    colorScheme: const ColorScheme.light(
      primary: Color(0xFF6366F1),
      secondary: Color(0xFF4F46E5),
      surface: Colors.white,
      error: Color(0xFFDC2626),
      onPrimary: Colors.white,
      onSurface: Color(0xFF1A1A2E),
    ),
    cardTheme: CardTheme(
      color: Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      elevation: 1,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Color(0xFFF8F9FC),
      elevation: 0,
      centerTitle: false,
      titleTextStyle: TextStyle(color: Color(0xFF1A1A2E), fontSize: 18, fontWeight: FontWeight.w600),
      iconTheme: IconThemeData(color: Color(0xFF1A1A2E)),
    ),
    bottomNavigationBarTheme: const BottomNavigationBarThemeData(
      backgroundColor: Colors.white,
      selectedItemColor: Color(0xFF6366F1),
      unselectedItemColor: Color(0xFF6B7280),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFFE2E5F0))),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFFE2E5F0))),
      focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF6366F1))),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: const Color(0xFF6366F1),
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      ),
    ),
  );

  static const statusColors = {
    'healthy': Color(0xFF22C55E),
    'active': Color(0xFF22C55E),
    'ok': Color(0xFF22C55E),
    'degraded': Color(0xFFF59E0B),
    'warning': Color(0xFFF59E0B),
    'error': Color(0xFFEF4444),
    'down': Color(0xFFEF4444),
    'failed': Color(0xFFEF4444),
    'pending': Color(0xFF3B82F6),
    'running': Color(0xFF3B82F6),
    'completed': Color(0xFF22C55E),
  };

  static Color statusColor(String status) => statusColors[status.toLowerCase()] ?? const Color(0xFF8888A8);
}
