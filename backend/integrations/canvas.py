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
        return 0

    resp = httpx.get(settings.canvas_ical_url)
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.text)

    cutoff = _actionable_days_from_now(3)
    upserted = 0

    cat_resp = (
        supabase.table("categories")
        .select("id")
        .eq("user_id", user_id)
        .eq("rank", 2)
        .execute()
    )
    if not cat_resp.data:
        return 0
    school_cat_id = cat_resp.data[0]["id"]

    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        uid = str(component.get("uid", ""))
        if "assignment" not in uid.lower():
            continue

        dtend = component.get("dtend")
        if not dtend:
            continue
        due = dtend.dt
        if isinstance(due, date) and not hasattr(due, "hour"):
            due_date = due
        else:
            due_date = due.date()

        if due_date > cutoff:
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

    return upserted
