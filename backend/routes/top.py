from fastapi import APIRouter, Depends
from backend.auth import get_current_user_id
from backend.db import get_supabase

router = APIRouter(prefix="/api", tags=["top"])


@router.get("/top")
def get_top(user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    resp = (
        supabase.table("items")
        .select("*, categories(title, rank)")
        .eq("user_id", user_id)
        .is_("completed_at", "null")
        .gt("priority_score", 0)
        .order("priority_score", desc=True)
        .limit(5)
        .execute()
    )
    return resp.data
