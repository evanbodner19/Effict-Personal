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
