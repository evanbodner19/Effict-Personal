import 'item.dart';

class Category {
  final String id;
  final String title;
  final int rank;
  final List<Item>? items;

  Category({
    required this.id,
    required this.title,
    required this.rank,
    this.items,
  });

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(
      id: json['id'],
      title: json['title'],
      rank: json['rank'],
      items: json['items'] != null
          ? (json['items'] as List)
              .map((i) => Item.fromJson(i as Map<String, dynamic>))
              .toList()
          : null,
    );
  }
}
