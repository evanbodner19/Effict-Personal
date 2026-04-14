import httpx
from datetime import datetime, timedelta, timezone
from backend.config import settings

STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
GYM_TYPES = {"WeightTraining", "Workout", "Crossfit", "RockClimbing"}


def _refresh_access_token() -> str:
    resp = httpx.post(
        STRAVA_TOKEN_URL,
        data={
            "client_id": settings.strava_client_id,
            "client_secret": settings.strava_client_secret,
            "refresh_token": settings.strava_refresh_token,
            "grant_type": "refresh_token",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _fetch_recent_activities(access_token: str) -> list[dict]:
    after = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
    resp = httpx.get(
        STRAVA_ACTIVITIES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params={"after": after, "per_page": 100},
    )
    resp.raise_for_status()
    activities = resp.json()
    return [
        {"type": a["type"], "start_date": a["start_date"], "name": a["name"]}
        for a in activities
        if a.get("type") in GYM_TYPES
    ]


def sync_strava(user_id: str, supabase) -> int:
    if not settings.strava_client_id:
        return 0

    access_token = _refresh_access_token()
    workouts = _fetch_recent_activities(access_token)

    resp = (
        supabase.table("items")
        .select("id")
        .eq("user_id", user_id)
        .eq("external_source", "strava")
        .is_("completed_at", "null")
        .execute()
    )
    if resp.data:
        item_id = resp.data[0]["id"]
        supabase.table("items").update({"external_data": workouts}).eq(
            "id", item_id
        ).execute()

    return len(workouts)
