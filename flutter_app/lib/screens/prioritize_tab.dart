import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/app_state.dart';
import '../models/category.dart';

class PrioritizeTab extends ConsumerStatefulWidget {
  const PrioritizeTab({super.key});

  @override
  ConsumerState<PrioritizeTab> createState() => _PrioritizeTabState();
}

class _PrioritizeTabState extends ConsumerState<PrioritizeTab> {
  List<Category>? _localCategories;

  @override
  Widget build(BuildContext context) {
    final categoriesAsync = ref.watch(categoriesProvider);

    return categoriesAsync.when(
      data: (categories) {
        _localCategories ??= List.from(categories);
        return Scaffold(
          body: ReorderableListView.builder(
            padding: const EdgeInsets.only(top: 8, bottom: 80),
            itemCount: _localCategories!.length,
            onReorder: _onReorder,
            itemBuilder: (context, index) {
              final cat = _localCategories![index];
              final itemCount = cat.items?.length ?? 0;
              return Dismissible(
                key: ValueKey(cat.id),
                direction: itemCount == 0
                    ? DismissDirection.endToStart
                    : DismissDirection.none,
                background: Container(
                  color: Colors.red,
                  alignment: Alignment.centerRight,
                  padding: const EdgeInsets.only(right: 16),
                  child: const Icon(Icons.delete, color: Colors.white),
                ),
                onDismissed: (_) => _deleteCategory(cat),
                child: ListTile(
                  leading: ReorderableDragStartListener(
                    index: index,
                    child: const Icon(Icons.drag_handle),
                  ),
                  title: Text(cat.title),
                  subtitle: Text('Rank ${cat.rank} - $itemCount items'),
                ),
              );
            },
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: _addCategory,
            child: const Icon(Icons.add),
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
    );
  }

  Future<void> _onReorder(int oldIndex, int newIndex) async {
    if (newIndex > oldIndex) newIndex--;
    setState(() {
      final item = _localCategories!.removeAt(oldIndex);
      _localCategories!.insert(newIndex, item);
    });
    final api = ref.read(apiServiceProvider);
    await api.reorderCategories(_localCategories!.map((c) => c.id).toList());
    ref.invalidate(categoriesProvider);
    ref.invalidate(topItemsProvider);
  }

  Future<void> _deleteCategory(Category cat) async {
    final api = ref.read(apiServiceProvider);
    await api.deleteCategory(cat.id);
    setState(() => _localCategories!.remove(cat));
    ref.invalidate(categoriesProvider);
  }

  Future<void> _addCategory() async {
    final controller = TextEditingController();
    final title = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('New Category'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(labelText: 'Category name'),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Create'),
          ),
        ],
      ),
    );
    if (title != null && title.isNotEmpty) {
      final api = ref.read(apiServiceProvider);
      final newRank = (_localCategories?.length ?? 0) + 1;
      await api.createCategory(title, newRank);
      _localCategories = null;
      ref.invalidate(categoriesProvider);
    }
  }
}
