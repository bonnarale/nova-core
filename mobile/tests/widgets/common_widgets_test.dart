import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:nova_core_mobile/widgets/common_widgets.dart';

void main() {
  group('MetricCard', () {
    testWidgets('renders title and value', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: MetricCard(title: 'Status', value: 'OK'))));
      expect(find.text('Status'), findsOneWidget);
      expect(find.text('OK'), findsOneWidget);
    });

    testWidgets('renders with change percentage', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: MetricCard(title: 'Tasks', value: '10', change: 12.5))));
      expect(find.text('+12.5%'), findsOneWidget);
    });

    testWidgets('renders negative change', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: MetricCard(title: 'Errors', value: '3', change: -5))));
      expect(find.text('-5.0%'), findsOneWidget);
    });

    testWidgets('renders with icon', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: MetricCard(title: 'Test', value: '1', icon: '\u2605'))));
      expect(find.text('\u2605'), findsOneWidget);
    });
  });

  group('StatusBadge', () {
    testWidgets('renders status text', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: StatusBadge(status: 'healthy'))));
      expect(find.text('healthy'), findsOneWidget);
    });

    testWidgets('renders error status', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: StatusBadge(status: 'error'))));
      expect(find.text('error'), findsOneWidget);
    });

    testWidgets('renders unknown status', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: StatusBadge(status: 'custom'))));
      expect(find.text('custom'), findsOneWidget);
    });
  });

  group('EmptyState', () {
    testWidgets('renders title', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: EmptyState(title: 'No items'))));
      expect(find.text('No items'), findsOneWidget);
    });

    testWidgets('renders description', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: EmptyState(title: 'Empty', description: 'Nothing here'))));
      expect(find.text('Nothing here'), findsOneWidget);
    });
  });

  group('PageHeader', () {
    testWidgets('renders title', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: PageHeader(title: 'Dashboard'))));
      expect(find.text('Dashboard'), findsOneWidget);
    });

    testWidgets('renders description', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: PageHeader(title: 'Dash', description: 'Overview'))));
      expect(find.text('Overview'), findsOneWidget);
    });

    testWidgets('renders action button', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: PageHeader(title: 'Test', action: ElevatedButton(onPressed: () {}, child: Text('Add'))))));
      expect(find.text('Add'), findsOneWidget);
    });
  });

  group('LoadingView', () {
    testWidgets('renders', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: LoadingView())));
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });
  });

  group('ErrorView', () {
    testWidgets('renders message', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: ErrorView(message: 'Something broke'))));
      expect(find.text('Something broke'), findsOneWidget);
    });

    testWidgets('renders retry button', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: ErrorView(message: 'Error', onRetry: () {}))));
      expect(find.text('Retry'), findsOneWidget);
    });
  });

  group('StatBar', () {
    testWidgets('renders label and value', (tester) async {
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: StatBar(label: 'CPU', value: 75))));
      expect(find.text('CPU'), findsOneWidget);
      expect(find.text('75'), findsOneWidget);
    });
  });
}
