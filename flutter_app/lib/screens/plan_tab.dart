import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/app_state.dart';
import '../models/category.dart';
import '../models/item.dart';
import '../widgets/item_form.dart';

class PlanTab extends ConsumerWidget {
  const PlanTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categoriesAsync = ref.watch(categoriesProvider);

    return categoriesAsync.when(
      data: (categories) {
        return Scaffold(
          body: ListView.builder(
            padding: const EdgeInsets.only(top: 8, bottom: 80),
            itemCount: categories.length,
            itemBuilder: (context, index) {
              final cat = categories[index];
              return ExpansionTile(
                title: Text(cat.title),
                initiallyExpanded: true,
                children: (cat.items ?? []).map((item) {
                  final subtitleParts = <String>[];
                  if (item.dueDate != null) subtitleParts.add('Due: ${item.dueDate}');
                  if (item.frequencyTarget != null) {
                    subtitleParts.add(
                      '${item.completionsInWindow ?? 0}/${item.frequencyTarget}',
                    );
                  }
                  return Dismissible(
                    key: ValueKey('item-${item.id}'),
                    direction: DismissDirection.endToStart,
                    background: Container(
                      color: Colors.red,
                      alignment: Alignment.centerRight,
                      padding: const EdgeInsets.only(right: 16),
                      child: const Icon(Icons.delete, color: Colors.white),
                    ),
                    confirmDismiss: (_) => _confirmDelete(context, item.title),
                    onDismissed: (_) => _deleteItem(ref, item),
                    child: ListTile(
                      title: Text(item.title),
                      subtitle: subtitleParts.isEmpty
                          ? null
                          : Text(subtitleParts.join(' • ')),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (item.isProject)
                            const Padding(
                              padding: EdgeInsets.only(right: 8),
                              child: Icon(Icons.folder, size: 18),
                            ),
                          Text(
                            item.priorityScore.toStringAsFixed(1),
                            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                  fontWeight: FontWeight.bold,
                                ),
                          ),
                        ],
                      ),
                      onTap: () => _showEditSheet(context, ref, item, categories),
                    ),
                  );
                }).toList(),
              );
            },
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: () => _showCreateSheet(context, ref, categories),
            child: const Icon(Icons.add),
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
    );
  }

  void _showCreateSheet(
      BuildContext context, WidgetRef ref, List<Category> categories) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
        ),
        child: ItemForm(
          categories: categories,
          onSubmit: (data) async {
            Navigator.pop(ctx);
            final api = ref.read(apiServiceProvider);
            await api.createItem(data);
            ref.invalidate(categoriesProvider);
            ref.invalidate(topItemsProvider);
          },
        ),
      ),
    );
  }

  Future<bool> _confirmDelete(BuildContext context, String title) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete item?'),
        content: Text('Delete "$title"? This cannot be undone.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  Future<void> _deleteItem(WidgetRef ref, Item item) async {
    final api = ref.read(apiServiceProvider);
    await api.deleteItem(item.id);
    ref.invalidate(categoriesProvider);
    ref.invalidate(topItemsProvider);
  }

  void _showEditSheet(
      BuildContext context, WidgetRef ref, Item item, List<Category> categories) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
        ),
        child: ItemForm(
          categories: categories,
          existingItem: item,
          onSubmit: (data) async {
            Navigator.pop(ctx);
            final api = ref.read(apiServiceProvider);
            await api.updateItem(item.id, data);
            ref.invalidate(categoriesProvider);
            ref.invalidate(topItemsProvider);
          },
        ),
      ),
    );
  }
}
