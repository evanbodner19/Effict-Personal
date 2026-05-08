"""Pace mode: per-category weekly time tracking.

Uses a rolling 7-day window for "this week". Sessions auto-close after 3 hours
to prevent zombies — if the user forgets to stop, the spent time is capped at
3h from the start.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from backend.auth import get_current_user_id
from backend.db import get_supabase

router = APIRouter(prefix="/api", tags=["pace"])

AUTO_CLOSE_HOURS = 3
ROLLING_WINDOW_DAYS = 7


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _close_stale_sessions(supabase, user_id: str, now: datetime) -> None:
    """Find any open session older than AUTO_CLOSE_HOURS and close it at start+cap."""
    cutoff = now - timedelta(hours=AUTO_CLOSE_HOURS)
    stale = (
        supabase.table("time_sessions")
        .select("id, started_at")
        .eq("user_id", user_id)
        .is_("ended_at", "null")
        .lt("started_at", cutoff.isoformat())
        .execute()
    )
    for row in stale.data or []:
        started = datetime.fromisoformat(row["started_at"])
        auto_end = started + timedelta(hours=AUTO_CLOSE_HOURS)
        supabase.table("time_sessions").update(
            {"ended_at": auto_end.isoformat()}
        ).eq("id", row["id"]).execute()


@router.post("/categories/{category_id}/sessions/start")
def start_session(
    category_id: str, user_id: str = Depends(get_current_user_id)
):
    supabase = get_supabase()
    now = _now()

    # Verify category belongs to user.
    cat = (
        supabase.table("categories")
        .select("id")
        .eq("id", category_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not cat.data:
        raise HTTPException(status_code=404, detail="Category not found")

    # Auto-close any session that ran past the 3h cap.
    _close_stale_sessions(supabase, user_id, now)

    # Auto-stop any other open session (only one active at a time).
    open_resp = (
        supabase.table("time_sessions")
        .select("id")
        .eq("user_id", user_id)
        .is_("ended_at", "null")
        .execute()
    )
    for row in open_resp.data or []:
        supabase.table("time_sessions").update(
            {"ended_at": now.isoformat()}
        ).eq("id", row["id"]).execute()

    insert = (
        supabase.table("time_sessions")
        .insert({
            "user_id": user_id,
            "category_id": category_id,
            "started_at": now.isoformat(),
        })
        .execute()
    )
    return insert.data[0]


@router.post("/sessions/{session_id}/stop")
def stop_session(session_id: str, user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    now = _now()

    sess = (
        supabase.table("time_sessions")
        .select("id, started_at, ended_at")
        .eq("id", session_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not sess.data:
        raise HTTPException(status_code=404, detail="Session not found")
    row = sess.data[0]
    if row.get("ended_at"):
        return row  # already closed (e.g. auto-stopped); idempotent

    # Cap at AUTO_CLOSE_HOURS from start so a forgotten timer doesn't dump
    # huge time onto the goal.
    started = datetime.fromisoformat(row["started_at"])
    cap = started + timedelta(hours=AUTO_CLOSE_HOURS)
    end = min(now, cap)

    updated = (
        supabase.table("time_sessions")
        .update({"ended_at": end.isoformat()})
        .eq("id", session_id)
        .execute()
    )
    return updated.data[0]


@router.get("/pace/this-week")
def pace_this_week(user_id: str = Depends(get_current_user_id)):
    """Return per-category goal + spent seconds over the rolling 7-day window,
    plus the active session if any. Categories with goal=0 are omitted."""
    supabase = get_supabase()
    now = _now()

    _close_stale_sessions(supabase, user_id, now)

    cats = (
        supabase.table("categories")
        .select("id, title, rank, weekly_hours_goal")
        .eq("user_id", user_id)
        .order("rank")
        .execute()
    )
    cat_rows = [
        c for c in (cats.data or []) if (c.get("weekly_hours_goal") or 0) > 0
    ]
    cat_ids = [c["id"] for c in cat_rows]
    if not cat_ids:
        return {"categories": [], "active_session": None}

    window_start = now - timedelta(days=ROLLING_WINDOW_DAYS)

    # Pull every session for this user that *might* overlap the window:
    # ended_at >= window_start OR ended_at IS NULL (open).
    sessions_resp = (
        supabase.table("time_sessions")
        .select("id, category_id, started_at, ended_at")
        .eq("user_id", user_id)
        .in_("category_id", cat_ids)
        .gte("started_at", (window_start - timedelta(hours=AUTO_CLOSE_HOURS)).isoformat())
        .execute()
    )

    spent_by_cat: dict[str, float] = {cid: 0.0 for cid in cat_ids}
    active_session = None
    for s in sessions_resp.data or []:
        started = datetime.fromisoformat(s["started_at"])
        ended_raw = s.get("ended_at")
        if ended_raw:
            ended = datetime.fromisoformat(ended_raw)
        else:
            # Open session: count up to now (the auto-close pass above already
            # closed anything past the 3h cap).
            ended = now
            active_session = {
                "id": s["id"],
                "category_id": s["category_id"],
                "started_at": s["started_at"],
            }
        # Clip to the rolling window.
        eff_start = max(started, window_start)
        if ended <= eff_start:
            continue
        spent_by_cat[s["category_id"]] = spent_by_cat.get(s["category_id"], 0.0) + (
            ended - eff_start
        ).total_seconds()

    out = []
    for c in cat_rows:
        out.append({
            "id": c["id"],
            "title": c["title"],
            "rank": c["rank"],
            "goal_hours": float(c.get("weekly_hours_goal") or 0),
            "spent_seconds": int(spent_by_cat.get(c["id"], 0)),
        })
    return {"categories": out, "active_session": active_session}
