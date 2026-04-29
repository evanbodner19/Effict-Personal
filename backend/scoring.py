import math
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional

SCHOOL_BUFFER_DAYS = 3
BASE_SCORE = 0.75


def category_weight(rank: int) -> float:
    return 1.0 / math.log2(1.15 * rank + 0.85)


def _is_in_time_window(
    now: datetime, window_start: Optional[time], window_end: Optional[time]
) -> bool:
    if window_start is None or window_end is None:
        return True
    current_time = now.time()
    if window_start <= window_end:
        return window_start <= current_time <= window_end
    else:
        # Overnight window (e.g., 20:00 to 02:00)
        return current_time >= window_start or current_time <= window_end


def calculate_score(
    rank: int,
    due_date: Optional[date],
    start_date: Optional[date],
    cadence_days: Optional[int],
    frequency_target: Optional[int],
    frequency_window_days: Optional[int],
    completions_in_window: int,
    last_touched_at: Optional[datetime],
    defer_count: int,
    deferred_until: Optional[datetime],
    window_start: Optional[time],
    window_end: Optional[time],
    external_source: Optional[str],
    external_data: Optional[dict],
    is_baseline: bool,
    now: datetime,
    _debug_title: Optional[str] = None,
) -> float:
    today = date.today()

    def _gate(reason):
        if _debug_title is not None:
            print(f"[score] {_debug_title!r} -> 0 ({reason})")
        return 0

    # Gating rules
    if start_date and today < start_date:
        return _gate(f"start_date {start_date} > today {today}")

    if deferred_until and now < deferred_until:
        return _gate(f"deferred_until {deferred_until} > now {now}")

    if not _is_in_time_window(now, window_start, window_end):
        return _gate(f"outside window {window_start}-{window_end} now={now.time()}")

    if frequency_target and completions_in_window >= frequency_target:
        return _gate(f"freq met {completions_in_window}/{frequency_target}")

    # Urgency
    urgency = 0.0
    effective_due = due_date
    if effective_due:
        if external_source == "canvas":
            effective_due = effective_due - timedelta(days=SCHOOL_BUFFER_DAYS)
        days_until = (effective_due - today).days
        if days_until < 0:
            urgency = 3.0 + abs(days_until) * 0.5
        else:
            urgency = 1.0 / (days_until + 1)

    # Staleness
    staleness = 0.0
    if cadence_days and last_touched_at:
        days_since = (now - last_touched_at).total_seconds() / 86400
        if is_baseline:
            staleness = 2 ** (days_since / cadence_days) - 1
        else:
            staleness = (days_since - cadence_days) / cadence_days

    # Frequency deficit
    freq_deficit = 0.0
    if frequency_target and frequency_target > 0:
        count = completions_in_window
        freq_deficit = max(0, (frequency_target - count) / frequency_target)

    # Avoidance
    avoidance = math.log(defer_count + 1)

    # Total
    raw = BASE_SCORE + urgency + staleness + freq_deficit + avoidance
    score = category_weight(rank) * raw
    if _debug_title is not None:
        print(
            f"[score] {_debug_title!r} rank={rank} u={urgency:.2f} "
            f"s={staleness:.2f} fd={freq_deficit:.2f} av={avoidance:.2f} "
            f"raw={raw:.2f} -> {score:.2f}"
        )
    return score


def rescore_item(supabase, item_id: str, user_id: str, lat: float = None, lng: float = None, tz: str = None):
    """Rescore a single item."""
    import zoneinfo
    now = datetime.now(timezone.utc)
    if tz:
        try:
            local_tz = zoneinfo.ZoneInfo(tz)
            now = now.astimezone(local_tz)
        except (KeyError, Exception):
            pass

    item_resp = supabase.table("items").select("*").eq("id", item_id).eq("user_id", user_id).execute()
    if not item_resp.data:
        return
    item = item_resp.data[0]

    cat_resp = supabase.table("categories").select("*").eq("id", item["category_id"]).execute()
    if not cat_resp.data:
        return
    cat = cat_resp.data[0]

    rank = cat["rank"]
    is_baseline = rank == 1

    w_start = time.fromisoformat(item["window_start"]) if item.get("window_start") else None
    w_end = time.fromisoformat(item["window_end"]) if item.get("window_end") else None

    if is_baseline and lat and lng and tz:
        from backend.integrations.zmanim import compute_prayer_windows
        prayer_windows = compute_prayer_windows(lat, lng, tz, now.date())
        title_lower = item["title"].lower()
        if title_lower in prayer_windows:
            pw = prayer_windows[title_lower]
            w_start = pw["start"]
            w_end = pw["end"]

    completions_in_window = 0
    if item.get("frequency_target"):
        window_days = item.get("frequency_window_days", 7)
        cutoff = now - timedelta(days=window_days)
        comp_resp = (
            supabase.table("completions")
            .select("id", count="exact")
            .eq("item_id", item_id)
            .gte("completed_at", cutoff.isoformat())
            .execute()
        )
        completions_in_window = comp_resp.count or 0

    last_touched = datetime.fromisoformat(item["last_touched_at"]) if item.get("last_touched_at") else None
    deferred_until_val = datetime.fromisoformat(item["deferred_until"]) if item.get("deferred_until") else None

    score = calculate_score(
        rank=rank,
        due_date=date.fromisoformat(item["due_date"]) if item.get("due_date") else None,
        start_date=date.fromisoformat(item["start_date"]) if item.get("start_date") else None,
        cadence_days=item.get("cadence_days"),
        frequency_target=item.get("frequency_target"),
        frequency_window_days=item.get("frequency_window_days"),
        completions_in_window=completions_in_window,
        last_touched_at=last_touched,
        defer_count=item.get("defer_count", 0),
        deferred_until=deferred_until_val,
        window_start=w_start,
        window_end=w_end,
        external_source=item.get("external_source"),
        external_data=item.get("external_data"),
        is_baseline=is_baseline,
        now=now,
    )

    supabase.table("items").update(
        {"priority_score": score, "score_updated_at": now.isoformat()}
    ).eq("id", item_id).execute()


def rescore_all(supabase, user_id: str, lat: float = None, lng: float = None, tz: str = None):
    """Rescore all active items for a user. Updates priority_score in the database."""
    import zoneinfo
    now = datetime.now(timezone.utc)
    # Convert to user's local timezone for time window comparisons
    if tz:
        try:
            local_tz = zoneinfo.ZoneInfo(tz)
            now = now.astimezone(local_tz)
        except (KeyError, Exception):
            pass

    # Fetch categories
    cat_resp = supabase.table("categories").select("*").eq("user_id", user_id).execute()
    categories = {c["id"]: c for c in cat_resp.data}

    # Fetch active items (not completed)
    items_resp = (
        supabase.table("items")
        .select("*")
        .eq("user_id", user_id)
        .is_("completed_at", "null")
        .execute()
    )

    # Pre-fetch all recent completions in one query (last 30 days covers all windows)
    cutoff_30d = (now - timedelta(days=30)).isoformat()
    all_completions = (
        supabase.table("completions")
        .select("item_id, completed_at")
        .eq("user_id", user_id)
        .gte("completed_at", cutoff_30d)
        .execute()
    ).data

    # Group completions by item_id
    completions_by_item: dict[str, list[str]] = {}
    for c in all_completions:
        completions_by_item.setdefault(c["item_id"], []).append(c["completed_at"])

    # Compute Zmanim once if GPS provided
    prayer_windows = None
    if lat and lng and tz:
        from backend.integrations.zmanim import compute_prayer_windows
        prayer_windows = compute_prayer_windows(lat, lng, tz, now.date())

    now_iso = now.isoformat()

    scored = 0
    failed = 0
    for item in items_resp.data:
        try:
            cat = categories.get(item["category_id"])
            if not cat:
                print(f"[score] {item.get('title')!r} skipped: no category {item.get('category_id')}")
                continue

            rank = cat["rank"]
            is_baseline = rank == 1

            w_start = None
            w_end = None
            if item.get("window_start"):
                w_start = time.fromisoformat(item["window_start"])
            if item.get("window_end"):
                w_end = time.fromisoformat(item["window_end"])

            if is_baseline and prayer_windows:
                title_lower = item["title"].lower()
                if title_lower in prayer_windows:
                    pw = prayer_windows[title_lower]
                    w_start = pw["start"]
                    w_end = pw["end"]

            completions_in_window = 0
            if item.get("frequency_target"):
                if item.get("external_source") == "strava" and item.get("external_data"):
                    workouts = item["external_data"]
                    if isinstance(workouts, list):
                        window_days = item.get("frequency_window_days", 7)
                        cutoff = now - timedelta(days=window_days)
                        completions_in_window = sum(
                            1 for w in workouts
                            if datetime.fromisoformat(w.get("start_date", "2000-01-01").replace("Z", "+00:00")) > cutoff
                        )
                else:
                    window_days = item.get("frequency_window_days", 7)
                    cutoff = now - timedelta(days=window_days)
                    item_completions = completions_by_item.get(item["id"], [])
                    completions_in_window = sum(
                        1 for ts in item_completions
                        if datetime.fromisoformat(ts) > cutoff
                    )

            last_touched = None
            if item.get("last_touched_at"):
                last_touched = datetime.fromisoformat(item["last_touched_at"])

            deferred_until = None
            if item.get("deferred_until"):
                deferred_until = datetime.fromisoformat(item["deferred_until"])

            score = calculate_score(
                rank=rank,
                due_date=date.fromisoformat(item["due_date"]) if item.get("due_date") else None,
                start_date=date.fromisoformat(item["start_date"]) if item.get("start_date") else None,
                cadence_days=item.get("cadence_days"),
                frequency_target=item.get("frequency_target"),
                frequency_window_days=item.get("frequency_window_days"),
                completions_in_window=completions_in_window,
                last_touched_at=last_touched,
                defer_count=item.get("defer_count", 0),
                deferred_until=deferred_until,
                window_start=w_start,
                window_end=w_end,
                external_source=item.get("external_source"),
                external_data=item.get("external_data"),
                is_baseline=is_baseline,
                now=now,
                _debug_title=item.get("title"),
            )

            supabase.table("items").update(
                {"priority_score": score, "score_updated_at": now_iso}
            ).eq("id", item["id"]).execute()
            scored += 1
        except Exception as e:
            failed += 1
            print(f"[score] FAILED for {item.get('title')!r}: {type(e).__name__}: {e}")

    print(f"[score] rescore_all: scored={scored} failed={failed} total={len(items_resp.data)}")
