import pytest
from datetime import datetime, date, time, timedelta, timezone
from backend.scoring import calculate_score, category_weight

SCHOOL_BUFFER_DAYS = 3


def test_category_weight_rank_1():
    w = category_weight(1)
    assert abs(w - 1.0) < 0.01


def test_category_weight_rank_6():
    w = category_weight(6)
    assert abs(w - 0.34) < 0.02


def test_category_weight_higher_rank_wins():
    assert category_weight(1) > category_weight(2) > category_weight(3)


def test_base_score_no_extras():
    """Item with no due date, no cadence, no frequency — just base score."""
    score = calculate_score(
        rank=3,
        due_date=None,
        start_date=None,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        defer_count=0,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=datetime.now(timezone.utc),
    )
    assert score > 0


def test_gated_before_start_date():
    tomorrow = date.today() + timedelta(days=1)
    score = calculate_score(
        rank=1,
        due_date=None,
        start_date=tomorrow,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        defer_count=0,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=datetime.now(timezone.utc),
    )
    assert score == 0


def test_gated_during_deferral():
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    score = calculate_score(
        rank=1,
        due_date=None,
        start_date=None,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        defer_count=1,
        deferred_until=future,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=datetime.now(timezone.utc),
    )
    assert score == 0


def test_overdue_scores_high():
    overdue_date = date.today() - timedelta(days=5)
    not_due = date.today() + timedelta(days=5)
    now = datetime.now(timezone.utc)
    kwargs = dict(
        rank=1,
        start_date=None,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        defer_count=0,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=now,
    )
    overdue_score = calculate_score(due_date=overdue_date, **kwargs)
    normal_score = calculate_score(due_date=not_due, **kwargs)
    assert overdue_score > normal_score


def test_frequency_target_met_gates():
    score = calculate_score(
        rank=1,
        due_date=None,
        start_date=None,
        cadence_days=None,
        frequency_target=3,
        frequency_window_days=7,
        completions_in_window=3,
        last_touched_at=None,
        defer_count=0,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=datetime.now(timezone.utc),
    )
    assert score == 0


def test_avoidance_increases_with_defers():
    now = datetime.now(timezone.utc)
    kwargs = dict(
        rank=1,
        due_date=None,
        start_date=None,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=now,
    )
    score_0 = calculate_score(defer_count=0, **kwargs)
    score_3 = calculate_score(defer_count=3, **kwargs)
    assert score_3 > score_0


def test_outside_time_window_gates():
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    # Window that excludes current time
    window_start = time((current_hour + 2) % 24, 0)
    window_end = time((current_hour + 4) % 24, 0)
    score = calculate_score(
        rank=1,
        due_date=None,
        start_date=None,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        defer_count=0,
        deferred_until=None,
        window_start=window_start,
        window_end=window_end,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=now,
    )
    assert score == 0


def test_baseline_exponential_staleness():
    now = datetime.now(timezone.utc)
    kwargs = dict(
        rank=1,
        due_date=None,
        start_date=None,
        cadence_days=1,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        defer_count=0,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        now=now,
    )
    # Baseline item touched 1 day ago vs 3 days ago
    score_1 = calculate_score(
        last_touched_at=now - timedelta(days=1), is_baseline=True, **kwargs
    )
    score_3 = calculate_score(
        last_touched_at=now - timedelta(days=3), is_baseline=True, **kwargs
    )
    assert score_3 > score_1
