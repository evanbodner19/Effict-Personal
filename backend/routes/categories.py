from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.auth import get_current_user_id
from backend.db import get_supabase

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CreateCategoryRequest(BaseModel):
    title: str
    rank: int


class ReorderRequest(BaseModel):
    order: list[str]  # list of category IDs in new rank order


@router.get("")
def list_categories(user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    # Fetch all categories
    all_cats = (
        supabase.table("categories")
        .select("*")
        .eq("user_id", user_id)
        .order("rank")
        .execute()
    )
    # Fetch active items per category
    items_resp = (
        supabase.table("items")
        .select("*")
        .eq("user_id", user_id)
        .is_("completed_at", "null")
        .order("priority_score", desc=True)
        .execute()
    )
    # Attach completions_in_window for items with a frequency target so the
    # plan tab can show "X/Y" progress.
    freq_items = [i for i in items_resp.data if i.get("frequency_target")]
    if freq_items:
        now = datetime.now(timezone.utc)
        # Use the widest window of any item to bound the completions query.
        max_window = max(i.get("frequency_window_days") or 7 for i in freq_items)
        cutoff = (now - timedelta(days=max_window)).isoformat()
        completions_resp = (
            supabase.table("completions")
            .select("item_id, completed_at")
            .eq("user_id", user_id)
            .gte("completed_at", cutoff)
            .execute()
        )
        comps_by_item: dict[str, list[str]] = {}
        for c in completions_resp.data:
            comps_by_item.setdefault(c["item_id"], []).append(c["completed_at"])

        for item in freq_items:
            window_days = item.get("frequency_window_days") or 7
            item_cutoff = now - timedelta(days=window_days)
            count = 0
            if item.get("external_source") == "strava" and isinstance(
                item.get("external_data"), list
            ):
                for w in item["external_data"]:
                    sd = (w.get("start_date") or "").replace("Z", "+00:00")
                    try:
                        if datetime.fromisoformat(sd) > item_cutoff:
                            count += 1
                    except ValueError:
                        pass
            else:
                for ts in comps_by_item.get(item["id"], []):
                    try:
                        if datetime.fromisoformat(ts) > item_cutoff:
                            count += 1
                    except ValueError:
                        pass
            item["completions_in_window"] = count

    items_by_cat = {}
    for item in items_resp.data:
        cat_id = item["category_id"]
        if cat_id not in items_by_cat:
            items_by_cat[cat_id] = []
        items_by_cat[cat_id].append(item)

    result = []
    for cat in all_cats.data:
        cat["items"] = items_by_cat.get(cat["id"], [])
        result.append(cat)
    return result


@router.post("")
def create_category(body: CreateCategoryRequest, user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    resp = (
        supabase.table("categories")
        .insert({"user_id": user_id, "title": body.title, "rank": body.rank})
        .execute()
    )
    return resp.data[0]


@router.delete("/{category_id}")
def delete_category(category_id: str, user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    # Check if category has active items
    items = (
        supabase.table("items")
        .select("id", count="exact")
        .eq("category_id", category_id)
        .eq("user_id", user_id)
        .is_("completed_at", "null")
        .execute()
    )
    if items.count and items.count > 0:
        raise HTTPException(status_code=400, detail="Category has active items")
    supabase.table("categories").delete().eq("id", category_id).eq(
        "user_id", user_id
    ).execute()
    return {"ok": True}


@router.put("/reorder")
def reorder_categories(body: ReorderRequest, user_id: str = Depends(get_current_user_id)):
    supabase = get_supabase()
    for i, cat_id in enumerate(body.order, start=1):
        supabase.table("categories").update({"rank": i}).eq("id", cat_id).eq(
            "user_id", user_id
        ).execute()
    return {"ok": True}
