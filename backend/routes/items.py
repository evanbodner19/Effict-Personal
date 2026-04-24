from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.auth import get_current_user_id
from backend.db import get_supabase
from backend.scoring import rescore_all

router = APIRouter(prefix="/api/items", tags=["items"])


class CreateItemRequest(BaseModel):
    title: str
    notes: Optional[str] = None
    category_id: str
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    cadence_days: Optional[int] = None
    frequency_target: Optional[int] = None
    frequency_window_days: Optional[int] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    is_project: bool = False


class UpdateItemRequest(BaseModel):
    title: Optional[str] = None
    notes: Optional[str] = None
    category_id: Optional[str] = None
    start_date: Optional[str] = None
    due_date: Optional[str] = None
    cadence_days: Optional[int] = None
    frequency_target: Optional[int] = None
    frequency_window_days: Optional[int] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    is_project: Optional[bool] = None


@router.post("")
def create_item(body: CreateItemRequest, user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    data = {"user_id": user_id, **body.model_dump(exclude_none=True)}
    resp = supabase.table("items").insert(data).execute()
    rescore_all(supabase, user_id)
    return resp.data[0]


@router.patch("/{item_id}")
def update_item(
    item_id: str, body: UpdateItemRequest, user_id: str = Depends(get_current_user_id)
):
    supabase = get_supabase()
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    resp = (
        supabase.table("items")
        .update(updates)
        .eq("id", item_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Item not found")
    rescore_all(supabase, user_id)
    return resp.data[0]


@router.delete("/{item_id}")
def delete_item(item_id: str, user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    resp = (
        supabase.table("items")
        .update({"completed_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", item_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


@router.post("/{item_id}/complete")
def complete_item(item_id: str, user_id: str = Depends(get_current_user_id)):
    import traceback as tb
    try:
        supabase = get_supabase()
        now = datetime.now(timezone.utc).isoformat()

        # Fetch the item
        resp = (
            supabase.table("items")
            .select("*")
            .eq("id", item_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not resp.data:
            raise HTTPException(status_code=404, detail="Item not found")

        item = resp.data[0]
        is_recurring = item.get("cadence_days") or item.get("frequency_target")

        if is_recurring:
            # Recurring: update last_touched_at, insert completion
            supabase.table("items").update(
                {"last_touched_at": now, "defer_count": 0}
            ).eq("id", item_id).execute()
            supabase.table("completions").insert(
                {"user_id": user_id, "item_id": item_id, "completed_at": now}
            ).execute()
        else:
            # One-time: set completed_at
            supabase.table("items").update({"completed_at": now}).eq(
                "id", item_id
            ).execute()

        if is_recurring:
            # Rescore just this item
            from backend.scoring import rescore_item
            rescore_item(supabase, item_id, user_id)
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        tb.print_exc()
        return {"detail": str(e), "traceback": tb.format_exc()}


@router.post("/{item_id}/defer")
def defer_item(item_id: str, user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()

    # Fetch current defer_count
    resp = (
        supabase.table("items")
        .select("defer_count")
        .eq("id", item_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="Item not found")

    current_count = resp.data[0].get("defer_count", 0)
    new_count = current_count + 1
    defer_hours = 2 + 2**new_count  # 4h, 6h, 10h, 18h, 34h
    deferred_until = datetime.now(timezone.utc) + timedelta(hours=defer_hours)

    supabase.table("items").update(
        {"defer_count": new_count, "deferred_until": deferred_until.isoformat()}
    ).eq("id", item_id).execute()

    from backend.scoring import rescore_item
    rescore_item(supabase, item_id, user_id)
    return {"ok": True, "deferred_until": deferred_until.isoformat()}
