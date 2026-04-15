class Item {
  final String id;
  final String title;
  final String? notes;
  final String categoryId;
  final String? categoryTitle;
  final int? categoryRank;
  final String? startDate;
  final String? dueDate;
  final int? cadenceDays;
  final int? frequencyTarget;
  final int? frequencyWindowDays;
  final String? windowStart;
  final String? windowEnd;
  final String? externalSource;
  final double priorityScore;
  final int deferCount;
  final String? deferredUntil;
  final bool isProject;

  Item({
    required this.id,
    required this.title,
    this.notes,
    required this.categoryId,
    this.categoryTitle,
    this.categoryRank,
    this.startDate,
    this.dueDate,
    this.cadenceDays,
    this.frequencyTarget,
    this.frequencyWindowDays,
    this.windowStart,
    this.windowEnd,
    this.externalSource,
    this.priorityScore = 0,
    this.deferCount = 0,
    this.deferredUntil,
    this.isProject = false,
  });

  factory Item.fromJson(Map<String, dynamic> json) {
    final categories = json['categories'];
    return Item(
      id: json['id'],
      title: json['title'],
      notes: json['notes'],
      categoryId: json['category_id'],
      categoryTitle: categories != null ? categories['title'] : null,
      categoryRank: categories != null ? categories['rank'] : null,
      startDate: json['start_date'],
      dueDate: json['due_date'],
      cadenceDays: json['cadence_days'],
      frequencyTarget: json['frequency_target'],
      frequencyWindowDays: json['frequency_window_days'],
      windowStart: json['window_start'],
      windowEnd: json['window_end'],
      externalSource: json['external_source'],
      priorityScore: (json['priority_score'] ?? 0).toDouble(),
      deferCount: json['defer_count'] ?? 0,
      deferredUntil: json['deferred_until'],
      isProject: json['is_project'] ?? false,
    );
  }
}
