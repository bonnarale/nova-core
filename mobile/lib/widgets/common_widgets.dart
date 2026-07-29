import 'package:flutter/material.dart';

class MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final String? icon;
  final double? change;
  const MetricCard({super.key, required this.title, required this.value, this.icon, this.change});

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(title, style: const TextStyle(fontSize: 13, color: Color(0xFF8888A8))),
                if (icon != null) Text(icon!, style: const TextStyle(color: Color(0xFF8888A8))),
              ],
            ),
            const SizedBox(height: 8),
            Text(value, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Color(0xFFE8E8F0))),
            if (change != null) ...[
              const SizedBox(height: 4),
              Text(
                '${change! >= 0 ? '+' : ''}${change!.toStringAsFixed(1)}%',
                style: TextStyle(fontSize: 12, color: change! >= 0 ? const Color(0xFF22C55E) : const Color(0xFFEF4444)),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class StatusBadge extends StatelessWidget {
  final String status;
  const StatusBadge({super.key, required this.status});

  static const _colors = {
    'healthy': Color(0xFF22C55E),
    'active': Color(0xFF22C55E),
    'ok': Color(0xFF22C55E),
    'degraded': Color(0xFFF59E0B),
    'warning': Color(0xFFF59E0B),
    'error': Color(0xFFEF4444),
    'down': Color(0xFFEF4444),
    'pending': Color(0xFF3B82F6),
    'running': Color(0xFF3B82F6),
    'completed': Color(0xFF22C55E),
  };

  @override
  Widget build(BuildContext context) {
    final color = _colors[status.toLowerCase()] ?? const Color(0xFF8888A8);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(width: 6, height: 6, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 4),
          Text(status, style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  final String title;
  final String? description;
  final IconData? icon;
  const EmptyState({super.key, required this.title, this.description, this.icon});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon ?? Icons.inbox_outlined, size: 48, color: const Color(0xFF8888A8)),
          const SizedBox(height: 12),
          Text(title, style: const TextStyle(fontSize: 16, color: Color(0xFFE8E8F0), fontWeight: FontWeight.w500)),
          if (description != null) ...[
            const SizedBox(height: 4),
            Text(description!, style: const TextStyle(fontSize: 13, color: Color(0xFF8888A8))),
          ],
        ],
      ),
    );
  }
}

class PageHeader extends StatelessWidget {
  final String title;
  final String? description;
  final Widget? action;
  const PageHeader({super.key, required this.title, this.description, this.action});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(0, 8, 0, 16),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Color(0xFFE8E8F0))),
                if (description != null) Text(description!, style: const TextStyle(fontSize: 13, color: Color(0xFF8888A8))),
              ],
            ),
          ),
          if (action != null) action!,
        ],
      ),
    );
  }
}

class LoadingView extends StatelessWidget {
  const LoadingView({super.key});
  @override
  Widget build(BuildContext context) {
    return const Center(child: CircularProgressIndicator(color: Color(0xFF6366F1)));
  }
}

class ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  const ErrorView({super.key, required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, size: 48, color: Color(0xFFEF4444)),
          const SizedBox(height: 12),
          Text(message, style: const TextStyle(color: Color(0xFF8888A8)), textAlign: TextAlign.center),
          if (onRetry != null) ...[
            const SizedBox(height: 16),
            ElevatedButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ],
      ),
    );
  }
}

class StatBar extends StatelessWidget {
  final String label;
  final double value;
  final double max;
  final Color color;
  const StatBar({super.key, required this.label, required this.value, this.max = 100, this.color = const Color(0xFF6366F1)});

  @override
  Widget build(BuildContext context) {
    final pct = (value / max).clamp(0.0, 1.0);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(width: 80, child: Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF8888A8)))),
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(value: pct, backgroundColor: const Color(0xFF2A2A4A), valueColor: AlwaysStoppedAnimation(color), minHeight: 6),
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(width: 40, child: Text(value.toInt().toString(), style: const TextStyle(fontSize: 12, color: Color(0xFFE8E8F0)), textAlign: TextAlign.right)),
        ],
      ),
    );
  }
}
