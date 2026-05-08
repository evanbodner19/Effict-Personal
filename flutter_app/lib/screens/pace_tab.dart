import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/app_state.dart';
import '../models/category.dart';
import '../models/item.dart';
import '../widgets/item_form.dart';

class PaceTab extends ConsumerWidget {
  const PaceTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final paceAsync = ref.watch(paceThisWeekProvider);

    return paceAsync.when(
      data: (data) {
        final cats = (data['categories'] as List? ?? [])
            .cast<Map<String, dynamic>>();
        final activeSession = data['active_session'] as Map<String, dynamic>?;

        if (cats.isEmpty) {
          return const Center(
            child: Padding(
              padding: EdgeInsets.all(32),
              child: Text(
                'No pace goals set yet.\n\nGo to Prioritize and set a weekly hours goal on a category to start tracking.',
                textAlign: TextAlign.center,
              ),
            ),
          );
        }

        return RefreshIndicator(
          onRefresh: () async {
            ref.invalidate(paceThisWeekProvider);
            await ref.read(paceThisWeekProvider.future);
          },
          child: ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: cats.length,
            itemBuilder: (context, i) {
              final c = cats[i];
              final goalH = (c['goal_hours'] as num).toDouble();
              final spentS = (c['spent_seconds'] as num).toInt();
              final spentH = spentS / 3600.0;
              final ratio = goalH > 0 ? (spentH / goalH).clamp(0.0, 1.0) : 0.0;
              final isActive = activeSession != null &&
                  activeSession['category_id'] == c['id'];

              return Card(
                margin: const EdgeInsets.only(bottom: 12),
                child: ListTile(
                  title: Row(
                    children: [
                      Expanded(child: Text(c['title'] as String)),
                      if (isActive)
                        const Icon(Icons.timer, size: 18, color: Colors.green),
                    ],
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      const SizedBox(height: 6),
                      LinearProgressIndicator(
                        value: ratio,
                        minHeight: 6,
                        backgroundColor:
                            Theme.of(context).colorScheme.surfaceContainerHighest,
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${spentH.toStringAsFixed(1)}h / ${goalH.toStringAsFixed(1)}h',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => _openSession(
                    context,
                    ref,
                    categoryId: c['id'] as String,
                    categoryTitle: c['title'] as String,
                    activeSession: isActive ? activeSession : null,
                  ),
                ),
              );
            },
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
    );
  }

  void _openSession(
    BuildContext context,
    WidgetRef ref, {
    required String categoryId,
    required String categoryTitle,
    Map<String, dynamic>? activeSession,
  }) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => SessionScreen(
          categoryId: categoryId,
          categoryTitle: categoryTitle,
          existingSession: activeSession,
        ),
      ),
    );
    // When the session screen returns, refresh pace + categories.
    ref.invalidate(paceThisWeekProvider);
    ref.invalidate(categoriesProvider);
    ref.invalidate(topItemsProvider);
  }
}

class SessionScreen extends ConsumerStatefulWidget {
  final String categoryId;
  final String categoryTitle;
  final Map<String, dynamic>? existingSession;

  const SessionScreen({
    super.key,
    required this.categoryId,
    required this.categoryTitle,
    this.existingSession,
  });

  @override
  ConsumerState<SessionScreen> createState() => _SessionScreenState();
}

class _SessionScreenState extends ConsumerState<SessionScreen> {
  String? _sessionId;
  DateTime? _startedAt;
  Timer? _ticker;
  Duration _elapsed = Duration.zero;
  bool _stopping = false;

  @override
  void initState() {
    super.initState();
    if (widget.existingSession != null) {
      _sessionId = widget.existingSession!['id'] as String;
      _startedAt = DateTime.parse(widget.existingSession!['started_at'] as String);
      _startTicker();
    } else {
      _startSession();
    }
  }

  Future<void> _startSession() async {
    try {
      final api = ref.read(apiServiceProvider);
      final session = await api.startSession(widget.categoryId);
      if (!mounted) return;
      setState(() {
        _sessionId = session['id'] as String;
        _startedAt = DateTime.parse(session['started_at'] as String);
      });
      _startTicker();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text('Could not start: $e')));
      Navigator.pop(context);
    }
  }

  void _startTicker() {
    _ticker?.cancel();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (_startedAt == null) return;
      setState(() {
        _elapsed = DateTime.now().toUtc().difference(_startedAt!.toUtc());
      });
    });
  }

  Future<void> _stopAndExit() async {
    if (_sessionId == null || _stopping) return;
    setState(() => _stopping = true);
    try {
      final api = ref.read(apiServiceProvider);
      await api.stopSession(_sessionId!);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Stop failed: $e')));
      }
    }
    if (mounted) Navigator.pop(context);
  }

  @override
  void dispose() {
    _ticker?.cancel();
    super.dispose();
  }

  String _formatElapsed(Duration d) {
    final h = d.inHours.toString().padLeft(2, '0');
    final m = (d.inMinutes % 60).toString().padLeft(2, '0');
    final s = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$h:$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    final categoriesAsync = ref.watch(categoriesProvider);

    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        await _stopAndExit();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(widget.categoryTitle),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: _stopAndExit,
          ),
        ),
        body: Column(
          children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 24),
              color: Theme.of(context).colorScheme.primaryContainer,
              child: Column(
                children: [
                  Text(
                    _formatElapsed(_elapsed),
                    style: Theme.of(context).textTheme.displayMedium?.copyWith(
                          fontFeatures: const [FontFeature.tabularFigures()],
                        ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _sessionId == null ? 'Starting…' : 'Session running',
                    style: Theme.of(context).textTheme.bodyMedium,
                  ),
                ],
              ),
            ),
            Expanded(
              child: categoriesAsync.when(
                data: (categories) {
                  final cat = categories.firstWhere(
                    (c) => c.id == widget.categoryId,
                    orElse: () => Category(
                      id: widget.categoryId,
                      title: widget.categoryTitle,
                      rank: 0,
                      items: [],
                    ),
                  );
                  final items = (cat.items ?? [])
                      .where((i) => i.priorityScore > 0)
                      .toList();
                  if (items.isEmpty) {
                    return const Center(
                      child: Padding(
                        padding: EdgeInsets.all(24),
                        child: Text(
                          'No items in this category have a score > 0 right now.',
                          textAlign: TextAlign.center,
                        ),
                      ),
                    );
                  }
                  return ListView.builder(
                    padding: const EdgeInsets.only(bottom: 96),
                    itemCount: items.length,
                    itemBuilder: (context, i) =>
                        _SessionItemTile(item: items[i], categories: categories),
                  );
                },
                loading: () =>
                    const Center(child: CircularProgressIndicator()),
                error: (e, _) => Center(child: Text('Error: $e')),
              ),
            ),
          ],
        ),
        floatingActionButton: FloatingActionButton.extended(
          onPressed: _stopping ? null : _stopAndExit,
          icon: const Icon(Icons.stop),
          label: const Text('Stop'),
          backgroundColor: Colors.red,
          foregroundColor: Colors.white,
        ),
      ),
    );
  }
}

class _SessionItemTile extends ConsumerWidget {
  final Item item;
  final List<Category> categories;

  const _SessionItemTile({required this.item, required this.categories});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final subtitleParts = <String>[];
    if (item.dueDate != null) subtitleParts.add('Due: ${item.dueDate}');
    if (item.frequencyTarget != null) {
      subtitleParts.add(
        '${item.completionsInWindow ?? 0}/${item.frequencyTarget}',
      );
    }

    return Dismissible(
      key: ValueKey('session-item-${item.id}'),
      direction: DismissDirection.endToStart,
      background: Container(
        color: Colors.red,
        alignment: Alignment.centerRight,
        padding: const EdgeInsets.only(right: 16),
        child: const Icon(Icons.delete, color: Colors.white),
      ),
      confirmDismiss: (_) async {
        final ok = await showDialog<bool>(
          context: context,
          builder: (ctx) => AlertDialog(
            title: const Text('Delete item?'),
            content: Text('Delete "${item.title}"? This cannot be undone.'),
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
        return ok ?? false;
      },
      onDismissed: (_) async {
        final api = ref.read(apiServiceProvider);
        await api.deleteItem(item.id);
        ref.invalidate(categoriesProvider);
        ref.invalidate(topItemsProvider);
      },
      child: ListTile(
        title: Text(item.title),
        subtitle: subtitleParts.isEmpty ? null : Text(subtitleParts.join(' • ')),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            IconButton(
              icon: const Icon(Icons.check_circle_outline),
              tooltip: 'Complete',
              onPressed: () async {
                final api = ref.read(apiServiceProvider);
                await api.completeItem(item.id);
                ref.invalidate(categoriesProvider);
                ref.invalidate(topItemsProvider);
              },
            ),
            Text(
              item.priorityScore.toStringAsFixed(1),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
          ],
        ),
        onTap: () {
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
        },
      ),
    );
  }
}
