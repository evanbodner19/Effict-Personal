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
                    await api.deferItem(item.id);
                    ref.invalidate(topItemsProvider);
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
}
