# dy Solidification and Face Attendance Plan

## Goal

Make `dy` safer and more maintainable before adding face-recognition attendance. The work should preserve the current Telegram bot and mini app flows, replace fragile database setup with migrations, prepare the project for Turso/libSQL, and introduce face embeddings as one additional table.

## Role Model Update

The admin credentials added through environment variables must create a **super admin** account.

Super admin is above normal admins and should have privileges that regular admins do not have, including:

- creating, updating, disabling, and deleting admin accounts
- managing critical system settings
- running database backup/sync/migration-related actions
- managing registration codes for privileged roles
- viewing operational/security-level logs or audits if those are added later

Normal admins should keep day-to-day management powers, but they should not be able to remove or downgrade the super admin.

Implementation options:

- add `super_admin` to the existing `Role` enum
- or add a separate boolean column such as `is_super_admin`

Preferred approach: add `super_admin` to `Role`, because the current authorization model already uses role enums.

## Phase 1: Project Hardening

### 1. Authentication

Current issue: web APIs can accept `telegram_id` from the query string as an authentication fallback.

Plan:

- keep query-string auth only for local development, controlled by an env flag
- require signed Telegram Mini App `initData` for production API calls
- centralize helpers like `require_user`, `require_admin`, `require_super_admin`, and `require_staff`
- return real HTTP status codes for unauthorized requests instead of `{"ok": false}`

### 2. Startup and Logging

Plan:

- fail startup if the database or bot cannot initialize
- remove raw Telegram update logging from production
- replace `print()` with structured logging
- avoid broad swallowed exceptions except where failure is genuinely non-critical

### 3. Tests

Add focused tests before large behavior changes:

- Telegram init-data verification
- admin/super-admin authorization
- attendance entry/exit logic
- registration/linking flow
- face enrollment service once added

## Phase 2: Migrations

Current issue: schema changes happen through `Base.metadata.create_all()` and manual `ALTER TABLE` statements during app startup.

Plan:

- initialize Alembic migrations
- create a baseline migration for the current schema
- remove runtime `ALTER TABLE` migrations from `db/database.py`
- make every future schema change a migration
- add a documented command for applying migrations locally and in deployment

Target commands:

```bash
uv run alembic revision --autogenerate -m "baseline"
uv run alembic upgrade head
```

## Phase 3: Turso/libSQL Database Move

The move to Turso should happen after migrations are clean.

Plan:

- evaluate the best Python client path for this project:
  - keep SQLAlchemy where practical
  - isolate Turso/libSQL-specific vector queries in a repository/service module
- update `DATABASE_URL` handling for local SQLite and remote Turso
- document required Turso env vars
- verify the current app behavior against local SQLite first, then Turso

Important constraint: do not scatter raw Turso vector SQL across route handlers.

## Phase 4: Face Embeddings Table

Only one new table is needed for v1.

Proposed model:

```sql
CREATE TABLE face_embeddings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL UNIQUE,
  embedding F32_BLOB(512) NOT NULL,
  model_name TEXT NOT NULL DEFAULT 'insightface-arcface',
  embedding_version INTEGER NOT NULL DEFAULT 1,
  quality_score REAL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

If Turso vector indexing is available in the selected deployment mode, add the matching vector index in the migration.

Rules:

- store embeddings only
- do not store raw face images in the database
- one row per user
- re-enrollment replaces the existing embedding
- embeddings must never be returned by public API responses

## Phase 5: Face Enrollment

Build enrollment before recognition.

Flow:

1. Admin, instructor, or super admin opens a user profile.
2. They upload or capture 1-5 face images.
3. Backend validates each image.
4. InsightFace SCRFD detects faces.
5. Reject images with zero faces or multiple faces.
6. ArcFace extracts 512-dim embeddings.
7. Backend averages valid embeddings.
8. Store the averaged embedding in `face_embeddings`.
9. UI shows the user as face-enrolled.

Recommended initial dependencies:

```bash
uv add insightface onnxruntime opencv-python-headless numpy
```

Add `supervision` later only if/when live multi-face tracking is implemented.

## Phase 6: Face Recognition Attendance v1

Start with single-person verification, not room-wide recognition.

Flow:

1. Intern opens the scanner/pass page.
2. Browser captures one face image.
3. Backend extracts an embedding.
4. Backend searches nearest stored face embedding.
5. Match must pass the configured threshold.
6. If the scanner is user-bound, matched face must equal the current Telegram user.
7. Mark entry or exit using the existing attendance logic.

Recommended env vars:

```env
RECOGNITION_THRESHOLD=0.4
FACE_MODEL_NAME=insightface-arcface
ALLOW_DEV_TELEGRAM_ID_AUTH=false
SUPER_ADMIN_TELEGRAM_ID=
SUPER_ADMIN_NAME=
SUPER_ADMIN_SURNAME=
SUPER_ADMIN_PHONE=
SUPER_ADMIN_DEPARTMENT=
```

## Phase 7: Live Multi-Face Attendance v2

Add this only after v1 is stable.

Flow:

- instructor starts a live attendance session
- browser sends frames through WebSocket
- backend detects faces
- ByteTrack or `supervision` tracks repeated faces
- only new tracks trigger recognition
- recognized users are marked present once
- UI shows detected users and confidence status

This phase is higher risk and should not block the safer single-person attendance flow.

## Phase 8: Privacy and Admin Controls

Add controls for biometric data:

- enroll face
- re-enroll face
- delete face embedding
- show enrollment status
- audit who enrolled or deleted an embedding
- require admin or higher for enrollment
- require super admin for bulk deletion or system-level biometric actions

## Suggested Implementation Order

1. Add `super_admin` role and env-based super-admin seed.
2. Harden web authentication.
3. Add role helper dependencies.
4. Add tests around auth and permissions.
5. Set up Alembic and baseline migration.
6. Remove runtime schema mutation.
7. Add Turso/libSQL compatibility layer.
8. Add `face_embeddings` migration and model.
9. Add face extraction/enrollment service.
10. Add enrollment API and UI.
11. Add single-person face attendance API.
12. Add live multi-face recognition as v2.

