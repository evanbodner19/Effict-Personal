# Effict Personal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile-first task prioritization app (Flutter + Python/FastAPI + Supabase) that surfaces the top 5 most important tasks using a Weighted Gravity scoring model.

**Architecture:** Flutter mobile app authenticates via Supabase Auth and talks to a stateless Python/FastAPI backend on Google Cloud Run. The backend owns all scoring logic and integrations (Strava, Canvas, Zmanim), queries Supabase PostgreSQL using the service role key. No background jobs — all sync is on-demand.

**Tech Stack:** Flutter (Dart), Python 3.11+, FastAPI, supabase-py, Supabase (PostgreSQL + Auth), Google Cloud Run, Docker

**Spec:** `docs/superpowers/specs/2026-04-13-effict-personal-design.md`

---

## File Structure

### Backend (`backend/`)

| File | Responsibility |
|------|---------------|
| `backend/main.py` | FastAPI app creation, CORS middleware, router registration, seed-data endpoint |
| `backend/auth.py` | JWT validation middleware, `get_current_user_id` dependency |
| `backend/db.py` | Supabase client singleton (service role key) |
| `backend/config.py` | Pydantic settings loading env vars |
| `backend/scoring.py` | Weighted gravity scoring: `calculate_score()`, `rescore_all()` |
| `backend/integrations/zmanim.py` | `compute_prayer_windows(lat, lng, timezone, date)` |
| `backend/integrations/strava.py` | `sync_strava(user_id, supabase)` — OAuth refresh + fetch workouts |
| `backend/integrations/canvas.py` | `sync_canvas(user_id, supabase)` — ICS parse + upsert assignments |
| `backend/routes/top.py` | `GET /api/top` |
| `backend/routes/items.py` | Item CRUD, complete, defer |
| `backend/routes/categories.py` | Category CRUD, reorder |
| `backend/routes/sync.py` | `/api/sync/canvas`, `/api/sync/strava`, `/api/sync/all`, `/api/recalculate` |
| `backend/seed.py` | `seed_user_data(user_id, supabase)` — default categories + items |
| `backend/requirements.txt` | Python dependencies |
| `backend/Dockerfile` | Cloud Run container |
| `backend/tests/test_scoring.py` | Unit tests for scoring formula |
| `backend/tests/test_auth.py` | Unit tests for JWT validation |
| `backend/tests/test_routes.py` | Integration tests for API routes |
| `backend/tests/test_integrations.py` | Unit tests for Zmanim computation |

### Database (`supabase/`)

| File | Responsibility |
|------|---------------|
| `supabase/migrations/001_create_tables.sql` | Table creation DDL |
| `supabase/migrations/002_rls_policies.sql` | Row Level Security policies |

### Flutter (`flutter_app/`)

| File | Responsibility |
|------|---------------|
| `flutter_app/lib/main.dart` | App entry point, Supabase init, MaterialApp |
| `flutter_app/lib/services/auth_service.dart` | Login, signup, logout, session management |
| `flutter_app/lib/services/api_service.dart` | HTTP client wrapping all backend calls with JWT |
| `flutter_app/lib/services/location_service.dart` | GPS location fetch + cache |
| `flutter_app/lib/models/category.dart` | Category data class + JSON serialization |
| `flutter_app/lib/models/item.dart` | Item data class + JSON serialization |
| `flutter_app/lib/screens/login_screen.dart` | Email/password login + signup |
| `flutter_app/lib/screens/home_screen.dart` | Bottom nav shell with 3 tabs |
| `flutter_app/lib/screens/perform_tab.dart` | Top 5 items, complete/defer actions |
| `flutter_app/lib/screens/plan_tab.dart` | Items by category, edit, create |
| `flutter_app/lib/screens/prioritize_tab.dart` | Reorder/manage categories |
| `flutter_app/lib/widgets/task_card.dart` | Reusable item card (title, category badge, actions) |
| `flutter_app/lib/widgets/item_form.dart` | Create/edit item form |
| `flutter_app/lib/providers/app_state.dart` | Riverpod providers for categories, items, top5 |
| `flutter_app/pubspec.yaml` | Flutter dependencies |

---

## Task 1: Project Scaffolding & Configuration

**Files:**
- Create: `backend/config.py`, `backend/requirements.txt`, `backend/main.py`, `backend/db.py`

- [ ] **Step 1: Create backend directory structure**

```bash
mkdir -p backend/integrations backend/routes backend/tests
touch backend/__init__.py backend/integrations/__init__.py backend/routes/__init__.py backend/tests/__init__.py
```

- [ ] **Step 2: Write `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
supabase==2.9.1
python-dotenv==1.0.1
pyjwt[crypto]==2.9.0
httpx==0.27.0
zmanim==0.5.1
icalendar==6.0.1
pyluach==2.2.0
pytest==8.3.0
pytest-asyncio==0.24.0
```

- [ ] **Step 3: Write `backend/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_refresh_token: str = ""
    canvas_ical_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 4: Write `backend/db.py`**

```python
from supabase import create_client, Client
from backend.config import settings

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _client
```

- [ ] **Step 5: Write `backend/main.py` (minimal — just health check)**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Effict API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Verify the server starts**

```bash
cd backend
pip install -r requirements.txt
# Create a minimal .env for local dev
echo 'SUPABASE_URL=https://placeholder.supabase.co' > .env
echo 'SUPABASE_SERVICE_ROLE_KEY=placeholder' >> .env
echo 'SUPABASE_JWT_SECRET=placeholder' >> .env
uvicorn backend.main:app --reload
# Visit http://localhost:8000/health — should return {"status": "ok"}
# Ctrl+C to stop
```

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend with FastAPI, config, and Supabase client"
```

---

## Task 2: Database Migration Scripts

**Files:**
- Create: `supabase/migrations/001_create_tables.sql`, `supabase/migrations/002_rls_policies.sql`

- [ ] **Step 1: Write `supabase/migrations/001_create_tables.sql`**

```sql
-- Categories
CREATE TABLE categories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) NOT NULL,
    title text NOT NULL,
    rank integer NOT NULL,
    UNIQUE (user_id, rank)
);

CREATE INDEX idx_categories_user_id ON categories(user_id);

-- Items
CREATE TABLE items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) NOT NULL,
    title text NOT NULL,
    notes text,
    category_id uuid REFERENCES categories(id),
    start_date date,
    due_date date,
    cadence_days integer,
    frequency_target integer,
    frequency_window_days integer,
    window_start time,
    window_end time,
    external_source text,
    external_data jsonb,
    priority_score float DEFAULT 0,
    defer_count integer DEFAULT 0,
    deferred_until timestamptz,
    created_at timestamptz DEFAULT now(),
    completed_at timestamptz,
    last_touched_at timestamptz,
    score_updated_at timestamptz,
    is_project boolean DEFAULT false
);

CREATE INDEX idx_items_user_id ON items(user_id);
CREATE INDEX idx_items_category_id ON items(category_id);
CREATE INDEX idx_items_completed_at ON items(completed_at);

-- Completions
CREATE TABLE completions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) NOT NULL,
    item_id uuid REFERENCES items(id) ON DELETE CASCADE,
    completed_at timestamptz DEFAULT now()
);

CREATE INDEX idx_completions_item_id ON completions(item_id);
CREATE INDEX idx_completions_user_id ON completions(user_id);
```

- [ ] **Step 2: Write `supabase/migrations/002_rls_policies.sql`**

```sql
-- Enable RLS on all tables
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE completions ENABLE ROW LEVEL SECURITY;

-- Categories policies
CREATE POLICY "Users can view own categories"
    ON categories FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own categories"
    ON categories FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own categories"
    ON categories FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own categories"
    ON categories FOR DELETE USING (auth.uid() = user_id);

-- Items policies
CREATE POLICY "Users can view own items"
    ON items FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own items"
    ON items FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own items"
    ON items FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own items"
    ON items FOR DELETE USING (auth.uid() = user_id);

-- Completions policies
CREATE POLICY "Users can view own completions"
    ON completions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own completions"
    ON completions FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own completions"
    ON completions FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users can delete own completions"
    ON completions FOR DELETE USING (auth.uid() = user_id);
```

- [ ] **Step 3: Commit**

```bash
git add supabase/
git commit -m "feat: add database migration scripts for tables and RLS policies"
```

---

## Task 3: JWT Auth Middleware

**Files:**
- Create: `backend/auth.py`, `backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_auth.py`**

```python
import pytest
import jwt
from unittest.mock import patch
from fastapi import HTTPException
from backend.auth import verify_jwt


TEST_SECRET = "test-secret-key-at-least-32-characters-long"


def make_token(payload: dict) -> str:
    return jwt.encode(payload, TEST_SECRET, algorithm="HS256")


def test_valid_token_returns_user_id():
    token = make_token({"sub": "user-123", "exp": 9999999999})
    with patch("backend.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_SECRET
        user_id = verify_jwt(token)
    assert user_id == "user-123"


def test_expired_token_raises():
    token = make_token({"sub": "user-123", "exp": 1000000000})
    with patch("backend.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_SECRET
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(token)
        assert exc_info.value.status_code == 401


def test_invalid_token_raises():
    with patch("backend.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_SECRET
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt("not-a-real-token")
        assert exc_info.value.status_code == 401


def test_missing_sub_raises():
    token = make_token({"exp": 9999999999})
    with patch("backend.auth.settings") as mock_settings:
        mock_settings.supabase_jwt_secret = TEST_SECRET
        with pytest.raises(HTTPException) as exc_info:
            verify_jwt(token)
        assert exc_info.value.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_auth.py -v
```

Expected: ImportError or ModuleNotFoundError — `verify_jwt` doesn't exist yet.

- [ ] **Step 3: Write `backend/auth.py`**

```python
import jwt
from fastapi import Depends, HTTPException, Header
from backend.config import settings


def verify_jwt(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization[7:]
    return verify_jwt(token)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_auth.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py backend/tests/test_auth.py
git commit -m "feat: add JWT auth middleware with Supabase token validation"
```

---

## Task 4: Scoring Engine

**Files:**
- Create: `backend/scoring.py`, `backend/tests/test_scoring.py`

- [ ] **Step 1: Write the failing tests `backend/tests/test_scoring.py`**

```python
import pytest
from datetime import datetime, date, time, timedelta, timezone
from backend.scoring import calculate_score, category_weight

SCHOOL_BUFFER_DAYS = 3


def test_category_weight_rank_1():
    w = category_weight(1)
    assert abs(w - 1.0) < 0.01


def test_category_weight_rank_6():
    w = category_weight(6)
    assert abs(w - 0.34) < 0.02


def test_category_weight_higher_rank_wins():
    assert category_weight(1) > category_weight(2) > category_weight(3)


def test_base_score_no_extras():
    """Item with no due date, no cadence, no frequency — just base score."""
    score = calculate_score(
        rank=3,
        due_date=None,
        start_date=None,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        defer_count=0,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=datetime.now(timezone.utc),
    )
    assert score > 0


def test_gated_before_start_date():
    tomorrow = date.today() + timedelta(days=1)
    score = calculate_score(
        rank=1,
        due_date=None,
        start_date=tomorrow,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        defer_count=0,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=datetime.now(timezone.utc),
    )
    assert score == 0


def test_gated_during_deferral():
    future = datetime.now(timezone.utc) + timedelta(hours=2)
    score = calculate_score(
        rank=1,
        due_date=None,
        start_date=None,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        defer_count=1,
        deferred_until=future,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=datetime.now(timezone.utc),
    )
    assert score == 0


def test_overdue_scores_high():
    overdue_date = date.today() - timedelta(days=5)
    not_due = date.today() + timedelta(days=5)
    now = datetime.now(timezone.utc)
    kwargs = dict(
        rank=1,
        start_date=None,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        defer_count=0,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=now,
    )
    overdue_score = calculate_score(due_date=overdue_date, **kwargs)
    normal_score = calculate_score(due_date=not_due, **kwargs)
    assert overdue_score > normal_score


def test_frequency_target_met_gates():
    score = calculate_score(
        rank=1,
        due_date=None,
        start_date=None,
        cadence_days=None,
        frequency_target=3,
        frequency_window_days=7,
        completions_in_window=3,
        last_touched_at=None,
        defer_count=0,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=datetime.now(timezone.utc),
    )
    assert score == 0


def test_avoidance_increases_with_defers():
    now = datetime.now(timezone.utc)
    kwargs = dict(
        rank=1,
        due_date=None,
        start_date=None,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=now,
    )
    score_0 = calculate_score(defer_count=0, **kwargs)
    score_3 = calculate_score(defer_count=3, **kwargs)
    assert score_3 > score_0


def test_outside_time_window_gates():
    now = datetime.now(timezone.utc)
    current_hour = now.hour
    # Window that excludes current time
    window_start = time((current_hour + 2) % 24, 0)
    window_end = time((current_hour + 4) % 24, 0)
    score = calculate_score(
        rank=1,
        due_date=None,
        start_date=None,
        cadence_days=None,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        last_touched_at=None,
        defer_count=0,
        deferred_until=None,
        window_start=window_start,
        window_end=window_end,
        external_source=None,
        external_data=None,
        is_baseline=False,
        now=now,
    )
    assert score == 0


def test_baseline_exponential_staleness():
    now = datetime.now(timezone.utc)
    kwargs = dict(
        rank=1,
        due_date=None,
        start_date=None,
        cadence_days=1,
        frequency_target=None,
        frequency_window_days=None,
        completions_in_window=0,
        defer_count=0,
        deferred_until=None,
        window_start=None,
        window_end=None,
        external_source=None,
        external_data=None,
        now=now,
    )
    # Baseline item touched 1 day ago vs 3 days ago
    score_1 = calculate_score(
        last_touched_at=now - timedelta(days=1), is_baseline=True, **kwargs
    )
    score_3 = calculate_score(
        last_touched_at=now - timedelta(days=3), is_baseline=True, **kwargs
    )
    assert score_3 > score_1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_scoring.py -v
```

Expected: ImportError — `calculate_score` doesn't exist yet.

- [ ] **Step 3: Write `backend/scoring.py`**

```python
import math
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional

SCHOOL_BUFFER_DAYS = 3
BASE_SCORE = 0.75


def category_weight(rank: int) -> float:
    return 1.0 / math.log2(0.75 * rank + 1.25)


def _is_in_time_window(
    now: datetime, window_start: Optional[time], window_end: Optional[time]
) -> bool:
    if window_start is None or window_end is None:
        return True
    current_time = now.time()
    if window_start <= window_end:
        return window_start <= current_time <= window_end
    else:
        # Overnight window (e.g., 20:00 to 02:00)
        return current_time >= window_start or current_time <= window_end


def calculate_score(
    rank: int,
    due_date: Optional[date],
    start_date: Optional[date],
    cadence_days: Optional[int],
    frequency_target: Optional[int],
    frequency_window_days: Optional[int],
    completions_in_window: int,
    last_touched_at: Optional[datetime],
    defer_count: int,
    deferred_until: Optional[datetime],
    window_start: Optional[time],
    window_end: Optional[time],
    external_source: Optional[str],
    external_data: Optional[dict],
    is_baseline: bool,
    now: datetime,
) -> float:
    today = now.date()

    # Gating rules
    if start_date and today < start_date:
        return 0

    if deferred_until and now < deferred_until:
        return 0

    if not _is_in_time_window(now, window_start, window_end):
        return 0

    if frequency_target and completions_in_window >= frequency_target:
        return 0

    # Urgency
    urgency = 0.0
    effective_due = due_date
    if effective_due:
        # School buffer
        if external_source == "canvas":
            effective_due = effective_due - timedelta(days=SCHOOL_BUFFER_DAYS)
        days_until = (effective_due - today).days
        if days_until < 0:
            urgency = 3.0 + abs(days_until) * 0.5
        else:
            urgency = 1.0 / (days_until + 1)

    # Staleness
    staleness = 0.0
    if cadence_days and last_touched_at:
        days_since = (now - last_touched_at).total_seconds() / 86400
        if is_baseline:
            staleness = 2 ** (days_since / cadence_days) - 1
        else:
            staleness = (days_since - cadence_days) / cadence_days

    # Frequency deficit
    freq_deficit = 0.0
    if frequency_target and frequency_target > 0:
        # For Strava items, count from external_data
        count = completions_in_window
        freq_deficit = max(0, (frequency_target - count) / frequency_target)

    # Avoidance
    avoidance = math.log(defer_count + 1)

    # Total
    raw = BASE_SCORE + urgency + staleness + freq_deficit + avoidance
    return category_weight(rank) * raw


def rescore_all(supabase, user_id: str, lat: float = None, lng: float = None, tz: str = None):
    """Rescore all active items for a user. Updates priority_score in the database."""
    now = datetime.now(timezone.utc)

    # Fetch categories
    cat_resp = supabase.table("categories").select("*").eq("user_id", user_id).execute()
    categories = {c["id"]: c for c in cat_resp.data}

    # Fetch active items (not completed)
    items_resp = (
        supabase.table("items")
        .select("*")
        .eq("user_id", user_id)
        .is_("completed_at", "null")
        .execute()
    )

    for item in items_resp.data:
        cat = categories.get(item["category_id"])
        if not cat:
            continue

        rank = cat["rank"]
        is_baseline = rank == 1

        # Determine time windows — for prayer items, compute from Zmanim
        w_start = None
        w_end = None
        if item.get("window_start"):
            w_start = time.fromisoformat(item["window_start"])
        if item.get("window_end"):
            w_end = time.fromisoformat(item["window_end"])

        # If this is a baseline prayer item and we have GPS, compute Zmanim windows
        if is_baseline and lat and lng and tz:
            from backend.integrations.zmanim import compute_prayer_windows
            prayer_windows = compute_prayer_windows(lat, lng, tz, now.date())
            title_lower = item["title"].lower()
            if title_lower in prayer_windows:
                pw = prayer_windows[title_lower]
                w_start = pw["start"]
                w_end = pw["end"]

        # Count completions in frequency window
        completions_in_window = 0
        if item.get("frequency_target"):
            if item.get("external_source") == "strava" and item.get("external_data"):
                # Count workouts from external_data
                workouts = item["external_data"]
                if isinstance(workouts, list):
                    window_days = item.get("frequency_window_days", 7)
                    cutoff = now - timedelta(days=window_days)
                    completions_in_window = sum(
                        1 for w in workouts
                        if datetime.fromisoformat(w.get("start_date", "2000-01-01")) > cutoff
                    )
            else:
                window_days = item.get("frequency_window_days", 7)
                cutoff = now - timedelta(days=window_days)
                comp_resp = (
                    supabase.table("completions")
                    .select("id", count="exact")
                    .eq("item_id", item["id"])
                    .gte("completed_at", cutoff.isoformat())
                    .execute()
                )
                completions_in_window = comp_resp.count or 0

        last_touched = None
        if item.get("last_touched_at"):
            last_touched = datetime.fromisoformat(item["last_touched_at"])

        deferred_until = None
        if item.get("deferred_until"):
            deferred_until = datetime.fromisoformat(item["deferred_until"])

        score = calculate_score(
            rank=rank,
            due_date=date.fromisoformat(item["due_date"]) if item.get("due_date") else None,
            start_date=date.fromisoformat(item["start_date"]) if item.get("start_date") else None,
            cadence_days=item.get("cadence_days"),
            frequency_target=item.get("frequency_target"),
            frequency_window_days=item.get("frequency_window_days"),
            completions_in_window=completions_in_window,
            last_touched_at=last_touched,
            defer_count=item.get("defer_count", 0),
            deferred_until=deferred_until,
            window_start=w_start,
            window_end=w_end,
            external_source=item.get("external_source"),
            external_data=item.get("external_data"),
            is_baseline=is_baseline,
            now=now,
        )

        supabase.table("items").update(
            {"priority_score": score, "score_updated_at": now.isoformat()}
        ).eq("id", item["id"]).execute()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_scoring.py -v
```

Expected: All 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/scoring.py backend/tests/test_scoring.py
git commit -m "feat: implement weighted gravity scoring engine with gating rules"
```

---

## Task 5: Zmanim Integration

**Files:**
- Create: `backend/integrations/zmanim.py`, `backend/tests/test_integrations.py`

- [ ] **Step 1: Write the failing test `backend/tests/test_integrations.py`**

```python
import pytest
from datetime import date, time
from backend.integrations.zmanim import compute_prayer_windows


def test_compute_prayer_windows_returns_three_prayers():
    # Chandler, AZ
    windows = compute_prayer_windows(33.31, -111.84, "America/Phoenix", date(2026, 4, 13))
    assert "shacharit" in windows
    assert "mincha" in windows
    assert "maariv" in windows


def test_prayer_windows_have_start_and_end():
    windows = compute_prayer_windows(33.31, -111.84, "America/Phoenix", date(2026, 4, 13))
    for name, window in windows.items():
        assert "start" in window
        assert "end" in window
        assert isinstance(window["start"], time)
        assert isinstance(window["end"], time)


def test_shacharit_starts_at_dawn():
    windows = compute_prayer_windows(33.31, -111.84, "America/Phoenix", date(2026, 4, 13))
    shacharit = windows["shacharit"]
    # Dawn should be before 6 AM in April in AZ
    assert shacharit["start"].hour < 6


def test_maariv_is_overnight_window():
    windows = compute_prayer_windows(33.31, -111.84, "America/Phoenix", date(2026, 4, 13))
    maariv = windows["maariv"]
    # Maariv starts after sunset, ends after midnight (overnight)
    assert maariv["start"] > maariv["end"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_integrations.py -v
```

Expected: ImportError — module doesn't exist.

- [ ] **Step 3: Write `backend/integrations/zmanim.py`**

```python
from datetime import date, time
from zmanim.zmanim_calendar import ZmanimCalendar
from zmanim.util.geo_location import GeoLocation
from java.util import TimeZone  # zmanim library uses this


def compute_prayer_windows(
    lat: float, lng: float, timezone_str: str, target_date: date
) -> dict[str, dict[str, time]]:
    """Compute prayer time windows for the given location and date.

    Returns a dict keyed by prayer name (lowercase) with 'start' and 'end' times.
    """
    location = GeoLocation(
        "location", lat, lng, 370.0, TimeZone.getTimeZone(timezone_str)
    )
    calendar = ZmanimCalendar(geo_location=location, date=target_date)

    alos = calendar.alos()  # dawn
    sunrise = calendar.sunrise()
    chatzos = calendar.chatzos()  # solar noon
    sunset = calendar.sunset()
    tzais = calendar.tzais()  # nightfall

    return {
        "shacharit": {
            "start": alos.time() if alos else time(5, 0),
            "end": chatzos.time() if chatzos else time(12, 0),
        },
        "mincha": {
            "start": chatzos.time() if chatzos else time(12, 0),
            "end": sunset.time() if sunset else time(19, 0),
        },
        "maariv": {
            "start": tzais.time() if tzais else time(20, 0),
            "end": alos.time() if alos else time(5, 0),  # overnight window
        },
    }
```

> **Note:** The `zmanim` Python library's API may differ from the above — the exact method names (`alos()`, `sunrise()`, `chatzos()`, `tzais()`, etc.) and the `GeoLocation` constructor should be verified against the installed version. The POC already uses this library, so check the POC code for the exact API. The pattern above captures the logic correctly; adjust method names as needed during implementation.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_integrations.py -v
```

Expected: All 4 tests PASS. (If the `zmanim` library API differs, adjust method names and rerun.)

- [ ] **Step 5: Commit**

```bash
git add backend/integrations/zmanim.py backend/tests/test_integrations.py
git commit -m "feat: add Zmanim integration for dynamic prayer time windows"
```

---

## Task 6: Strava Integration

**Files:**
- Create: `backend/integrations/strava.py`

- [ ] **Step 1: Write `backend/integrations/strava.py`**

```python
import httpx
from datetime import datetime, timedelta, timezone
from backend.config import settings

STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
GYM_TYPES = {"WeightTraining", "Workout", "Crossfit", "RockClimbing"}


def _refresh_access_token() -> str:
    """Exchange refresh token for a fresh access token."""
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
    """Fetch last 30 days of activities, filtered to gym types."""
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
    """Sync Strava gym workouts into the user's Strava-linked item.

    Returns the number of workouts found.
    """
    if not settings.strava_client_id:
        return 0

    access_token = _refresh_access_token()
    workouts = _fetch_recent_activities(access_token)

    # Find the user's Strava item
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/integrations/strava.py
git commit -m "feat: add Strava integration for gym workout syncing"
```

---

## Task 7: Canvas Integration

**Files:**
- Create: `backend/integrations/canvas.py`

- [ ] **Step 1: Write `backend/integrations/canvas.py`**

```python
import httpx
from datetime import date, timedelta
from icalendar import Calendar
from pyluach import dates as pyluach_dates
from backend.config import settings


def _is_actionable_day(d: date) -> bool:
    """Check if a date is actionable (not Shabbos or Yom Tov)."""
    hebrew = pyluach_dates.GregorianDate(d.year, d.month, d.day).to_heb()
    # Saturday = Shabbos
    if d.weekday() == 5:
        return False
    # Check for Yom Tov
    if hebrew.festival(israel=False):
        return False
    return True


def _actionable_days_from_now(n: int) -> date:
    """Return the date that is n actionable days from today."""
    current = date.today()
    count = 0
    while count < n:
        current += timedelta(days=1)
        if _is_actionable_day(current):
            count += 1
    return current


def sync_canvas(user_id: str, supabase) -> int:
    """Sync Canvas assignments from ICS feed.

    Only imports assignments due within 3 actionable days.
    Returns the number of assignments upserted.
    """
    if not settings.canvas_ical_url:
        return 0

    resp = httpx.get(settings.canvas_ical_url)
    resp.raise_for_status()
    cal = Calendar.from_ical(resp.text)

    cutoff = _actionable_days_from_now(3)
    upserted = 0

    # Get the School category (rank 2) for this user
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

        # Check if already exists (by external_source + title match)
        existing = (
            supabase.table("items")
            .select("id, completed_at")
            .eq("user_id", user_id)
            .eq("external_source", "canvas")
            .eq("title", title)
            .execute()
        )

        if existing.data:
            # Don't resurrect completed items
            if existing.data[0].get("completed_at"):
                continue
            # Update due date
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
```

- [ ] **Step 2: Commit**

```bash
git add backend/integrations/canvas.py
git commit -m "feat: add Canvas ICS integration with Shabbos/Yom Tov filtering"
```

---

## Task 8: Seed Data

**Files:**
- Create: `backend/seed.py`

- [ ] **Step 1: Write `backend/seed.py`**

```python
from datetime import time


DEFAULT_CATEGORIES = [
    {"title": "Baseline", "rank": 1},
    {"title": "School", "rank": 2},
    {"title": "Physical Health", "rank": 3},
    {"title": "Dad's Business", "rank": 4},
    {"title": "Todo List", "rank": 5},
    {"title": "Career", "rank": 6},
]

DEFAULT_ITEMS = [
    {
        "title": "Shacharit",
        "category_rank": 1,
        "cadence_days": 1,
        "frequency_target": 1,
        "frequency_window_days": 1,
    },
    {
        "title": "Mincha",
        "category_rank": 1,
        "cadence_days": 1,
        "frequency_target": 1,
        "frequency_window_days": 1,
    },
    {
        "title": "Maariv",
        "category_rank": 1,
        "cadence_days": 1,
        "frequency_target": 1,
        "frequency_window_days": 1,
    },
    {
        "title": "Hisbodedus",
        "category_rank": 1,
        "cadence_days": 1,
    },
    {
        "title": "Gym",
        "category_rank": 3,
        "frequency_target": 4,
        "frequency_window_days": 7,
        "external_source": "strava",
    },
]


def seed_user_data(user_id: str, supabase) -> None:
    """Create default categories and items for a new user.

    Idempotent — skips if user already has categories.
    """
    existing = (
        supabase.table("categories")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    if existing.count and existing.count > 0:
        return

    # Create categories
    cat_map = {}
    for cat in DEFAULT_CATEGORIES:
        resp = (
            supabase.table("categories")
            .insert({"user_id": user_id, "title": cat["title"], "rank": cat["rank"]})
            .execute()
        )
        cat_map[cat["rank"]] = resp.data[0]["id"]

    # Create items
    for item_def in DEFAULT_ITEMS:
        category_id = cat_map[item_def["category_rank"]]
        item = {
            "user_id": user_id,
            "title": item_def["title"],
            "category_id": category_id,
        }
        for field in [
            "cadence_days", "frequency_target", "frequency_window_days", "external_source"
        ]:
            if field in item_def:
                item[field] = item_def[field]
        supabase.table("items").insert(item).execute()
```

- [ ] **Step 2: Commit**

```bash
git add backend/seed.py
git commit -m "feat: add seed data for default categories and items"
```

---

## Task 9: API Routes — Categories

**Files:**
- Create: `backend/routes/categories.py`

- [ ] **Step 1: Write `backend/routes/categories.py`**

```python
from fastapi import APIRouter, Depends
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
    resp = (
        supabase.table("categories")
        .select("*, items!inner(*)") 
        .eq("user_id", user_id)
        .order("rank")
        .execute()
    )
    # Also fetch categories without items
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
    # Check if category has items
    items = (
        supabase.table("items")
        .select("id", count="exact")
        .eq("category_id", category_id)
        .eq("user_id", user_id)
        .is_("completed_at", "null")
        .execute()
    )
    if items.count and items.count > 0:
        from fastapi import HTTPException
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
```

- [ ] **Step 2: Register router in `backend/main.py`**

Add to `backend/main.py`:

```python
from backend.routes.categories import router as categories_router

app.include_router(categories_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/routes/categories.py backend/main.py
git commit -m "feat: add category API routes (CRUD, reorder)"
```

---

## Task 10: API Routes — Items

**Files:**
- Create: `backend/routes/items.py`

- [ ] **Step 1: Write `backend/routes/items.py`**

```python
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

    rescore_all(supabase, user_id)
    return {"ok": True}


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

    rescore_all(supabase, user_id)
    return {"ok": True, "deferred_until": deferred_until.isoformat()}
```

- [ ] **Step 2: Register router in `backend/main.py`**

Add to `backend/main.py`:

```python
from backend.routes.items import router as items_router

app.include_router(items_router)
```

- [ ] **Step 3: Commit**

```bash
git add backend/routes/items.py backend/main.py
git commit -m "feat: add item API routes (CRUD, complete, defer)"
```

---

## Task 11: API Routes — Top & Sync

**Files:**
- Create: `backend/routes/top.py`, `backend/routes/sync.py`

- [ ] **Step 1: Write `backend/routes/top.py`**

```python
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
```

- [ ] **Step 2: Write `backend/routes/sync.py`**

```python
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
```

- [ ] **Step 3: Register routers in `backend/main.py`**

Add to `backend/main.py`:

```python
from backend.routes.top import router as top_router
from backend.routes.sync import router as sync_router

app.include_router(top_router)
app.include_router(sync_router)
```

- [ ] **Step 4: Commit**

```bash
git add backend/routes/top.py backend/routes/sync.py backend/main.py
git commit -m "feat: add top-5 and sync API routes"
```

---

## Task 12: Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 2: Verify Docker build works**

```bash
cd backend
docker build -t effict-api .
```

Expected: Build succeeds.

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat: add Dockerfile for Cloud Run deployment"
```

---

## Task 13: Flutter Project Scaffolding

**Files:**
- Create: `flutter_app/` (Flutter project), `flutter_app/pubspec.yaml`, `flutter_app/lib/main.dart`

- [ ] **Step 1: Create Flutter project**

```bash
flutter create --org com.effict flutter_app
```

- [ ] **Step 2: Update `flutter_app/pubspec.yaml` dependencies**

Add under `dependencies:`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  supabase_flutter: ^2.5.0
  flutter_riverpod: ^2.5.0
  http: ^1.2.0
  geolocator: ^12.0.0
```

- [ ] **Step 3: Install dependencies**

```bash
cd flutter_app
flutter pub get
```

- [ ] **Step 4: Write `flutter_app/lib/main.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';

// TODO: Replace with your actual Supabase credentials
const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
const supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Supabase.initialize(url: supabaseUrl, anonKey: supabaseAnonKey);
  runApp(const ProviderScope(child: EffictApp()));
}

class EffictApp extends StatelessWidget {
  const EffictApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Effict',
      theme: ThemeData(
        colorSchemeSeed: Colors.indigo,
        useMaterial3: true,
      ),
      home: Supabase.instance.client.auth.currentSession != null
          ? const HomeScreen()
          : const LoginScreen(),
    );
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add flutter_app/
git commit -m "feat: scaffold Flutter project with Supabase and Riverpod"
```

---

## Task 14: Flutter Models

**Files:**
- Create: `flutter_app/lib/models/category.dart`, `flutter_app/lib/models/item.dart`

- [ ] **Step 1: Write `flutter_app/lib/models/category.dart`**

```dart
class Category {
  final String id;
  final String title;
  final int rank;
  final List<Item>? items;

  Category({
    required this.id,
    required this.title,
    required this.rank,
    this.items,
  });

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(
      id: json['id'],
      title: json['title'],
      rank: json['rank'],
      items: json['items'] != null
          ? (json['items'] as List).map((i) => Item.fromJson(i)).toList()
          : null,
    );
  }
}

// Forward reference — Item is defined in item.dart
import 'item.dart';
```

> **Note:** The import at the bottom is intentional for the forward reference. In practice, move the import to the top of the file during implementation.

- [ ] **Step 2: Write `flutter_app/lib/models/item.dart`**

```dart
class Item {
  final String id;
  final String title;
  final String? notes;
  final String categoryId;
  final String? categoryTitle;
  final int? categoryRank;
  final String? startDate;
  final String? dueDate;
  final int? cadenceDays;
  final int? frequencyTarget;
  final int? frequencyWindowDays;
  final String? windowStart;
  final String? windowEnd;
  final String? externalSource;
  final double priorityScore;
  final int deferCount;
  final String? deferredUntil;
  final bool isProject;

  Item({
    required this.id,
    required this.title,
    this.notes,
    required this.categoryId,
    this.categoryTitle,
    this.categoryRank,
    this.startDate,
    this.dueDate,
    this.cadenceDays,
    this.frequencyTarget,
    this.frequencyWindowDays,
    this.windowStart,
    this.windowEnd,
    this.externalSource,
    this.priorityScore = 0,
    this.deferCount = 0,
    this.deferredUntil,
    this.isProject = false,
  });

  factory Item.fromJson(Map<String, dynamic> json) {
    final categories = json['categories'];
    return Item(
      id: json['id'],
      title: json['title'],
      notes: json['notes'],
      categoryId: json['category_id'],
      categoryTitle: categories != null ? categories['title'] : null,
      categoryRank: categories != null ? categories['rank'] : null,
      startDate: json['start_date'],
      dueDate: json['due_date'],
      cadenceDays: json['cadence_days'],
      frequencyTarget: json['frequency_target'],
      frequencyWindowDays: json['frequency_window_days'],
      windowStart: json['window_start'],
      windowEnd: json['window_end'],
      externalSource: json['external_source'],
      priorityScore: (json['priority_score'] ?? 0).toDouble(),
      deferCount: json['defer_count'] ?? 0,
      deferredUntil: json['deferred_until'],
      isProject: json['is_project'] ?? false,
    );
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add flutter_app/lib/models/
git commit -m "feat: add Category and Item data models"
```

---

## Task 15: Flutter Services (Auth, API, Location)

**Files:**
- Create: `flutter_app/lib/services/auth_service.dart`, `flutter_app/lib/services/api_service.dart`, `flutter_app/lib/services/location_service.dart`

- [ ] **Step 1: Write `flutter_app/lib/services/location_service.dart`**

```dart
import 'package:geolocator/geolocator.dart';

class LocationService {
  Position? _cachedPosition;

  Future<Position?> getLocation() async {
    if (_cachedPosition != null) return _cachedPosition;

    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) return null;

    LocationPermission permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) return null;
    }
    if (permission == LocationPermission.deniedForever) return null;

    _cachedPosition = await Geolocator.getCurrentPosition(
      desiredAccuracy: LocationAccuracy.low,
    );
    return _cachedPosition;
  }
}
```

- [ ] **Step 2: Write `flutter_app/lib/services/api_service.dart`**

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/item.dart';
import '../models/category.dart';
import 'location_service.dart';

const backendUrl = String.fromEnvironment('BACKEND_URL');

class ApiService {
  final LocationService _locationService = LocationService();

  Future<String> _getToken() async {
    final session = Supabase.instance.client.auth.currentSession;
    if (session == null) throw Exception('Not authenticated');
    return session.accessToken;
  }

  Future<Map<String, String>> _headers() async {
    final token = await _getToken();
    return {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    };
  }

  String _locationParams() {
    final pos = _locationService._cachedPosition;
    if (pos == null) return '';
    // Detect timezone from platform
    final tz = DateTime.now().timeZoneName;
    return '?lat=${pos.latitude}&lng=${pos.longitude}&tz=$tz';
  }

  Future<Map<String, dynamic>> syncAll() async {
    // Ensure location is fetched
    await _locationService.getLocation();
    final headers = await _headers();
    final resp = await http.post(
      Uri.parse('$backendUrl/api/sync/all${_locationParams()}'),
      headers: headers,
    );
    return jsonDecode(resp.body);
  }

  Future<List<Item>> getTop() async {
    final headers = await _headers();
    final resp = await http.get(
      Uri.parse('$backendUrl/api/top'),
      headers: headers,
    );
    final list = jsonDecode(resp.body) as List;
    return list.map((j) => Item.fromJson(j)).toList();
  }

  Future<List<Category>> getCategories() async {
    final headers = await _headers();
    final resp = await http.get(
      Uri.parse('$backendUrl/api/categories'),
      headers: headers,
    );
    final list = jsonDecode(resp.body) as List;
    return list.map((j) => Category.fromJson(j)).toList();
  }

  Future<void> completeItem(String itemId) async {
    final headers = await _headers();
    await http.post(
      Uri.parse('$backendUrl/api/items/$itemId/complete'),
      headers: headers,
    );
  }

  Future<void> deferItem(String itemId) async {
    final headers = await _headers();
    await http.post(
      Uri.parse('$backendUrl/api/items/$itemId/defer'),
      headers: headers,
    );
  }

  Future<void> createItem(Map<String, dynamic> data) async {
    final headers = await _headers();
    await http.post(
      Uri.parse('$backendUrl/api/items'),
      headers: headers,
      body: jsonEncode(data),
    );
  }

  Future<void> updateItem(String itemId, Map<String, dynamic> data) async {
    final headers = await _headers();
    await http.patch(
      Uri.parse('$backendUrl/api/items/$itemId'),
      headers: headers,
      body: jsonEncode(data),
    );
  }

  Future<void> deleteItem(String itemId) async {
    final headers = await _headers();
    await http.delete(
      Uri.parse('$backendUrl/api/items/$itemId'),
      headers: headers,
    );
  }

  Future<void> reorderCategories(List<String> order) async {
    final headers = await _headers();
    await http.put(
      Uri.parse('$backendUrl/api/categories/reorder'),
      headers: headers,
      body: jsonEncode({'order': order}),
    );
  }

  Future<void> createCategory(String title, int rank) async {
    final headers = await _headers();
    await http.post(
      Uri.parse('$backendUrl/api/categories'),
      headers: headers,
      body: jsonEncode({'title': title, 'rank': rank}),
    );
  }

  Future<void> deleteCategory(String categoryId) async {
    final headers = await _headers();
    await http.delete(
      Uri.parse('$backendUrl/api/categories/$categoryId'),
      headers: headers,
    );
  }
}
```

- [ ] **Step 3: Write `flutter_app/lib/services/auth_service.dart`**

```dart
import 'package:supabase_flutter/supabase_flutter.dart';

class AuthService {
  final _supabase = Supabase.instance.client;

  Session? get currentSession => _supabase.auth.currentSession;
  bool get isLoggedIn => currentSession != null;

  Future<void> signIn(String email, String password) async {
    await _supabase.auth.signInWithPassword(email: email, password: password);
  }

  Future<void> signUp(String email, String password) async {
    await _supabase.auth.signUp(email: email, password: password);
  }

  Future<void> signOut() async {
    await _supabase.auth.signOut();
  }
}
```

- [ ] **Step 4: Commit**

```bash
git add flutter_app/lib/services/
git commit -m "feat: add auth, API, and location services"
```

---

## Task 16: Flutter State Management (Riverpod Providers)

**Files:**
- Create: `flutter_app/lib/providers/app_state.dart`

- [ ] **Step 1: Write `flutter_app/lib/providers/app_state.dart`**

```dart
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/api_service.dart';
import '../models/item.dart';
import '../models/category.dart';

final apiServiceProvider = Provider((ref) => ApiService());

final topItemsProvider = FutureProvider<List<Item>>((ref) async {
  final api = ref.read(apiServiceProvider);
  return api.getTop();
});

final categoriesProvider = FutureProvider<List<Category>>((ref) async {
  final api = ref.read(apiServiceProvider);
  return api.getCategories();
});
```

- [ ] **Step 2: Commit**

```bash
git add flutter_app/lib/providers/
git commit -m "feat: add Riverpod providers for top items and categories"
```

---

## Task 17: Flutter Login Screen

**Files:**
- Create: `flutter_app/lib/screens/login_screen.dart`

- [ ] **Step 1: Write `flutter_app/lib/screens/login_screen.dart`**

```dart
import 'package:flutter/material.dart';
import '../services/auth_service.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _authService = AuthService();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _isSignUp = false;
  bool _isLoading = false;
  String? _error;

  Future<void> _submit() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      if (_isSignUp) {
        await _authService.signUp(
          _emailController.text.trim(),
          _passwordController.text,
        );
      } else {
        await _authService.signIn(
          _emailController.text.trim(),
          _passwordController.text,
        );
      }
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const HomeScreen()),
        );
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Effict')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            TextField(
              controller: _emailController,
              decoration: const InputDecoration(labelText: 'Email'),
              keyboardType: TextInputType.emailAddress,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _passwordController,
              decoration: const InputDecoration(labelText: 'Password'),
              obscureText: true,
            ),
            const SizedBox(height: 8),
            if (_error != null)
              Text(_error!, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _isLoading ? null : _submit,
              child: Text(_isSignUp ? 'Sign Up' : 'Sign In'),
            ),
            TextButton(
              onPressed: () => setState(() => _isSignUp = !_isSignUp),
              child: Text(
                _isSignUp
                    ? 'Already have an account? Sign in'
                    : 'Need an account? Sign up',
              ),
            ),
          ],
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add flutter_app/lib/screens/login_screen.dart
git commit -m "feat: add login screen with email/password auth"
```

---

## Task 18: Flutter Home Screen (Tab Shell)

**Files:**
- Create: `flutter_app/lib/screens/home_screen.dart`

- [ ] **Step 1: Write `flutter_app/lib/screens/home_screen.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'perform_tab.dart';
import 'plan_tab.dart';
import 'prioritize_tab.dart';
import '../providers/app_state.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _currentIndex = 0;
  bool _initialSyncDone = false;

  @override
  void initState() {
    super.initState();
    _initialSync();
  }

  Future<void> _initialSync() async {
    final api = ref.read(apiServiceProvider);
    await api.syncAll();
    ref.invalidate(topItemsProvider);
    ref.invalidate(categoriesProvider);
    setState(() => _initialSyncDone = true);
  }

  @override
  Widget build(BuildContext context) {
    final tabs = [
      const PerformTab(),
      const PlanTab(),
      const PrioritizeTab(),
    ];

    return Scaffold(
      body: _initialSyncDone
          ? tabs[_currentIndex]
          : const Center(child: CircularProgressIndicator()),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.play_arrow), label: 'Perform'),
          NavigationDestination(icon: Icon(Icons.list), label: 'Plan'),
          NavigationDestination(icon: Icon(Icons.sort), label: 'Prioritize'),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add flutter_app/lib/screens/home_screen.dart
git commit -m "feat: add home screen with 3-tab navigation and initial sync"
```

---

## Task 19: Flutter Task Card Widget

**Files:**
- Create: `flutter_app/lib/widgets/task_card.dart`

- [ ] **Step 1: Write `flutter_app/lib/widgets/task_card.dart`**

```dart
import 'package:flutter/material.dart';
import '../models/item.dart';

class TaskCard extends StatelessWidget {
  final Item item;
  final VoidCallback onComplete;
  final VoidCallback onDefer;

  const TaskCard({
    super.key,
    required this.item,
    required this.onComplete,
    required this.onDefer,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (item.categoryTitle != null)
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: _categoryColor(item.categoryRank ?? 5),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      item.categoryTitle!,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                      ),
                    ),
                  ),
                const Spacer(),
                if (item.dueDate != null)
                  Text(
                    item.dueDate!,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              item.title,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                IconButton.filled(
                  onPressed: onDefer,
                  icon: const Icon(Icons.access_time),
                  tooltip: 'Defer',
                ),
                const SizedBox(width: 8),
                IconButton.filled(
                  onPressed: onComplete,
                  icon: const Icon(Icons.check),
                  tooltip: 'Complete',
                  style: IconButton.styleFrom(
                    backgroundColor: Colors.green,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Color _categoryColor(int rank) {
    const colors = [
      Colors.indigo,
      Colors.orange,
      Colors.teal,
      Colors.purple,
      Colors.blue,
      Colors.brown,
    ];
    return colors[(rank - 1) % colors.length];
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add flutter_app/lib/widgets/task_card.dart
git commit -m "feat: add TaskCard widget with category badge and action buttons"
```

---

## Task 20: Flutter Perform Tab

**Files:**
- Create: `flutter_app/lib/screens/perform_tab.dart`

- [ ] **Step 1: Write `flutter_app/lib/screens/perform_tab.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/app_state.dart';
import '../widgets/task_card.dart';

class PerformTab extends ConsumerWidget {
  const PerformTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final topItems = ref.watch(topItemsProvider);

    return RefreshIndicator(
      onRefresh: () async {
        final api = ref.read(apiServiceProvider);
        await api.syncAll();
        ref.invalidate(topItemsProvider);
      },
      child: topItems.when(
        data: (items) {
          if (items.isEmpty) {
            return const Center(child: Text('No tasks right now'));
          }
          return ListView.builder(
            padding: const EdgeInsets.only(top: 8, bottom: 16),
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              return TaskCard(
                item: item,
                onComplete: () async {
                  final api = ref.read(apiServiceProvider);
                  await api.completeItem(item.id);
                  ref.invalidate(topItemsProvider);
                  ref.invalidate(categoriesProvider);
                },
                onDefer: () async {
                  final api = ref.read(apiServiceProvider);
                  await api.deferItem(item.id);
                  ref.invalidate(topItemsProvider);
                },
              );
            },
          );
        },
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Error: $e')),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add flutter_app/lib/screens/perform_tab.dart
git commit -m "feat: add Perform tab with top-5 items and pull-to-refresh"
```

---

## Task 21: Flutter Item Form Widget

**Files:**
- Create: `flutter_app/lib/widgets/item_form.dart`

- [ ] **Step 1: Write `flutter_app/lib/widgets/item_form.dart`**

```dart
import 'package:flutter/material.dart';
import '../models/item.dart';
import '../models/category.dart';

class ItemForm extends StatefulWidget {
  final List<Category> categories;
  final Item? existingItem;
  final void Function(Map<String, dynamic> data) onSubmit;

  const ItemForm({
    super.key,
    required this.categories,
    this.existingItem,
    required this.onSubmit,
  });

  @override
  State<ItemForm> createState() => _ItemFormState();
}

class _ItemFormState extends State<ItemForm> {
  late final TextEditingController _titleController;
  late final TextEditingController _notesController;
  late final TextEditingController _cadenceController;
  late final TextEditingController _freqTargetController;
  late final TextEditingController _freqWindowController;
  String? _selectedCategoryId;
  DateTime? _dueDate;
  DateTime? _startDate;
  bool _isProject = false;

  @override
  void initState() {
    super.initState();
    final item = widget.existingItem;
    _titleController = TextEditingController(text: item?.title ?? '');
    _notesController = TextEditingController(text: item?.notes ?? '');
    _cadenceController =
        TextEditingController(text: item?.cadenceDays?.toString() ?? '');
    _freqTargetController =
        TextEditingController(text: item?.frequencyTarget?.toString() ?? '');
    _freqWindowController =
        TextEditingController(text: item?.frequencyWindowDays?.toString() ?? '');
    _selectedCategoryId = item?.categoryId ?? widget.categories.first.id;
    _dueDate = item?.dueDate != null ? DateTime.tryParse(item!.dueDate!) : null;
    _startDate =
        item?.startDate != null ? DateTime.tryParse(item!.startDate!) : null;
    _isProject = item?.isProject ?? false;
  }

  void _submit() {
    final data = <String, dynamic>{
      'title': _titleController.text.trim(),
      'category_id': _selectedCategoryId,
    };
    if (_notesController.text.trim().isNotEmpty) {
      data['notes'] = _notesController.text.trim();
    }
    if (_dueDate != null) {
      data['due_date'] = _dueDate!.toIso8601String().split('T')[0];
    }
    if (_startDate != null) {
      data['start_date'] = _startDate!.toIso8601String().split('T')[0];
    }
    if (_cadenceController.text.isNotEmpty) {
      data['cadence_days'] = int.tryParse(_cadenceController.text);
    }
    if (_freqTargetController.text.isNotEmpty) {
      data['frequency_target'] = int.tryParse(_freqTargetController.text);
    }
    if (_freqWindowController.text.isNotEmpty) {
      data['frequency_window_days'] = int.tryParse(_freqWindowController.text);
    }
    data['is_project'] = _isProject;
    widget.onSubmit(data);
  }

  Future<void> _pickDate(bool isDue) async {
    final date = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2020),
      lastDate: DateTime(2030),
    );
    if (date != null) {
      setState(() {
        if (isDue) {
          _dueDate = date;
        } else {
          _startDate = date;
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            controller: _titleController,
            decoration: const InputDecoration(labelText: 'Title'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _notesController,
            decoration: const InputDecoration(labelText: 'Notes'),
            maxLines: 3,
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _selectedCategoryId,
            decoration: const InputDecoration(labelText: 'Category'),
            items: widget.categories
                .map((c) =>
                    DropdownMenuItem(value: c.id, child: Text(c.title)))
                .toList(),
            onChanged: (v) => setState(() => _selectedCategoryId = v),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _pickDate(false),
                  child: Text(_startDate != null
                      ? 'Start: ${_startDate!.toIso8601String().split('T')[0]}'
                      : 'Start Date'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton(
                  onPressed: () => _pickDate(true),
                  child: Text(_dueDate != null
                      ? 'Due: ${_dueDate!.toIso8601String().split('T')[0]}'
                      : 'Due Date'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _cadenceController,
            decoration: const InputDecoration(labelText: 'Cadence (days)'),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _freqTargetController,
                  decoration:
                      const InputDecoration(labelText: 'Frequency target'),
                  keyboardType: TextInputType.number,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _freqWindowController,
                  decoration:
                      const InputDecoration(labelText: 'Window (days)'),
                  keyboardType: TextInputType.number,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            title: const Text('Is Project'),
            value: _isProject,
            onChanged: (v) => setState(() => _isProject = v),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _submit,
            child: Text(widget.existingItem != null ? 'Update' : 'Create'),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add flutter_app/lib/widgets/item_form.dart
git commit -m "feat: add item create/edit form widget"
```

---

## Task 22: Flutter Plan Tab

**Files:**
- Create: `flutter_app/lib/screens/plan_tab.dart`

- [ ] **Step 1: Write `flutter_app/lib/screens/plan_tab.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/app_state.dart';
import '../models/category.dart';
import '../models/item.dart';
import '../widgets/item_form.dart';

class PlanTab extends ConsumerWidget {
  const PlanTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categoriesAsync = ref.watch(categoriesProvider);

    return categoriesAsync.when(
      data: (categories) {
        return Scaffold(
          body: ListView.builder(
            padding: const EdgeInsets.only(top: 8, bottom: 80),
            itemCount: categories.length,
            itemBuilder: (context, index) {
              final cat = categories[index];
              return ExpansionTile(
                title: Text(cat.title),
                initiallyExpanded: true,
                children: (cat.items ?? []).map((item) {
                  return ListTile(
                    title: Text(item.title),
                    subtitle: item.dueDate != null
                        ? Text('Due: ${item.dueDate}')
                        : null,
                    trailing: item.isProject
                        ? const Icon(Icons.folder, size: 18)
                        : null,
                    onTap: () => _showEditSheet(context, ref, item, categories),
                  );
                }).toList(),
              );
            },
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: () => _showCreateSheet(context, ref, categories),
            child: const Icon(Icons.add),
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
    );
  }

  void _showCreateSheet(
      BuildContext context, WidgetRef ref, List<Category> categories) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
        ),
        child: ItemForm(
          categories: categories,
          onSubmit: (data) async {
            Navigator.pop(ctx);
            final api = ref.read(apiServiceProvider);
            await api.createItem(data);
            ref.invalidate(categoriesProvider);
            ref.invalidate(topItemsProvider);
          },
        ),
      ),
    );
  }

  void _showEditSheet(
      BuildContext context, WidgetRef ref, Item item, List<Category> categories) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(ctx).viewInsets.bottom,
        ),
        child: ItemForm(
          categories: categories,
          existingItem: item,
          onSubmit: (data) async {
            Navigator.pop(ctx);
            final api = ref.read(apiServiceProvider);
            await api.updateItem(item.id, data);
            ref.invalidate(categoriesProvider);
            ref.invalidate(topItemsProvider);
          },
        ),
      ),
    );
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add flutter_app/lib/screens/plan_tab.dart
git commit -m "feat: add Plan tab with expandable categories and item editing"
```

---

## Task 23: Flutter Prioritize Tab

**Files:**
- Create: `flutter_app/lib/screens/prioritize_tab.dart`

- [ ] **Step 1: Write `flutter_app/lib/screens/prioritize_tab.dart`**

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/app_state.dart';
import '../models/category.dart';

class PrioritizeTab extends ConsumerStatefulWidget {
  const PrioritizeTab({super.key});

  @override
  ConsumerState<PrioritizeTab> createState() => _PrioritizeTabState();
}

class _PrioritizeTabState extends ConsumerState<PrioritizeTab> {
  List<Category>? _localCategories;

  @override
  Widget build(BuildContext context) {
    final categoriesAsync = ref.watch(categoriesProvider);

    return categoriesAsync.when(
      data: (categories) {
        _localCategories ??= List.from(categories);
        return Scaffold(
          body: ReorderableListView.builder(
            padding: const EdgeInsets.only(top: 8, bottom: 80),
            itemCount: _localCategories!.length,
            onReorder: _onReorder,
            itemBuilder: (context, index) {
              final cat = _localCategories![index];
              final itemCount = cat.items?.length ?? 0;
              return Dismissible(
                key: ValueKey(cat.id),
                direction: itemCount == 0
                    ? DismissDirection.endToStart
                    : DismissDirection.none,
                background: Container(
                  color: Colors.red,
                  alignment: Alignment.centerRight,
                  padding: const EdgeInsets.only(right: 16),
                  child: const Icon(Icons.delete, color: Colors.white),
                ),
                onDismissed: (_) => _deleteCategory(cat),
                child: ListTile(
                  leading: ReorderableDragStartListener(
                    index: index,
                    child: const Icon(Icons.drag_handle),
                  ),
                  title: Text(cat.title),
                  subtitle: Text('Rank ${cat.rank} — $itemCount items'),
                ),
              );
            },
          ),
          floatingActionButton: FloatingActionButton(
            onPressed: _addCategory,
            child: const Icon(Icons.add),
          ),
        );
      },
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Error: $e')),
    );
  }

  Future<void> _onReorder(int oldIndex, int newIndex) async {
    if (newIndex > oldIndex) newIndex--;
    setState(() {
      final item = _localCategories!.removeAt(oldIndex);
      _localCategories!.insert(newIndex, item);
    });
    final api = ref.read(apiServiceProvider);
    await api.reorderCategories(_localCategories!.map((c) => c.id).toList());
    ref.invalidate(categoriesProvider);
    ref.invalidate(topItemsProvider);
  }

  Future<void> _deleteCategory(Category cat) async {
    final api = ref.read(apiServiceProvider);
    await api.deleteCategory(cat.id);
    setState(() => _localCategories!.remove(cat));
    ref.invalidate(categoriesProvider);
  }

  Future<void> _addCategory() async {
    final controller = TextEditingController();
    final title = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('New Category'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(labelText: 'Category name'),
          autofocus: true,
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Create'),
          ),
        ],
      ),
    );
    if (title != null && title.isNotEmpty) {
      final api = ref.read(apiServiceProvider);
      final newRank = (_localCategories?.length ?? 0) + 1;
      await api.createCategory(title, newRank);
      _localCategories = null; // reset to refetch
      ref.invalidate(categoriesProvider);
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add flutter_app/lib/screens/prioritize_tab.dart
git commit -m "feat: add Prioritize tab with drag-to-reorder and category management"
```

---

## Task 24: Fix Category Model Import & Final Wiring

**Files:**
- Modify: `flutter_app/lib/models/category.dart`

- [ ] **Step 1: Fix `flutter_app/lib/models/category.dart`**

The model needs the import at the top, not the bottom:

```dart
import 'item.dart';

class Category {
  final String id;
  final String title;
  final int rank;
  final List<Item>? items;

  Category({
    required this.id,
    required this.title,
    required this.rank,
    this.items,
  });

  factory Category.fromJson(Map<String, dynamic> json) {
    return Category(
      id: json['id'],
      title: json['title'],
      rank: json['rank'],
      items: json['items'] != null
          ? (json['items'] as List)
              .map((i) => Item.fromJson(i as Map<String, dynamic>))
              .toList()
          : null,
    );
  }
}
```

- [ ] **Step 2: Verify Flutter compiles**

```bash
cd flutter_app
flutter analyze
```

Expected: No errors (warnings are OK).

- [ ] **Step 3: Commit**

```bash
git add flutter_app/
git commit -m "fix: correct category model import and verify compilation"
```

---

## Task 25: Android Configuration & Build Verification

**Files:**
- Modify: `flutter_app/android/app/src/main/AndroidManifest.xml`

- [ ] **Step 1: Add location permissions to AndroidManifest.xml**

Add inside `<manifest>` before `<application>`:

```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<uses-permission android:name="android.permission.INTERNET" />
```

- [ ] **Step 2: Verify debug build succeeds**

```bash
cd flutter_app
flutter build apk --debug --dart-define=SUPABASE_URL=https://placeholder.supabase.co --dart-define=SUPABASE_ANON_KEY=placeholder --dart-define=BACKEND_URL=http://localhost:8080
```

Expected: Build succeeds, APK generated.

- [ ] **Step 3: Commit**

```bash
git add flutter_app/android/
git commit -m "feat: add location and internet permissions for Android"
```

---

## Task 26: End-to-End Integration Test

**Files:**
- Create: `backend/tests/test_routes.py`

- [ ] **Step 1: Write `backend/tests/test_routes.py`**

```python
"""
Integration test — requires a running Supabase instance.
Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET in .env.
Create a test user in Supabase Auth and generate a valid JWT.

These tests hit the real API endpoints with a real database.
Skip if env vars are not set.
"""
import os
import pytest
from fastapi.testclient import TestClient

# Skip entire module if no Supabase config
pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or "placeholder" in os.getenv("SUPABASE_URL", "placeholder"),
    reason="No real Supabase configured",
)


@pytest.fixture
def client():
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Must set TEST_JWT in env — a valid Supabase JWT for a test user."""
    token = os.getenv("TEST_JWT", "")
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_sync_all_requires_auth(client):
    resp = client.post("/api/sync/all")
    assert resp.status_code in (401, 422)


def test_top_requires_auth(client):
    resp = client.get("/api/top")
    assert resp.status_code in (401, 422)


def test_full_flow(client, auth_headers):
    """Smoke test: sync → get top → create item → complete → verify."""
    # Sync (seeds data on first run)
    resp = client.post("/api/sync/all?lat=33.31&lng=-111.84&tz=America/Phoenix", headers=auth_headers)
    assert resp.status_code == 200

    # Get categories (should have seed data)
    resp = client.get("/api/categories", headers=auth_headers)
    assert resp.status_code == 200
    categories = resp.json()
    assert len(categories) >= 6

    # Get top
    resp = client.get("/api/top", headers=auth_headers)
    assert resp.status_code == 200

    # Create item
    cat_id = categories[0]["id"]
    resp = client.post(
        "/api/items",
        headers=auth_headers,
        json={"title": "Test Item", "category_id": cat_id},
    )
    assert resp.status_code == 200
    item_id = resp.json()["id"]

    # Complete item
    resp = client.post(f"/api/items/{item_id}/complete", headers=auth_headers)
    assert resp.status_code == 200
```

- [ ] **Step 2: Run unit tests (scoring + auth — these don't need Supabase)**

```bash
cd backend
python -m pytest tests/test_scoring.py tests/test_auth.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_routes.py
git commit -m "test: add integration test suite for API routes"
```

---

## Task 27: Cloud Run Deployment Setup

**Files:**
- Modify: `backend/Dockerfile`
- Create: `backend/.dockerignore`

- [ ] **Step 1: Write `backend/.dockerignore`**

```
__pycache__
*.pyc
.env
tests/
.git
```

- [ ] **Step 2: Update Dockerfile for proper module resolution**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./backend/

ENV PYTHONPATH=/app

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

- [ ] **Step 3: Document deployment commands**

Create `backend/DEPLOY.md`:

```markdown
# Deploying Effict Backend to Cloud Run

## Prerequisites
- Google Cloud SDK installed (`gcloud`)
- A GCP project with Cloud Run enabled
- Environment variables set in Cloud Run

## Deploy

```bash
cd backend
gcloud run deploy effict-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --memory 256Mi \
  --set-env-vars "SUPABASE_URL=...,SUPABASE_SERVICE_ROLE_KEY=...,SUPABASE_JWT_SECRET=...,STRAVA_CLIENT_ID=...,STRAVA_CLIENT_SECRET=...,STRAVA_REFRESH_TOKEN=...,CANVAS_ICAL_URL=..."
```

## After deployment
- Note the Cloud Run URL
- Use it as BACKEND_URL when building the Flutter app
```

- [ ] **Step 4: Commit**

```bash
git add backend/.dockerignore backend/Dockerfile backend/DEPLOY.md
git commit -m "feat: finalize Cloud Run deployment config"
```

---

## Summary

| Task | What it builds |
|------|---------------|
| 1 | Backend scaffolding (FastAPI + config + Supabase client) |
| 2 | Database migrations (tables + RLS) |
| 3 | JWT auth middleware |
| 4 | Scoring engine (weighted gravity model) |
| 5 | Zmanim integration (prayer times from GPS) |
| 6 | Strava integration (gym workout sync) |
| 7 | Canvas integration (assignment sync with Shabbos filtering) |
| 8 | Seed data (default categories + items) |
| 9 | Category API routes |
| 10 | Item API routes (CRUD + complete + defer) |
| 11 | Top-5 and sync API routes |
| 12 | Dockerfile |
| 13 | Flutter project scaffolding |
| 14 | Flutter data models |
| 15 | Flutter services (auth, API, location) |
| 16 | Flutter Riverpod providers |
| 17 | Login screen |
| 18 | Home screen (tab shell + initial sync) |
| 19 | TaskCard widget |
| 20 | Perform tab |
| 21 | Item form widget |
| 22 | Plan tab |
| 23 | Prioritize tab |
| 24 | Fix model imports + verify compilation |
| 25 | Android permissions + build verification |
| 26 | Integration tests |
| 27 | Cloud Run deployment setup |
