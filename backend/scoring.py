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
) -> float:
    today = date.today()

    # Gating rules
    if start_date and today < start_date:
        return 0

    if deferred_until and now < deferred_until:
        return 0

    if not _is_in_time_window(now, window_start, window_end):
        return 0

    if frequency_target and completions_in_window >= frequency_target:
        return 0

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
    return category_weight(rank) * raw


def rescore_all(supabase, user_id: str, lat: float = None, lng: float = None, tz: str = None):
    """Rescore all active items for a user. Updates priority_score in the database."""
    now = datetime.now(timezone.utc)

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

    for item in items_resp.data:
        cat = categories.get(item["category_id"])
        if not cat:
            continue

        rank = cat["rank"]
        is_baseline = rank == 1

        # Determine time windows
        w_start = None
        w_end = None
        if item.get("window_start"):
            w_start = time.fromisoformat(item["window_start"])
        if item.get("window_end"):
            w_end = time.fromisoformat(item["window_end"])

        # If this is a baseline prayer item and we have GPS, compute Zmanim windows
        if is_baseline and lat and lng and tz:
            from backend.integrations.zmanim import compute_prayer_windows
            prayer_windows = compute_prayer_windows(lat, lng, tz, now.date())
            title_lower = item["title"].lower()
            if title_lower in prayer_windows:
                pw = prayer_windows[title_lower]
                w_start = pw["start"]
                w_end = pw["end"]

        # Count completions in frequency window
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
                comp_resp = (
                    supabase.table("completions")
                    .select("id", count="exact")
                    .eq("item_id", item["id"])
                    .gte("completed_at", cutoff.isoformat())
                    .execute()
                )
                completions_in_window = comp_resp.count or 0

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
        )

        supabase.table("items").update(
            {"priority_score": score, "score_updated_at": now.isoformat()}
        ).eq("id", item["id"]).execute()
