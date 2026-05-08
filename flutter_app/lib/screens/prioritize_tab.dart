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
                  subtitle: Text(
                    'Rank ${cat.rank} - $itemCount items - lead ${cat.leadTimeDays}d',
                  ),
                  onTap: () => _editCategory(cat),
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
    final result = await _showCategoryDialog(
      title: '',
      leadTimeDays: 7,
      weeklyHoursGoal: 0,
      isEdit: false,
    );
    if (result == null) return;
    final api = ref.read(apiServiceProvider);
    final newRank = (_localCategories?.length ?? 0) + 1;
    await api.createCategory(
      result.title,
      newRank,
      leadTimeDays: result.leadTimeDays,
      weeklyHoursGoal: result.weeklyHoursGoal,
    );
    _localCategories = null;
    ref.invalidate(categoriesProvider);
    ref.invalidate(topItemsProvider);
  }

  Future<void> _editCategory(Category cat) async {
    final result = await _showCategoryDialog(
      title: cat.title,
      leadTimeDays: cat.leadTimeDays,
      weeklyHoursGoal: cat.weeklyHoursGoal,
      isEdit: true,
    );
    if (result == null) return;
    final api = ref.read(apiServiceProvider);
    await api.updateCategory(
      cat.id,
      title: result.title != cat.title ? result.title : null,
      leadTimeDays:
          result.leadTimeDays != cat.leadTimeDays ? result.leadTimeDays : null,
      weeklyHoursGoal: result.weeklyHoursGoal != cat.weeklyHoursGoal
          ? result.weeklyHoursGoal
          : null,
    );
    _localCategories = null;
    ref.invalidate(categoriesProvider);
    ref.invalidate(topItemsProvider);
  }

  Future<_CategoryDialogResult?> _showCategoryDialog({
    required String title,
    required int leadTimeDays,
    required double weeklyHoursGoal,
    required bool isEdit,
  }) {
    final controller = TextEditingController(text: title);
    int leadTime = leadTimeDays;
    double hoursGoal = weeklyHoursGoal;
    return showDialog<_CategoryDialogResult>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setState) => AlertDialog(
          title: Text(isEdit ? 'Edit Category' : 'New Category'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: controller,
                  decoration: const InputDecoration(labelText: 'Category name'),
                  autofocus: true,
                ),
                const SizedBox(height: 16),
                Text('Lead time: $leadTime days'),
                const Text(
                  'How early due-date items in this category start ramping up',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
                Slider(
                  value: leadTime.toDouble(),
                  min: 1,
                  max: 30,
                  divisions: 29,
                  label: '$leadTime d',
                  onChanged: (v) => setState(() => leadTime = v.round()),
                ),
                const SizedBox(height: 8),
                Text('Weekly goal: ${hoursGoal.toStringAsFixed(1)} h'),
                const Text(
                  'Hours per week to spend on this category in Pace mode (0 = no goal, hidden from Pace)',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
                Slider(
                  value: hoursGoal.clamp(0, 40),
                  min: 0,
                  max: 40,
                  divisions: 80,
                  label: '${hoursGoal.toStringAsFixed(1)} h',
                  onChanged: (v) => setState(() => hoursGoal = v),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                final t = controller.text.trim();
                if (t.isEmpty) return;
                Navigator.pop(
                  ctx,
                  _CategoryDialogResult(t, leadTime, hoursGoal),
                );
              },
              child: Text(isEdit ? 'Save' : 'Create'),
            ),
          ],
        ),
      ),
    );
  }
}

class _CategoryDialogResult {
  final String title;
  final int leadTimeDays;
  final double weeklyHoursGoal;
  _CategoryDialogResult(this.title, this.leadTimeDays, this.weeklyHoursGoal);
}
