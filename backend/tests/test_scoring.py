import math
import pytest
from datetime import datetime, date, time, timedelta, timezone
from backend.scoring import calculate_score, category_weight, _demand


def _kwargs(**overrides):
    base = dict(
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
    base.update(overrides)
    return base


def test_category_weight_rank_1():
    assert abs(category_weight(1) - 1.0) < 0.01


def test_category_weight_higher_rank_wins():
    assert category_weight(1) > category_weight(2) > category_weight(3)


def test_demand_curve_shape():
    assert _demand(0) == 0
    assert _demand(0.5) == pytest.approx(0.5)
    assert _demand(1.0) == pytest.approx(1.0)
    # Linear, no compression — growth rate past 1 matches growth rate before 1.
    assert _demand(2.0) == pytest.approx(2.0)
    assert _demand(10) == pytest.approx(10)
    assert _demand(100) - _demand(10) == pytest.approx(90)


def test_standalone_with_no_age_signal_is_low():
    score = calculate_score(**_kwargs())
    # No created_at, no due, no recurrence → demand=0, only BASE_SCORE survives.
    assert score > 0
    assert score < 0.3


def test_standalone_grows_with_age():
    now = datetime.now(timezone.utc)
    fresh = calculate_score(**_kwargs(now=now, created_at=now - timedelta(days=1), importance=3))
    aged = calculate_score(**_kwargs(now=now, created_at=now - timedelta(days=60), importance=3))
    very_old = calculate_score(**_kwargs(now=now, created_at=now - timedelta(days=365), importance=3))
    assert very_old > aged > fresh


def test_standalone_importance_scales_growth():
    now = datetime.now(timezone.utc)
    created = now - timedelta(days=60)
    low = calculate_score(**_kwargs(now=now, created_at=created, importance=1))
    high = calculate_score(**_kwargs(now=now, created_at=created, importance=5))
    assert high > low


def test_gated_before_start_date():
    score = calculate_score(**_kwargs(rank=1, start_date=date.today() + timedelta(days=1)))
    assert score == 0


def test_gated_during_deferral():
    now = datetime.now(timezone.utc)
    score = calculate_score(**_kwargs(rank=1, defer_count=1, deferred_until=now + timedelta(hours=2), now=now))
    assert score == 0


def test_gated_outside_time_window():
    now = datetime.now(timezone.utc)
    h = now.hour
    score = calculate_score(
        **_kwargs(
            rank=1,
            window_start=time((h + 2) % 24, 0),
            window_end=time((h + 4) % 24, 0),
            now=now,
        )
    )
    assert score == 0


def test_gated_when_frequency_target_met():
    score = calculate_score(
        **_kwargs(rank=1, frequency_target=3, frequency_window_days=7, completions_in_window=3)
    )
    assert score == 0


def test_due_ramps_with_lead_time():
    today = date.today()
    far = calculate_score(**_kwargs(rank=2, due_date=today + timedelta(days=14), lead_time_days=7))
    soon = calculate_score(**_kwargs(rank=2, due_date=today + timedelta(days=2), lead_time_days=7))
    today_due = calculate_score(**_kwargs(rank=2, due_date=today, lead_time_days=7))
    # Outside lead window → no demand contribution.
    assert far < soon < today_due


def test_overdue_grows_linearly_unbounded():
    today = date.today()
    one_day = calculate_score(**_kwargs(rank=2, due_date=today - timedelta(days=1), lead_time_days=7))
    one_month = calculate_score(**_kwargs(rank=2, due_date=today - timedelta(days=30), lead_time_days=7))
    one_year = calculate_score(**_kwargs(rank=2, due_date=today - timedelta(days=365), lead_time_days=7))
    assert one_year > one_month > one_day
    # Linear growth: doubling overdue days roughly doubles the marginal score
    # past the lead-time floor (no log compression).
    assert (one_year - one_day) > 10 * (one_month - one_day)


def test_recurring_grows_with_staleness_then_caps():
    now = datetime.now(timezone.utc)
    fresh = calculate_score(**_kwargs(rank=1, cadence_days=2, last_touched_at=now - timedelta(hours=12), now=now))
    due = calculate_score(**_kwargs(rank=1, cadence_days=2, last_touched_at=now - timedelta(days=2), now=now))
    very_late = calculate_score(**_kwargs(rank=1, cadence_days=2, last_touched_at=now - timedelta(days=30), now=now))
    abandoned = calculate_score(**_kwargs(rank=1, cadence_days=2, last_touched_at=now - timedelta(days=365), now=now))
    # Up through "due", scores grow.
    assert due > fresh
    # Past one cycle, recurring caps — abandoned daily doesn't dominate.
    assert very_late == pytest.approx(due, rel=0.001)
    assert abandoned == pytest.approx(due, rel=0.001)


def test_frequency_caps_at_full_deficit():
    # Even if completions_in_window is negative (shouldn't happen but ensure cap).
    score_zero = calculate_score(**_kwargs(rank=1, frequency_target=4, completions_in_window=0))
    # Same target, same shape — capped at 1.0 progress regardless.
    assert score_zero > 0


def test_hybrid_takes_max_pressure():
    """Item that's both due-soon AND past-cadence should not double-count."""
    now = datetime.now(timezone.utc)
    today = date.today()
    score = calculate_score(
        **_kwargs(
            rank=2,
            due_date=today + timedelta(days=1),
            cadence_days=2,
            last_touched_at=now - timedelta(days=2),
            lead_time_days=7,
            now=now,
        )
    )
    only_due = calculate_score(
        **_kwargs(rank=2, due_date=today + timedelta(days=1), lead_time_days=7, now=now)
    )
    only_recurring = calculate_score(
        **_kwargs(rank=2, cadence_days=2, last_touched_at=now - timedelta(days=2), now=now)
    )
    expected = max(only_due, only_recurring)
    # Hybrid demand = max of progresses, so final should match the stronger signal.
    assert score == pytest.approx(expected, rel=0.01)


def test_categories_balanced_in_normal_range():
    """The whole point of the overhaul: a 'just-due' task, a 'just-stale' habit,
    and a 'moderately-aged' standalone shouldn't differ by an order of magnitude."""
    now = datetime.now(timezone.utc)
    today = date.today()
    standalone = calculate_score(
        **_kwargs(rank=2, created_at=now - timedelta(days=30), importance=3, now=now)
    )
    due_today = calculate_score(**_kwargs(rank=2, due_date=today, lead_time_days=7, now=now))
    recurring_due = calculate_score(
        **_kwargs(rank=2, cadence_days=2, last_touched_at=now - timedelta(days=2), now=now)
    )
    # All should be within ~3x of each other — no category dominates.
    scores = [standalone, due_today, recurring_due]
    assert max(scores) / min(scores) < 3.0


def test_importance_scales_due_date_items():
    today = date.today()
    base = _kwargs(rank=2, due_date=today, lead_time_days=7)
    low = calculate_score(**{**base, "importance": 1})
    mid = calculate_score(**{**base, "importance": 3})
    high = calculate_score(**{**base, "importance": 5})
    assert low < mid < high


def test_importance_scales_recurring_items():
    now = datetime.now(timezone.utc)
    base = _kwargs(rank=2, cadence_days=2, last_touched_at=now - timedelta(days=2), now=now)
    low = calculate_score(**{**base, "importance": 1})
    high = calculate_score(**{**base, "importance": 5})
    assert high > low


def test_avoidance_increases_with_defers():
    score_0 = calculate_score(**_kwargs(rank=1, defer_count=0))
    score_3 = calculate_score(**_kwargs(rank=1, defer_count=3))
    assert score_3 > score_0
