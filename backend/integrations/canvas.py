import httpx
from datetime import date, timedelta
from icalendar import Calendar
from pyluach import dates as pyluach_dates
from backend.config import settings


def _is_actionable_day(d: date) -> bool:
    hebrew = pyluach_dates.GregorianDate(d.year, d.month, d.day).to_heb()
    if d.weekday() == 5:
        return False
    if hebrew.festival(israel=False):
        return False
    return True


def _actionable_days_from_now(n: int) -> date:
    current = date.today()
    count = 0
    while count < n:
        current += timedelta(days=1)
        if _is_actionable_day(current):
            count += 1
    return current


def sync_canvas(user_id: str, supabase) -> int:
    if not settings.canvas_ical_url:
        print("[canvas] no canvas_ical_url configured")
        return 0

    resp = httpx.get(settings.canvas_ical_url, follow_redirects=True)
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.text)

    cutoff = _actionable_days_from_now(14)
    upserted = 0
    skipped_no_date = 0
    skipped_past_cutoff = 0
    total_events = 0

    cat_resp = (
        supabase.table("categories")
        .select("id, rank")
        .eq("user_id", user_id)
        .order("rank")
        .execute()
    )
    if not cat_resp.data:
        print("[canvas] user has no categories")
        return 0
    school_cat = next(
        (c for c in cat_resp.data if c.get("rank") == 2), cat_resp.data[0]
    )
    school_cat_id = school_cat["id"]

    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        total_events += 1
        uid = str(component.get("uid", ""))

        dtend = component.get("dtend") or component.get("dtstart")
        if not dtend:
            skipped_no_date += 1
            continue
        due = dtend.dt
        if isinstance(due, date) and not hasattr(due, "hour"):
            due_date = due
        else:
            due_date = due.date()

        if due_date < date.today():
            continue
        if due_date > cutoff:
            skipped_past_cutoff += 1
            continue

        title = str(component.get("summary", "Untitled Assignment"))

        existing = (
            supabase.table("items")
            .select("id, completed_at")
            .eq("user_id", user_id)
            .eq("external_source", "canvas")
            .eq("title", title)
            .execute()
        )

        if existing.data:
            if existing.data[0].get("completed_at"):
                continue
            supabase.table("items").update({"due_date": due_date.isoformat()}).eq(
                "id", existing.data[0]["id"]
            ).execute()
        else:
            supabase.table("items").insert(
                {
                    "user_id": user_id,
                    "title": title,
                    "category_id": school_cat_id,
                    "due_date": due_date.isoformat(),
                    "external_source": "canvas",
                    "external_data": {"uid": uid},
                }
            ).execute()

        upserted += 1

    print(
        f"[canvas] events={total_events} upserted={upserted} "
        f"skipped_no_date={skipped_no_date} skipped_past_cutoff={skipped_past_cutoff} "
        f"cutoff={cutoff.isoformat()}"
    )
    return upserted
