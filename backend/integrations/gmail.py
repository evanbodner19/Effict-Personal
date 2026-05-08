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
MAX_MESSAGES_PER_SYNC = 100


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


def _list_message_ids(access_token: str, label_id: str) -> list[str]:
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
                return ids
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return ids


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

    msg_ids = _list_message_ids(access_token, label_id)
    if not msg_ids:
        print("[gmail] no messages with Action label")
        return 0

    # Fetch existing gmail items in one query so we don't re-create.
    existing_resp = (
        supabase.table("items")
        .select("id, external_data, completed_at")
        .eq("user_id", user_id)
        .eq("external_source", "gmail")
        .execute()
    )
    seen_ids: set[str] = set()
    for row in existing_resp.data or []:
        ed = row.get("external_data") or {}
        gid = ed.get("gmail_msg_id") if isinstance(ed, dict) else None
        if gid:
            seen_ids.add(gid)

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
        # Fall back to lowest-priority category (highest rank) so emails don't crowd
        # higher-priority lanes if the user has renamed/removed "Todo List".
        target_cat = max(cat_resp.data, key=lambda c: c.get("rank") or 0)
        print(f"[gmail] no {TARGET_CATEGORY_TITLE!r} category — using {target_cat.get('title')!r}")
    target_cat_id = target_cat["id"]

    created = 0
    skipped_existing = 0
    for msg_id in msg_ids:
        if msg_id in seen_ids:
            skipped_existing += 1
            continue
        try:
            msg = _get_message(access_token, msg_id)
        except httpx.HTTPError as e:
            print(f"[gmail] failed to fetch msg {msg_id}: {e}")
            continue

        thread_id = msg.get("threadId", msg_id)
        title = _subject(msg)
        sender = _sender(msg)
        due = _email_date(msg)
        link = f"https://mail.google.com/mail/u/0/#all/{thread_id}"
        notes = f"From: {sender}\n{link}"

        supabase.table("items").insert(
            {
                "user_id": user_id,
                "title": title,
                "notes": notes,
                "category_id": target_cat_id,
                "due_date": due.isoformat(),
                "external_source": "gmail",
                "external_data": {
                    "gmail_msg_id": msg_id,
                    "gmail_thread_id": thread_id,
                },
            }
        ).execute()
        created += 1

    print(
        f"[gmail] action_messages={len(msg_ids)} created={created} "
        f"skipped_existing={skipped_existing}"
    )
    return created
