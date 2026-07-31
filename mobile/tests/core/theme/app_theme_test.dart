import 'package:flutter_test/flutter_test.dart';
import 'package:nova_core_mobile/core/theme/app_theme.dart';
import 'package:flutter/material.dart';

void main() {
  group('AppTheme', () {
    test('dark theme has correct scaffold color', () {
      expect(AppTheme.dark.scaffoldBackgroundColor, const Color(0xFF0A0A0F));
    });

    test('light theme has correct scaffold color', () {
      expect(AppTheme.light.scaffoldBackgroundColor, const Color(0xFFF8F9FC));
    });

    test('dark theme has correct primary color', () {
      expect(AppTheme.dark.colorScheme.primary, const Color(0xFF6366F1));
    });

    test('light theme has correct primary color', () {
      expect(AppTheme.light.colorScheme.primary, const Color(0xFF6366F1));
    });

    test('statusColors map is populated', () {
      expect(AppTheme.statusColors.isNotEmpty, true);
      expect(AppTheme.statusColors.containsKey('healthy'), true);
      expect(AppTheme.statusColors.containsKey('error'), true);
    });

    test('statusColor returns correct colors', () {
      expect(AppTheme.statusColor('healthy'), const Color(0xFF22C55E));
      expect(AppTheme.statusColor('error'), const Color(0xFFEF4444));
      expect(AppTheme.statusColor('warning'), const Color(0xFFF59E0B));
      expect(AppTheme.statusColor('unknown'), const Color(0xFF8888A8));
    });
  });
}
