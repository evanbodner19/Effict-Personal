import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/app_state.dart';
import '../widgets/task_card.dart';

class PerformTab extends ConsumerWidget {
  const PerformTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final topItems = ref.watch(topItemsProvider);

    return RefreshIndicator(
      onRefresh: () async {
        final api = ref.read(apiServiceProvider);
        await api.syncAll();
        ref.invalidate(topItemsProvider);
      },
      child: topItems.when(
        data: (items) {
          if (items.isEmpty) {
            return ListView(
              children: const [
                SizedBox(height: 200),
                Center(child: Text('No tasks right now')),
              ],
            );
          }
          return ListView.builder(
            padding: const EdgeInsets.only(top: 8, bottom: 16),
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              return TaskCard(
                item: item,
                onComplete: () async {
                  try {
                    final api = ref.read(apiServiceProvider);
                    await api.completeItem(item.id);
                    ref.invalidate(topItemsProvider);
                    ref.invalidate(categoriesProvider);
                  } catch (e) {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('$e')),
                      );
                    }
                  }
                },
                onDefer: () async {
                  try {
                    final api = ref.read(apiServiceProvider);
                    final result = await api.deferItem(item.id);
                    ref.invalidate(topItemsProvider);
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(_deferMessage(result))),
                      );
                    }
                  } catch (e) {
                    if (context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('$e')),
                      );
                    }
                  }
                },
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }

  String _deferMessage(Map<String, dynamic> result) {
    final until = DateTime.tryParse(result['deferred_until'] ?? '')?.toLocal();
    if (until == null) return 'Deferred';
    final now = DateTime.now();
    final diff = until.difference(now);
    final hours = diff.inHours;
    final mins = diff.inMinutes.remainder(60);
    final duration = hours > 0 ? '${hours}h ${mins}m' : '${diff.inMinutes}m';
    final hour = until.hour;
    final ampm = hour >= 12 ? 'PM' : 'AM';
    final h12 = hour % 12 == 0 ? 12 : hour % 12;
    final mm = until.minute.toString().padLeft(2, '0');
    return 'Deferred for $duration (until $h12:$mm $ampm)';
  }
}
