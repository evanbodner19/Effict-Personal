# Effict Personal — Production Design Spec

## Overview

Effict is a personal task prioritization system that uses a Weighted Gravity Model to score tasks and surface the top 5 most urgent/important items. This spec covers the move from a local POC (Python/FastAPI/SQLite/vanilla JS) to a production system (Flutter/Supabase/Cloud Run).

## Architecture

```
Flutter App (Mobile)  ──JWT──>  Python/FastAPI (Cloud Run)  ──SQL──>  Supabase (PostgreSQL)
                      <─JSON──                              <───────
```

- **Flutter** — Mobile-first app, authenticates via Supabase Auth, sends device GPS with requests
- **Python/FastAPI on Google Cloud Run** — Stateless. Owns scoring logic and integrations (Strava, Canvas, Zmanim). Validates Supabase JWTs. Scales to zero.
- **Supabase** — PostgreSQL database, Auth provider, Row Level Security
- **No background jobs** — All sync and rescoring happens on-demand (app open + pull-to-refresh)

## Database (Supabase PostgreSQL)

Three tables, all with `user_id uuid references auth.users(id)`:

### categories

| Column   | Type    | Constraints                          |
|----------|---------|--------------------------------------|
| id       | uuid    | PK, default `gen_random_uuid()`      |
| user_id  | uuid    | FK → auth.users, not null            |
| title    | text    | not null                             |
| rank     | integer | not null                             |

Unique constraint on `(user_id, rank)`.

Default 6 categories: Baseline (1), School (2), Physical Health (3), Dad's Business (4), Todo List (5), Career (6).

### items

| Column                 | Type        | Notes                                      |
|------------------------|-------------|---------------------------------------------|
| id                     | uuid        | PK, default `gen_random_uuid()`             |
| user_id                | uuid        | FK → auth.users, not null                   |
| title                  | text        | not null                                    |
| notes                  | text        |                                             |
| category_id            | uuid        | FK → categories                             |
| start_date             | date        |                                             |
| due_date               | date        |                                             |
| cadence_days           | integer     |                                             |
| frequency_target       | integer     |                                             |
| frequency_window_days  | integer     |                                             |
| window_start           | time        | time-of-day range for gating                |
| window_end             | time        | supports overnight (start > end)            |
| external_source        | text        | "strava" or "canvas"                        |
| external_data          | jsonb       | integration-specific payload                |
| priority_score         | float       |                                             |
| defer_count            | integer     | default 0                                   |
| deferred_until         | timestamptz |                                             |
| created_at             | timestamptz | default now()                               |
| completed_at           | timestamptz | set when one-time item is completed         |
| last_touched_at        | timestamptz | set when recurring item is completed        |
| score_updated_at       | timestamptz |                                             |
| is_project             | boolean     | display-only flag                           |

### completions

| Column       | Type        | Notes                           |
|--------------|-------------|---------------------------------|
| id           | uuid        | PK, default `gen_random_uuid()` |
| user_id      | uuid        | FK → auth.users, for RLS        |
| item_id      | uuid        | FK → items                      |
| completed_at | timestamptz | default now()                   |

### Row Level Security

All tables: `user_id = auth.uid()` policy on SELECT, INSERT, UPDATE, DELETE. The Python backend uses the Supabase service role key to bypass RLS.

### Seed Data

On first login, the backend creates the 6 default categories and 5 seed items (Shacharit, Mincha, Maariv, Hisbodedus, Gym) for that user.

## Python Backend (FastAPI on Cloud Run)

### Project Structure

```
backend/
  main.py              # FastAPI app, startup, middleware
  auth.py              # Supabase JWT validation
  scoring.py           # Weighted gravity model (unchanged logic)
  integrations/
    zmanim.py          # Compute prayer windows from lat/lng/date
    strava.py          # OAuth2 + fetch workouts
    canvas.py          # ICS feed parsing
  routes/
    items.py           # CRUD, complete, defer
    categories.py      # CRUD, reorder
    sync.py            # Sync + rescore endpoints
    top.py             # GET /api/top
  db.py                # Supabase client (using supabase-py)
  Dockerfile
  requirements.txt
```

### Key Changes from POC

- **SQLAlchemy → supabase-py**: Use the Supabase Python client instead of ORM. Service role key bypasses RLS for server-side operations.
- **Auth middleware**: Extracts JWT from `Authorization: Bearer` header, validates against Supabase JWT secret, extracts `user_id`. All routes require valid JWT.
- **Zmanim accepts lat/lng/timezone**: Flutter sends device GPS with requests. Prayer windows are computed on-the-fly at score time — no hardcoded location. The `window_start`/`window_end` columns on items are still used for non-prayer items (user-defined time windows), but for prayer items (Shacharit, Mincha, Maariv) these values are computed from Zmanim and injected at score time without being persisted.
- **No APScheduler**: Scoring and sync happen only when called.
- **Combined sync endpoint**: `POST /api/sync/all` runs Zmanim compute → Canvas sync → Strava sync → rescore in one call. Flutter calls this on app open and pull-to-refresh.

### Scoring Logic

Unchanged from POC:

```
score = category_weight(rank) * (base + urgency + staleness + freq_deficit + avoidance)
```

- `category_weight`: `1 / log2(0.75*rank + 1.25)`
- `urgency`: from `due_date` — normal: `1/(days+1)`, overdue: `3 + days_overdue * 0.5`
- `staleness`: baseline items use `2^(days/cadence) - 1`, others use `(days_since - cadence) / cadence`
- `freq_deficit`: `(target - count) / target`, drops to 0 when met
- `avoidance`: `log(defer_count + 1)`
- `base`: flat 0.75 floor

Gating rules (score = 0): before `start_date`, during deferral, outside time window, frequency target met.

Special rules: school buffer (3 days), baseline exponential staleness, overnight time windows.

### API Routes

| Method | Path                     | Purpose                             |
|--------|--------------------------|-------------------------------------|
| GET    | /api/top                 | Top 5 active items by score         |
| GET    | /api/categories          | All categories with active items    |
| POST   | /api/items               | Create item                         |
| PATCH  | /api/items/{id}          | Update item                         |
| DELETE | /api/items/{id}          | Soft-delete (sets completed_at)     |
| POST   | /api/items/{id}/complete | Complete (one-time or recurring)    |
| POST   | /api/items/{id}/defer    | Defer with escalating duration      |
| POST   | /api/recalculate         | Force full rescore                  |
| PUT    | /api/categories/reorder  | Reorder category ranks              |
| POST   | /api/categories          | Create new category                 |
| DELETE | /api/categories/{id}     | Delete category (must be empty)     |
| POST   | /api/sync/canvas         | Manual Canvas sync + rescore        |
| POST   | /api/sync/strava         | Manual Strava sync + rescore        |
| POST   | /api/sync/all            | Combined sync + rescore (new)       |

All routes require Supabase JWT. All queries scoped by `user_id` from JWT.

### Completion Logic

- **One-time item**: sets `completed_at` → disappears permanently
- **Recurring item** (has `cadence_days` or `frequency_target`): sets `last_touched_at`, inserts a completion row → stays active, score resets

### Defer Logic

- Increments `defer_count`, sets `deferred_until = now + (2 + 2^defer_count)` hours
- Escalating: 4h → 6h → 10h → 18h → 34h
- On expiry, item reappears with higher avoidance score

## Flutter App

### Auth Flow

1. App launches → check for cached Supabase session
2. If no session → login screen (email/password with sign-up option)
3. On successful auth → request location permission → navigate to home
4. Supabase Flutter SDK handles session persistence and token refresh

### Navigation

`BottomNavigationBar` with 3 tabs: **Perform**, **Plan**, **Prioritize**. Standard Material Design.

### Perform Tab (Home)

- Top 5 scored items as cards
- Each card: title, category badge (colored), due date if applicable
- Two action buttons per card: Complete (checkmark), Defer (clock)
- Pull-to-refresh triggers `POST /api/sync/all`
- Auto-syncs on app open

### Plan Tab

- Items grouped by category, ordered by category rank
- Expandable category sections showing active items
- Tap item to edit (title, notes, category, due date, start date, cadence, frequency, time window, is_project)
- FAB to create new item

### Prioritize Tab

- Categories listed by rank
- Drag-to-reorder (ReorderableListView)
- Swipe to delete (only if empty)
- Button to add new category

### State Management

- `provider` or `riverpod` for state management
- Single `ApiService` class wrapping all HTTP calls, attaching Supabase JWT
- Device location fetched once on app start, cached in memory, sent with sync requests

### Offline Behavior

None for v1. App requires network. Shows error state if offline.

## Deployment & Configuration

### Cloud Run

- Deploy from Dockerfile via `gcloud run deploy`
- Min instances: 0 (scales to zero), max instances: 1
- Memory: 256MB, concurrency: 1
- Environment variables:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_JWT_SECRET`
  - `STRAVA_CLIENT_ID`
  - `STRAVA_CLIENT_SECRET`
  - `STRAVA_REFRESH_TOKEN`
  - `CANVAS_ICAL_URL`

### Supabase

- Create project via dashboard
- SQL migration for tables, RLS policies, indexes
- Enable email/password auth
- Keys needed: project URL, anon key (Flutter), service role key (backend), JWT secret

### Flutter

- Supabase project URL and anon key embedded in app (safe — RLS protects data)
- Backend Cloud Run URL in build config
- Build for Android first, iOS later

### Strava

- Same OAuth credentials as POC, stored in Cloud Run env vars
- Re-authorization done manually if needed (no in-app OAuth for v1)

### Canvas

- Same unauthenticated ICS URL in Cloud Run env vars
