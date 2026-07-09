# FaceAttend — AI Attendance System
## Project Technical Blueprint

---

## 1. Project Goal

Build a web-based facial recognition attendance system where:
- A **lecturer** opens a video feed in a browser, the system detects all student faces in the room and marks them present automatically
- **Students** register themselves by uploading multiple photos from different angles (minimum 1, recommended 3–5)
- An **admin** can manage students, view attendance records, and export reports
- Recognition works even when students are **not facing the camera directly**

---

## 2. Stack Decisions & Rationale

| Layer | Tool | Why |
|---|---|---|
| Face detection | InsightFace SCRFD | Multi-face, angle-robust, ships with InsightFace |
| Face recognition | InsightFace ArcFace (ONNX) | State-of-the-art accuracy, ONNX = fast CPU inference |
| Face tracking | ByteTrack | Avoids re-running recognition every frame; huge perf win |
| Embeddings | numpy (averaged per student) | Average of all enrollment photos = robust representation |
| Vector search | PostgreSQL + pgvector | Cosine similarity in SQL; no separate service needed |
| Photo storage | Cloudinary | Profile photos only (display); NOT used for embeddings |
| Backend | FastAPI | Async, fast, auto-docs, background task support |
| Database | PostgreSQL (hosted) | pgvector support; production-ready; Neon/Supabase/Railway |
| Frontend | HTML + JS (or React) | Served by FastAPI; no separate frontend server needed |
| Video processing | OpenCV + numpy | Frame extraction, preprocessing |
| Data export | pandas | CSV / Excel attendance reports |
| Inference speed | ONNX Runtime | 2–5x faster than default PyTorch on CPU |
| Package manager | uv | Fast, modern Python package management |

---

## 3. What Is NOT Stored

- Raw student photos are **not** stored in the database
- Only **face embeddings** (512-dim float vectors) live in PostgreSQL
- One averaged embedding per student, generated from all enrollment photos
- Cloudinary stores only the display/profile photo (optional, for UI)

---

## 4. Database Schema (Target)

```
students
  id, name, student_id, course_ids[], profile_photo_url, created_at

face_embeddings
  id, student_id (FK), embedding (vector(512)), created_at

courses
  id, name, code, lecturer_id

sessions
  id, course_id (FK), date, started_at, ended_at

attendance
  id, session_id (FK), student_id (FK), confidence_score, marked_at
```

The `embedding` column uses `pgvector`. Matching query:
```sql
SELECT student_id, embedding <-> $1 AS distance
FROM face_embeddings
ORDER BY distance LIMIT 1;
```
Threshold: distance < 0.4 = present (tune during testing).

---

## 5. Enrollment Flow (Agent Direction)

```
Student uploads 1–5 photos (different angles)
  → Backend receives images
  → For each photo:
      InsightFace detects face → extracts 512-dim ArcFace embedding
  → Average all embeddings → single mean vector
  → Store mean vector in face_embeddings table
  → Store profile photo on Cloudinary (optional)
  → Return success to student
```

Key rule: **one row per student** in `face_embeddings`. Re-enrollment replaces the existing row.

---

## 6. Live Attendance Pipeline (Agent Direction)

```
Lecturer starts session (selects course) → session row created in DB
  → Frontend opens webcam / video stream
  → Frames sent to backend (or processed server-side via WebSocket)
  → For each frame batch:
      OpenCV decodes frame
      SCRFD detects all faces → returns bounding boxes
      ByteTrack assigns track IDs to each face
      For NEW track IDs only:
          ArcFace (ONNX) extracts 512-dim embedding
          pgvector cosine search → nearest student
          If distance < threshold → mark student present in attendance table
      Confirmed tracks: skip re-recognition for next N frames
  → Frontend shows live "detected" list updating in real time
  → Lecturer ends session → session closed
```

Key rule: **ByteTrack prevents re-running ArcFace on confirmed faces**. Only new track IDs trigger the expensive embedding + search step.

---

## 7. API Endpoints (Target)

```
POST   /auth/login
POST   /students/register
POST   /students/{id}/enroll          ← upload photos, generate embeddings
GET    /students/                     ← list all students

POST   /sessions/start                ← lecturer starts attendance
POST   /sessions/{id}/end
WS     /sessions/{id}/stream          ← WebSocket for live frame processing
GET    /sessions/{id}/attendance      ← who was marked present

GET    /attendance/export?session_id= ← returns CSV/Excel via pandas
GET    /dashboard/stats               ← summary for admin
```

---

## 8. Build Order (Agent Should Follow This Sequence)

### Phase 1 — Foundation
1. PostgreSQL setup + pgvector extension enabled
2. DB schema creation (SQLAlchemy models)
3. FastAPI project scaffold with uv
4. Auth (JWT, lecturer vs student vs admin roles)

### Phase 2 — Enrollment
5. Student registration endpoint
6. Photo upload → InsightFace embedding extraction
7. Embedding averaging + pgvector storage
8. Cloudinary profile photo upload (optional)

### Phase 3 — Live Recognition
9. OpenCV frame capture / WebSocket stream receiver
10. SCRFD face detection on frames
11. ByteTrack integration for face tracking
12. ArcFace ONNX embedding + pgvector cosine search
13. Attendance marking with confidence score

### Phase 4 — Frontend
14. Lecturer dashboard (start session, live detected faces list)
15. Student registration page (webcam capture or file upload)
16. Admin panel (student list, attendance history)

### Phase 5 — Export & Polish
17. pandas CSV/Excel export endpoint
18. Attendance dashboard with per-session stats
19. Confidence threshold tuning
20. Anti-spoofing (v2, optional)

---

## 9. uv Installation Commands

```bash
# Core AI stack
uv add insightface
uv add onnxruntime          # CPU inference (use onnxruntime-gpu if CUDA available)
uv add opencv-python-headless
uv add numpy

# Tracking
uv add lap                  # dependency for ByteTrack
# ByteTrack — install from source (no official PyPI package)
# git clone https://github.com/ifzhang/ByteTrack && pip install -e ByteTrack

# Backend
uv add fastapi
uv add "uvicorn[standard]"
uv add python-multipart     # for file uploads
uv add python-jose          # JWT auth
uv add passlib              # password hashing
uv add websockets

# Database
uv add sqlalchemy
uv add asyncpg              # async postgres driver
uv add psycopg2-binary      # sync fallback / migrations
uv add pgvector             # pgvector SQLAlchemy integration

# Storage & export
uv add cloudinary
uv add pandas
uv add openpyxl             # Excel export via pandas

# Dev tools
uv add --dev pytest
uv add --dev httpx          # for testing FastAPI
```

> **ByteTrack note:** ByteTrack has no stable PyPI release. Install from GitHub:
> `git clone https://github.com/ifzhang/ByteTrack.git && cd ByteTrack && uv pip install -e .`
> Alternative: use `supervision` library which bundles ByteTrack — `uv add supervision`

---

## 10. Environment Variables Required

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
SECRET_KEY=your_jwt_secret
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
RECOGNITION_THRESHOLD=0.4   # cosine distance; lower = stricter
FRAME_SAMPLE_RATE=5         # process every Nth frame
```

---

## 11. Key Decisions for Agent to Remember

- **Never store raw images in PostgreSQL** — embeddings only
- **Threshold tuning**: start at 0.4 cosine distance, adjust based on false positive rate in testing
- **ByteTrack replaces per-frame recognition** — only trigger ArcFace on new track IDs
- **ONNX Runtime** is mandatory for performance — load model once at startup, reuse
- **pgvector** cosine search handles the matching — no sklearn needed
- **One averaged embedding per student** — re-enrollment overwrites, does not append
- **WebSocket** for live feed, not polling — latency matters for real-time display
- **supervision** library as ByteTrack shortcut if direct install causes issues
