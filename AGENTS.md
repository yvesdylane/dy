# dy — AGENTS.md

## Quick start

```bash
uv sync
uv run python main.py          # dev server on :8000
uv run alembic upgrade head     # apply migrations
uv run alembic revision --autogenerate -m "desc"  # new migration
uv run pytest                   # run tests
```

## Architecture

- **FastAPI** + **sync SQLAlchemy** (`libsql_experimental` for Turso, sessions wrapped via `asyncio.to_thread()`)
- Package manager: `uv` (not pip, not poetry)
- Python >=3.12,<3.14
- Entrypoint: `main.py` → `app:app` (uvicorn). App factory in `app.py`
- Config: `config.py` uses `pydantic-settings`, reads from `.env`
- DB session: `db/database.py` — `get_db()` async generator, `init_db()` for startup
- Telegram bot: `python-telegram-bot` via webhook (not polling), wired in `app.py` lifespan

## Project layout

```
dy/
  app.py              # FastAPI app, lifespan, router includes
  main.py             # uvicorn runner only
  config.py           # pydantic-settings, typed env vars
  auth/               # telegram auth + session + deps
  bot/                # telegram bot handlers
  controllers/         # business logic (routes call these)
  db/                 # database.py (engine, session, base)
  models/             # SQLAlchemy models + pydantic schemas
  routes/             # ALL route modules (web, auth, admin, API)
    web.py            # GET /, /register, /instructor
    auth.py           # POST /auth/telegram, /api/register
    adminRoutes.py    # GET /admin (shell), /admin/page/{name} (fragments)
    api/
      stats.py        # GET /api/admin/stats
      users.py        # CRUD /api/admin/users
  web/
    templates/
      admin/
        index.html    # Shell only (sidebar, nav, #content div, modal)
        sections/     # Fragment HTML — one per page
          dashboard.html  users.html  codes.html  registers.html
          leaves.html  pass.html  tasks.html  cleaning.html
          notes.html  info.html  complaints.html
      instructor/
        index.html
        sections/
      index.html
      registraion.html
    static/
      js/
        admin/
          app.js          # Navigation (loadPage), modal, dark mode
          dashboard.js    # Fetch /api/admin/stats, render cards
          users.js        # User CRUD, search, pagination, modals
          codes.js        # (stub)
          registers.js    # (stub)
          leaves.js       # (stub)
          pass.js         # (stub)
          tasks.js        # Task CRUD, filters, list, create/edit/delete modals
          cleaning.js     # (stub)
          notes.js        # Note CRUD, filters, list, create/edit/view/delete modals
          info.js         # (stub)
          complaints.js   # (stub)
      app.js            # Telegram Mini App auth handler
  previouse/          # old v1 code — reference only, do NOT import from here
migrations/           # Alembic (sync for Turso, async for local), two migrations exist
```

## Page-loading architecture

- **Shell + fragments**: Each dashboard (admin, instructor) has a shell template (`index.html`) that contains only navigation (sidebar, bottom nav, modal, theme toggle) and an empty `<div id="content">`.
- **Loading pages**: `app.js` exposes `loadPage(name)` which fetches `GET /admin/page/{name}` (returns only the fragment HTML) → inserts into `#content` → loads the corresponding JS from `/static/js/admin/{name}.js`.
- **Per-page JS**: Each section has its own JS file. When the page is loaded, the old `<script id="page-script">` is removed and the new one is appended, so only one page's JS runs at a time.
- **Nav buttons (desktop sidebar + mobile bottom nav)**: Use `data-page="name"` — click delegation in `app.js` calls `loadPage(name)`. Notes is NOT in the nav — it's a sub-tab under Tasks.
- **Header tab pills (mobile only)**: Some nav items show sub-tabs as pill buttons in the mobile header (beside the theme toggle). Patterns:
  - `#headerPills` for People: `data-people-tab="users|codes"` — Users/Codes switch.
  - `#headerAttPills` for Attendance: `data-att-tab="registers|leaves|pass"` — Registers/Leaves/Pass switch.
  - `#headerTasksPills` for Tasks: `data-tasks-tab="tasks|notes"` — Tasks/Notes switch.
  - Each pill button calls `loadPage()` with the fragment name. `app.js` function `updateTitle(name)` shows the correct pill group and sets the active pill.
- **Routes in `routes/adminRoutes.py`**: `GET /admin` returns the shell, `GET /admin/page/{name}` returns the fragment. Both require authentication via `get_current_user`. Both `tasks` and `notes` are in the `PAGES` dict.

## Important conventions

- **DB access** — uses **sync SQLAlchemy** with sessions via `asyncio.to_thread()`. `libsql_experimental` sync driver is used for Turso (the async `aiolibsql` dialect is broken). `get_db()` dependency yields sync `Session` objects wrapped in executor threads. Use `get_sync_db()` for non-async contexts.
- **Auth flow** — `POST /auth/telegram` verifies Telegram init data → creates server-side session in `user_sessions` DB table → sets `session_id` cookie (HttpOnly, Secure, SameSite=Lax). Every subsequent request reads session from cookie via `auth/deps.py:get_current_user`. No JWT, no re-verification of init data.
- **Role hierarchy**: `intern` < `instructor` < `admin` < `super_admin`. Dependencies in `auth/deps.py` enforce this.
- **Known bugs**:
  - Department enum mismatch: model says `DBM = "DBMs"` but existing migration uses `DBMS`. Fix model to match migration if regenerating.
  - `UserSession` model needs its own Alembic migration before use.
- **`get_db()` cleanup timing**: FastAPI `yield`-based dependency cleanup (code after `yield`) runs **after** the response is already sent. This means `session.commit()` in `get_db()` happens post-response. If commit fails, the client already got a 200 OK but data is rolled back. **Fix**: For write operations that must persist before response, use `run_in_session()` from `db/database.py` instead — it creates a fresh session, runs the function, and commits **within the same thread** before returning. See `routes/api/attendance.py:save_attendance_endpoint` for example.

## Attendance codes system (`controllers/passController.py`)

- An in-memory pool of 16 codes, each with a 60-second TTL, stored as `{code_str: (expires_at, mode)}` protected by a `threading.Lock`.
- `start_pass(mode)` — clears the pool, generates 16 fresh codes in the given mode (`"entry"` or `"exit"`). Called from the admin Pass page.
- `get_active_codes()` — returns all non-expired codes, auto-replenishes to 16 if some expired.
- `use_code(code_str)` — validates and consumes a single code. Returns `(valid: bool, mode: str | None)`. Deletes the code from the pool after use (single-use).
- `stop_pass()` — empties the pool.
- Codes are 5 chars from `[ACDEFGHJKLMNPQRSTUVWXYZ23456789]` (no B, I, O, 0, 1 to avoid confusion).
- **Important**: The pool is **in-process memory** — if the server restarts, all codes are lost. Codes are single-use, not stored in DB.

## Bot attendance handling (`bot/commands/attendance.py`)

- `handle_attendance_code` — triggered by `/XXXXX` messages (5-char code regex `^/[A-Z0-9]{5}$`).
- Flow: validates code via `use_code()` → checks group match → checks fees → finds/creates `Attendance` for today → finds/creates `InternAttendance` entry → sets `enter_at` or `left_at` based on code mode.
- **Entry/exit modes**: If `mode == "entry"`, sets `enter_at`. If `mode == "exit"`, sets `left_at`. Exit is allowed even without entry (no dependency check between the two).
- No attendance on Sundays.
- Fee check: if `fees_paid < 20000`, shows warning; if past `fee_block_start_date`, blocks attendance entirely.

## Admin attendance save fix

- **Bug**: POST `/api/admin/attendance/save` returned 200 OK but entry/exit times didn't persist. Root cause: route used `get_db()` dependency which commits **after** response is sent. Any commit failure resulted in silent rollback with 200 OK already delivered.
- **Fix**: Route now uses `run_in_session(save_attendance, att_id, entries)` which creates a fresh session, runs `save_attendance` (with `db.flush()`), commits, and closes — all in a single thread, **before** the 200 response is sent.
- `save_attendance` in `controllers/attendanceController.py` receives `entries: list[dict]` where each dict has `user_id`, `enter_at` (time string `"HH:MM"` or null), `left_at` (same). Combines time strings with attendance date via `datetime.combine()`.

## Face recognition

- Face-recognition-based attendance was in v1 (`previouse/`) but is **disabled** in v2.
- Bot now uses QR/code-based attendance only.
- Face recognition is CPU-heavy and incompatible with Render's 512MB free tier. Re-enable only if deploying to a beefier server.

## Sync system (`bot/commands/sync.py`)

- `/sync_attendance` command — admin-only manual sync from WhatsApp backup.
- Uses `sync_user_attendance_data()` in `db/sync.py` to merge: users (by telegram_id or phone), attendance records, leave requests, and task submissions.
- **User retention logic**: When a matching phone is found in backup but the existing user has a fake/placeholder telegram_id (`pending_*`), the existing user's telegram_id is updated with the backup's valid telegram_id instead of dropping the user.
- Errors and skips are collected in `user_messages` list and appended to the final report + printed to console.

## Leave request staff notification

- After an intern submits a leave request (via bot), `bot/commands/leave.py` notifies all staff (admin, super_admin, instructor roles) who have a valid `telegram_id`.
- Notification includes intern name, department, date, reason, and a **View & Review** inline button.
- The button sends the admin back to the web app (`/admin/page/leaves`) to review and approve/reject.

## Registration flow

- `/register` page reads `telegram_id` from URL query param (set by `web/static/js/app.js`).
- Form collects: name, surname, phone, gender, department, school, DOB, quarter, fees.
- `POST /api/register` creates user with `telegram_id`, role=`intern`, and sets `fees_paid`.
- Quarter field is `type="text"` (not number) to avoid browser number-stepper issues.

## Operational notes

- DB schema: Alembic migrations (run on startup via `init_db()` + manual `alembic upgrade head`)
- `enter_at` column on `intern_attendances` was originally `NOT NULL`; made nullable via migration `781d654a6975` since not all interns are exempted from entry time.
- No CI, no pre-commit, no linter/formatter config yet
- Tests: pytest + httpx available in dev deps, no test suite written yet
- Deploy: Render — build `uv sync --frozen && uv cache prune --ci`, start `uv run python main.py`
- `.env` is gitignored; see `.env.example` for required vars
- `previouse/` folder is the old v1 monolith — preserved for reference, do NOT import from it in new code
- Templates: Jinja2 with role-based subdirectories (`admin/`, `instructor/`), sections stored in `sections/` as fragment HTML
