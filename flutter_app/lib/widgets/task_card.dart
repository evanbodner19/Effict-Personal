import 'package:flutter/material.dart';
import '../models/item.dart';

class TaskCard extends StatelessWidget {
  final Item item;
  final VoidCallback onComplete;
  final VoidCallback onDefer;

  const TaskCard({
    super.key,
    required this.item,
    required this.onComplete,
    required this.onDefer,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (item.categoryTitle != null)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: _categoryColor(item.categoryRank ?? 5),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      item.categoryTitle!,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                      ),
                    ),
                  ),
                const Spacer(),
                if (item.dueDate != null)
                  Text(
                    item.dueDate!,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Text(
                    item.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                Text(
                  item.priorityScore.toStringAsFixed(1),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                FilledButton.tonalIcon(
                  onPressed: onDefer,
                  icon: const Icon(Icons.access_time),
                  label: const Text('Defer'),
                ),
                const SizedBox(width: 8),
                FilledButton.icon(
                  onPressed: onComplete,
                  icon: const Icon(Icons.check),
                  label: const Text('Done'),
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.green,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _categoryColor(int rank) {
    const colors = [
      Colors.indigo,
      Colors.orange,
      Colors.teal,
      Colors.purple,
      Colors.blue,
      Colors.brown,
    ];
    return colors[(rank - 1) % colors.length];
  }
}
