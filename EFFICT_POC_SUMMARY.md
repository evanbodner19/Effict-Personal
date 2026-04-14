# Effict — Project Summary

## What It Is

A **priority scoring engine** that surfaces "the right task at the right time" from a ranked list of life domains. It computes a numeric priority score for every active task and shows you the top 5 most urgent/important items right now.

## Core Concept: The Scoring Formula

```
score = category_weight(rank) × (base + urgency + staleness + freq_deficit + avoidance)
```

**Five scoring components:**

| Component | What it does |
|---|---|
| **category_weight** | `1 / log2(0.75*rank + 1.25)` — rank 1 (Baseline) = 1.0, rank 6 = 0.34. Higher-ranked life domains always win ties. |
| **urgency** | Driven by `due_date`. Normal: `1/(days+1)`. Overdue: `3 + days_overdue × 0.5`. Escalates sharply past deadline. |
| **staleness** | Driven by `cadence_days`. Baseline items use exponential: `2^(days/cadence) - 1`. Others use linear: `(days_since - cadence) / cadence`. |
| **freq_deficit** | Driven by `frequency_target` / `frequency_window_days`. `(target - count) / target`. Drops to 0 when target met. |
| **avoidance** | `log(defer_count + 1)`. Grows each time user clicks "Later" — makes deferred items harder to ignore. |
| **base** | Flat 0.75 floor so items without due dates/cadence still appear. |

**Gating rules (score = 0 when):**

- Before `start_date`
- During deferral period (`deferred_until`)
- Outside `window_start`/`window_end` time-of-day range
- `frequency_target` already met in the rolling window

## Data Model (3 tables)

### Category — life domains with a rank (priority order)

- `id`, `title`, `rank`
- Default 6: Baseline (1), School (2), Physical Health (3), Dad's Business (4), Todo List (5), Career (6)
- User can reorder, create, and delete categories

### Item — a task/action

- Core: `title`, `notes`, `category_id`
- Scheduling: `start_date`, `due_date`, `cadence_days`
- Frequency: `frequency_target`, `frequency_window_days`
- Time windows: `window_start`, `window_end` (time-of-day, for prayer items)
- External: `external_source` ("strava" or "canvas"), `external_data` (JSON blob)
- Scoring output: `priority_score`, `defer_count`, `deferred_until`
- Timestamps: `created_at`, `completed_at`, `last_touched_at`, `score_updated_at`
- Flag: `is_project` (display-only)

### Completion — log entry for each time a recurring item is completed

- `id`, `item_id`, `completed_at`
- Only for recurring items; one-time items just set `Item.completed_at`

## Completion Logic

- **One-time item:** sets `completed_at` → disappears permanently
- **Recurring item** (has `cadence_days` or `frequency_target`): sets `last_touched_at`, inserts a `Completion` row → stays active, score resets

## Defer Logic

- Increments `defer_count`, sets `deferred_until = now + (2 + 2^defer_count)` hours
- Escalating: 4h → 6h → 10h → 18h → 34h
- When deferral expires, item reappears with higher avoidance score

## Special Rules

- **School buffer:** School items' effective due date is shifted back 3 days (`SCHOOL_BUFFER_DAYS`) so they surface before the actual deadline
- **Baseline exponential staleness:** Prayer/daily items use `2^(days/cadence) - 1` instead of linear staleness — skipping even one day escalates fast
- **Overnight time windows:** Maariv (evening prayer) has `window_start > window_end`, interpreted as crossing midnight

## Integrations

### Zmanim (Prayer Times)

- Uses the `zmanim` library with hardcoded location (Chandler, AZ — lat 33.31, lng -111.84, elevation 370m, America/Phoenix timezone)
- Computes sunrise, chatzos (solar noon), sunset, tzais (nightfall), and alos (dawn) daily
- Writes these onto prayer items' `window_start`/`window_end` columns
- Refreshed every 15 minutes

### Strava (Gym Tracking)

- OAuth2 flow with `client_id`, `client_secret`, `refresh_token` from `.env`
- Fetches last 30 days of activities, filters to gym types: `WeightTraining`, `Workout`, `Crossfit`, `RockClimbing`
- Stores filtered workout list as JSON in `Item.external_data` on the item with `external_source="strava"`
- Scoring counts workouts in last 7 days from this JSON instead of from the Completion table

### Canvas LMS (School Assignments)

- Fetches an unauthenticated iCal feed URL from `.env` (`CANVAS_ICAL_URL`)
- Parses VEVENT components, filters to UIDs containing "assignment"
- Upserts into School category with `external_source="canvas"`
- Only imports assignments due within 3 "actionable days" (skips Shabbos/Saturday and Yom Tov via `pyluach`)
- Never resurrects user-completed items

## API Routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/top` | Top 5 active items by score (score > 0) |
| GET | `/api/categories` | All categories with their active items |
| POST | `/api/items` | Create item |
| PATCH | `/api/items/{id}` | Update item fields |
| DELETE | `/api/items/{id}` | Soft-delete (sets `completed_at`) |
| POST | `/api/items/{id}/complete` | Complete (one-time or recurring) |
| POST | `/api/items/{id}/defer` | Defer with escalating duration |
| POST | `/api/recalculate` | Force full rescore |
| PUT | `/api/categories/reorder` | Reorder category ranks |
| POST | `/api/categories` | Create new category |
| DELETE | `/api/categories/{id}` | Delete category (must be empty) |
| POST | `/api/sync/canvas` | Manual Canvas sync + rescore |
| POST | `/api/sync/strava` | Manual Strava sync + rescore |

## Auth

- Optional bearer token via `API_TOKEN` env var
- If set, all `/api/*` routes require `Authorization: Bearer <token>`
- If unset, no auth (local dev mode)
- Static files (`/`, `/static/*`) always pass through

## Background Processing

- APScheduler runs every 15 minutes: updates prayer windows → syncs Canvas → syncs Strava → rescores all items
- Scoring also triggers immediately after any create/update/complete/defer/reorder action

## UI

- Single-page vanilla JS app (`static/index.html`)
- Three tabs: **Perform** (top 5 items with Complete/Defer buttons), **Plan** (items by category), **Prioritize** (drag-to-reorder categories, create/delete categories)
- PWA-enabled with `manifest.json` and service worker
- Auth token prompted once and stored in `localStorage`

## Tech Stack (POC)

- Python/FastAPI, SQLAlchemy ORM, SQLite (local) or PostgreSQL (Railway)
- No build tools, no frontend framework
- Dependencies: `fastapi`, `uvicorn`, `sqlalchemy`, `apscheduler`, `httpx`, `python-dotenv`, `zmanim`, `icalendar`, `pyluach`, `psycopg2-binary`

## Seed Data

5 default items: Shacharit, Mincha, Maariv (prayer with time windows + frequency), Hisbodedus (cadence-based), Gym (Strava-linked frequency)
