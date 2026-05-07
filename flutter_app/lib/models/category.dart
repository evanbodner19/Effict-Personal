import 'item.dart';

class Category {
  final String id;
  final String title;
  final int rank;
  final int leadTimeDays;
  final List<Item>? items;

  Category({
    required this.id,
    required this.title,
    required this.rank,
    this.leadTimeDays = 7,
    this.items,
  });

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(
      id: json['id'],
      title: json['title'],
      rank: json['rank'],
      leadTimeDays: json['lead_time_days'] ?? 7,
      items: json['items'] != null
          ? (json['items'] as List)
              .map((i) => Item.fromJson(i as Map<String, dynamic>))
              .toList()
          : null,
    );
  }
}
