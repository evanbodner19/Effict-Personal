from datetime import date, time
from zmanim.zmanim_calendar import ZmanimCalendar
from zmanim.util.geo_location import GeoLocation


def compute_prayer_windows(
    lat: float,
    lng: float,
    timezone_str: str,
    target_date: date,
) -> dict[str, dict[str, time]]:
    """Compute halachic prayer windows for a given location and date.

    Returns a dict with keys "shacharit", "mincha", "maariv".
    Each value is a dict with "start" and "end" keys containing time objects.

    Maariv is an overnight window (nightfall → dawn next day), so start > end.
    """
    geo = GeoLocation("location", lat, lng, timezone_str)
    cal = ZmanimCalendar(geo_location=geo, date=target_date)

    alos = cal.alos()        # dawn (alot hashachar) — start of shacharit window
    chatzos = cal.chatzos()  # solar noon — end of shacharit / start of mincha
    shkia = cal.shkia()      # halachic sunset — end of mincha window
    tzais = cal.tzais()      # nightfall (tzait hakochavim) — start of maariv

    if any(t is None for t in [alos, chatzos, shkia, tzais]):
        raise ValueError(
            f"Could not compute zmanim for lat={lat}, lng={lng}, "
            f"tz={timezone_str}, date={target_date}. "
            "One or more required times returned None (polar region or invalid input)."
        )

    return {
        "shacharit": {
            "start": alos.time(),
            "end": chatzos.time(),
        },
        "mincha": {
            "start": chatzos.time(),
            "end": shkia.time(),
        },
        # Maariv is overnight: nightfall tonight → dawn tomorrow.
        # start > end signals the overnight crossing to callers.
        "maariv": {
            "start": tzais.time(),
            "end": alos.time(),
        },
    }
