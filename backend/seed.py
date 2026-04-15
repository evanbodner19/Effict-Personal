DEFAULT_CATEGORIES = [
    {"title": "Baseline", "rank": 1},
    {"title": "School", "rank": 2},
    {"title": "Physical Health", "rank": 3},
    {"title": "Dad's Business", "rank": 4},
    {"title": "Todo List", "rank": 5},
    {"title": "Career", "rank": 6},
]

DEFAULT_ITEMS = [
    {
        "title": "Shacharit",
        "category_rank": 1,
        "cadence_days": 1,
        "frequency_target": 1,
        "frequency_window_days": 1,
    },
    {
        "title": "Mincha",
        "category_rank": 1,
        "cadence_days": 1,
        "frequency_target": 1,
        "frequency_window_days": 1,
    },
    {
        "title": "Maariv",
        "category_rank": 1,
        "cadence_days": 1,
        "frequency_target": 1,
        "frequency_window_days": 1,
    },
    {
        "title": "Hisbodedus",
        "category_rank": 1,
        "cadence_days": 1,
    },
    {
        "title": "Gym",
        "category_rank": 3,
        "frequency_target": 4,
        "frequency_window_days": 7,
        "external_source": "strava",
    },
]


def seed_user_data(user_id: str, supabase) -> None:
    """Create default categories and items for a new user.

    Idempotent — skips if user already has categories.
    """
    existing = (
        supabase.table("categories")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    if existing.count and existing.count > 0:
        return

    # Create categories
    cat_map = {}
    for cat in DEFAULT_CATEGORIES:
        resp = (
            supabase.table("categories")
            .insert({"user_id": user_id, "title": cat["title"], "rank": cat["rank"]})
            .execute()
        )
        cat_map[cat["rank"]] = resp.data[0]["id"]

    # Create items
    for item_def in DEFAULT_ITEMS:
        category_id = cat_map[item_def["category_rank"]]
        item = {
            "user_id": user_id,
            "title": item_def["title"],
            "category_id": category_id,
        }
        for field in [
            "cadence_days", "frequency_target", "frequency_window_days", "external_source"
        ]:
            if field in item_def:
                item[field] = item_def[field]
        supabase.table("items").insert(item).execute()
