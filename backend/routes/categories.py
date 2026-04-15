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
