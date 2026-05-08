"""Gmail integration: pull messages with the 'Action' label and turn each into an item.

Dedups by Gmail message id, stored in items.external_data.gmail_msg_id. Email date
becomes the due_date so an email from N days ago surfaces as N days overdue. We do
not modify labels — Gmail organization stays untouched.
"""
import base64
import re
from datetime import date, datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from typing import Optional

import httpx

from backend.config import settings

GMAIL_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"
ACTION_LABEL_NAME = "Action"
TARGET_CATEGORY_TITLE = "Todo List"
MAX_MESSAGES_PER_SYNC = 500


def _refresh_access_token() -> str:
    resp = httpx.post(
        GMAIL_TOKEN_URL,
        data={
            "client_id": settings.gmail_client_id,
            "client_secret": settings.gmail_client_secret,
            "refresh_token": settings.gmail_refresh_token,
            "grant_type": "refresh_token",
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _find_label_id(access_token: str, name: str) -> Optional[str]:
    resp = httpx.get(
        f"{GMAIL_API}/labels",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    resp.raise_for_status()
    for label in resp.json().get("labels", []):
        if label.get("name") == name:
            return label.get("id")
    return None


def _list_message_ids(access_token: str, label_id: str) -> tuple[list[str], bool]:
    """Return (message_ids, hit_cap). hit_cap=True means we may have missed
    items beyond the cap, so the caller must NOT auto-complete based on absence."""
    ids: list[str] = []
    page_token: Optional[str] = None
    while True:
        params = {"labelIds": label_id, "maxResults": 100}
        if page_token:
            params["pageToken"] = page_token
        resp = httpx.get(
            f"{GMAIL_API}/messages",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        for m in data.get("messages", []) or []:
            ids.append(m["id"])
            if len(ids) >= MAX_MESSAGES_PER_SYNC:
                return ids, True
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return ids, False


def _get_message(access_token: str, msg_id: str) -> dict:
    # metadata format gives us headers without bloating with body content.
    resp = httpx.get(
        f"{GMAIL_API}/messages/{msg_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "format": "metadata",
            "metadataHeaders": ["Subject", "From", "Date"],
        },
    )
    resp.raise_for_status()
    return resp.json()


def _header(msg: dict, name: str) -> str:
    headers = msg.get("payload", {}).get("headers", []) or []
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def _email_date(msg: dict) -> date:
    """Prefer the Date header; fall back to internalDate (Gmail-side timestamp in ms)."""
    raw = _header(msg, "Date")
    if raw:
        try:
            return parsedate_to_datetime(raw).date()
        except (TypeError, ValueError):
            pass
    internal = msg.get("internalDate")
    if internal:
        try:
            return datetime.fromtimestamp(int(internal) / 1000, tz=timezone.utc).date()
        except (TypeError, ValueError):
            pass
    return date.today()


def _sender(msg: dict) -> str:
    raw = _header(msg, "From")
    name, addr = parseaddr(raw)
    return name or addr or raw or "Unknown"


def _subject(msg: dict) -> str:
    return _header(msg, "Subject").strip() or "(no subject)"


def sync_gmail(user_id: str, supabase) -> int:
    if not (
        settings.gmail_client_id
        and settings.gmail_client_secret
        and settings.gmail_refresh_token
    ):
        print("[gmail] not configured")
        return 0

    access_token = _refresh_access_token()

    label_id = _find_label_id(access_token, ACTION_LABEL_NAME)
    if not label_id:
        print(f"[gmail] no label named {ACTION_LABEL_NAME!r}")
        return 0

    msg_ids, hit_cap = _list_message_ids(access_token, label_id)
    labeled_ids = set(msg_ids)

    cat_resp = (
        supabase.table("categories")
        .select("id, title, rank")
        .eq("user_id", user_id)
        .order("rank")
        .execute()
    )
    if not cat_resp.data:
        print("[gmail] user has no categories")
        return 0
    target_cat = next(
        (c for c in cat_resp.data if (c.get("title") or "").lower() == TARGET_CATEGORY_TITLE.lower()),
        None,
    )
    if not target_cat:
        target_cat = max(cat_resp.data, key=lambda c: c.get("rank") or 0)
        print(f"[gmail] no {TARGET_CATEGORY_TITLE!r} category — using {target_cat.get('title')!r}")
    target_cat_id = target_cat["id"]

    existing_resp = (
        supabase.table("items")
        .select("id, external_data, completed_at")
        .eq("user_id", user_id)
        .eq("external_source", "gmail")
        .execute()
    )
    existing_by_msg: dict[str, dict] = {}
    for row in existing_resp.data or []:
        ed = row.get("external_data") or {}
        gid = ed.get("gmail_msg_id") if isinstance(ed, dict) else None
        if gid:
            existing_by_msg[gid] = row

    today_iso = date.today().isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()

    created = 0
    revived = 0
    completed = 0
    skipped_active = 0

    # Pass 1: walk the labeled list. Create new ones, revive completed ones.
    for msg_id in msg_ids:
        existing = existing_by_msg.get(msg_id)
        if existing is None:
            try:
                msg = _get_message(access_token, msg_id)
            except httpx.HTTPError as e:
                print(f"[gmail] failed to fetch msg {msg_id}: {e}")
                continue
            thread_id = msg.get("threadId", msg_id)
            link = f"https://mail.google.com/mail/u/0/#all/{thread_id}"
            supabase.table("items").insert(
                {
                    "user_id": user_id,
                    "title": _subject(msg),
                    "notes": f"From: {_sender(msg)}\n{link}",
                    "category_id": target_cat_id,
                    "due_date": _email_date(msg).isoformat(),
                    "external_source": "gmail",
                    "external_data": {
                        "gmail_msg_id": msg_id,
                        "gmail_thread_id": thread_id,
                    },
                }
            ).execute()
            created += 1
        elif existing.get("completed_at"):
            # Revive: re-labeled means new info, treat as fresh-actionable.
            supabase.table("items").update(
                {"completed_at": None, "due_date": today_iso}
            ).eq("id", existing["id"]).execute()
            revived += 1
        else:
            skipped_active += 1

    # Pass 2: anything in our DB that's no longer labeled gets auto-completed,
    # but ONLY if we know we got the full label list (didn't hit the pagination cap).
    if not hit_cap:
        for gid, row in existing_by_msg.items():
            if gid in labeled_ids:
                continue
            if row.get("completed_at"):
                continue
            supabase.table("items").update({"completed_at": now_iso}).eq(
                "id", row["id"]
            ).execute()
            completed += 1
    elif existing_by_msg:
        print(
            f"[gmail] hit cap ({MAX_MESSAGES_PER_SYNC}) — skipping auto-complete pass"
        )

    print(
        f"[gmail] labeled={len(msg_ids)} created={created} revived={revived} "
        f"auto_completed={completed} skipped_active={skipped_active} hit_cap={hit_cap}"
    )
    return created + revived
