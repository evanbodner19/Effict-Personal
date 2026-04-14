"""Tests for backend/integrations/zmanim.py — prayer time window computation."""
import pytest
from datetime import date, time

from backend.integrations.zmanim import compute_prayer_windows

# Phoenix, AZ — UTC-7 year-round (no DST), reliable zmanim year-round.
PHOENIX_LAT = 33.4484
PHOENIX_LNG = -112.0740
PHOENIX_TZ = "America/Phoenix"

# April 13, 2026 is a representative spring day for AZ.
APRIL_DATE = date(2026, 4, 13)


@pytest.fixture
def windows():
    return compute_prayer_windows(PHOENIX_LAT, PHOENIX_LNG, PHOENIX_TZ, APRIL_DATE)


def test_returns_all_three_prayers(windows):
    """Result must contain entries for all three daily prayers."""
    assert set(windows.keys()) == {"shacharit", "mincha", "maariv"}


def test_each_entry_has_start_and_end(windows):
    """Each prayer window must have 'start' and 'end' keys."""
    for prayer, window in windows.items():
        assert "start" in window, f"{prayer} missing 'start'"
        assert "end" in window, f"{prayer} missing 'end'"


def test_start_and_end_are_time_objects(windows):
    """Start and end values must be datetime.time instances."""
    for prayer, window in windows.items():
        assert isinstance(window["start"], time), (
            f"{prayer} start is {type(window['start'])}, expected time"
        )
        assert isinstance(window["end"], time), (
            f"{prayer} end is {type(window['end'])}, expected time"
        )


def test_shacharit_starts_before_6am(windows):
    """Shacharit (dawn) in Phoenix in April starts well before 6 AM."""
    shacharit_start = windows["shacharit"]["start"]
    assert shacharit_start < time(6, 0), (
        f"Shacharit start {shacharit_start} expected before 06:00 "
        f"(dawn in Phoenix, April)"
    )


def test_maariv_is_overnight_window(windows):
    """Maariv runs from nightfall to dawn — start should be after end."""
    maariv = windows["maariv"]
    assert maariv["start"] > maariv["end"], (
        f"Maariv start={maariv['start']} should be > end={maariv['end']} "
        f"(overnight crossing)"
    )


def test_shacharit_end_is_mincha_start(windows):
    """Chatzos (solar noon) is both the end of shacharit and start of mincha."""
    assert windows["shacharit"]["end"] == windows["mincha"]["start"]


def test_mincha_end_is_before_maariv_start(windows):
    """Sunset (end of mincha) precedes nightfall (start of maariv)."""
    assert windows["mincha"]["end"] < windows["maariv"]["start"]


def test_ordering_within_day(windows):
    """Dawn < solar noon < sunset < nightfall — all within a single day."""
    dawn = windows["shacharit"]["start"]
    noon = windows["shacharit"]["end"]      # == mincha start
    sunset = windows["mincha"]["end"]
    nightfall = windows["maariv"]["start"]

    assert dawn < noon < sunset < nightfall
