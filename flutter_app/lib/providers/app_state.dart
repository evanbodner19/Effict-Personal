import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../models/item.dart';
import '../models/category.dart';

final apiServiceProvider = Provider((ref) => ApiService());

final topItemsProvider = FutureProvider<List<Item>>((ref) async {
  final api = ref.read(apiServiceProvider);
  return api.getTop();
});

final categoriesProvider = FutureProvider<List<Category>>((ref) async {
  final api = ref.read(apiServiceProvider);
  return api.getCategories();
});
