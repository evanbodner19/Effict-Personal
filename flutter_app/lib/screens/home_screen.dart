import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'perform_tab.dart';
import 'plan_tab.dart';
import 'prioritize_tab.dart';
import '../providers/app_state.dart';
import '../services/update_service.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _currentIndex = 0;
  bool _initialSyncDone = false;

  @override
  void initState() {
    super.initState();
    _initialSync();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) UpdateService.checkForUpdate(context);
    });
  }

  Future<void> _initialSync() async {
    try {
      final api = ref.read(apiServiceProvider);
      await api.syncAll().timeout(const Duration(seconds: 15));
      ref.invalidate(topItemsProvider);
      ref.invalidate(categoriesProvider);
    } catch (_) {
      // Sync failed or timed out — show UI anyway
    }
    if (mounted) setState(() => _initialSyncDone = true);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = [
      const PerformTab(),
      const PlanTab(),
      const PrioritizeTab(),
    ];

    return Scaffold(
      body: _initialSyncDone
          ? tabs[_currentIndex]
          : const Center(child: CircularProgressIndicator()),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.play_arrow), label: 'Perform'),
          NavigationDestination(icon: Icon(Icons.list), label: 'Plan'),
          NavigationDestination(icon: Icon(Icons.sort), label: 'Prioritize'),
        ],
      ),
    );
  }
}
