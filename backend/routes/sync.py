from typing import Optional
from fastapi import APIRouter, Depends, Query
from backend.auth import get_current_user_id
from backend.db import get_supabase
from backend.scoring import rescore_all
from backend.integrations.strava import sync_strava
from backend.integrations.canvas import sync_canvas
from backend.seed import seed_user_data

router = APIRouter(prefix="/api", tags=["sync"])


@router.post("/sync/canvas")
def sync_canvas_endpoint(user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    count = sync_canvas(user_id, supabase)
    rescore_all(supabase, user_id)
    return {"synced": count}


@router.post("/sync/strava")
def sync_strava_endpoint(user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    count = sync_strava(user_id, supabase)
    rescore_all(supabase, user_id)
    return {"synced": count}


@router.post("/sync/all")
def sync_all(
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    tz: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
):
    supabase = get_supabase()

    # Ensure user has seed data
    seed_user_data(user_id, supabase)

    # Sync integrations
    canvas_count = sync_canvas(user_id, supabase)
    strava_count = sync_strava(user_id, supabase)

    # Rescore with GPS for Zmanim
    rescore_all(supabase, user_id, lat=lat, lng=lng, tz=tz)

    return {
        "canvas_synced": canvas_count,
        "strava_synced": strava_count,
        "rescored": True,
    }


@router.post("/recalculate")
def recalculate(
    lat: Optional[float] = Query(None),
    lng: Optional[float] = Query(None),
    tz: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
):
    supabase = get_supabase()
    rescore_all(supabase, user_id, lat=lat, lng=lng, tz=tz)
    return {"ok": True}
