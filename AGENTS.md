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
- **Department enum mismatch** (known bug): model says `DBM = "DBMs"` but the existing migration uses `DBMS`. Fix the model to match the migration if regenerating.
- **Session model** (`UserSession`) needs its own Alembic migration before use.

## Operational notes

- DB schema: Alembic migrations (run on startup via `init_db()` + manual `alembic upgrade head`)
- No CI, no pre-commit, no linter/formatter config yet
- Tests: pytest + httpx available in dev deps, no test suite written yet
- Deploy: Render — build `uv sync --frozen && uv cache prune --ci`, start `uv run python main.py`
- `.env` is gitignored; see `.env.example` for required vars
- `previouse/` folder is the old v1 monolith — preserved for reference, do NOT import from it in new code
- Templates: Jinja2 with role-based subdirectories (`admin/`, `instructor/`), sections stored in `sections/` as fragment HTML
