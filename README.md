# AutoAttendance

Face-recognition-based classroom attendance. Each professor enrolls their students once
(a guided 5-angle capture per student), then takes attendance by pointing a phone or
laptop camera at the classroom — every enrolled face in the photo is detected and matched
in one shot, scoped to that course's roster only.

## Why this design

- **Multi-tenant**: each professor logs in and manages their own courses independently.
- **BYOD**: no dedicated kiosk hardware — any browser with a camera works (phone or laptop).
- **Per-course-scoped matching**: face matching only searches the enrolled students of the
  specific course being taken, not the whole university — this keeps 1:N identification
  accuracy high regardless of total institution size.
- **Multi-angle enrollment**: 5 guided captures (front/left/right/up/down) per student
  improve real-world matching robustness versus a single enrollment photo.
- **Multi-face detection**: one classroom photo is enough — every face in frame is detected
  and matched in a single request, not one student at a time.

## Accuracy

Benchmarked against the public LFW (Labeled Faces in the Wild) dataset —
[notebooks/face_accuracy_benchmark.ipynb](notebooks/face_accuracy_benchmark.ipynb) — using
InsightFace's `buffalo_s` model (CPU-only detection + recognition, no GPU needed):

| Course roster size | 1:N accuracy |
|---------------------|--------------|
| 10 students          | 100.0%       |
| 30 students          | 98.5%        |
| 60 students           | 98.5%        |
| 100 students          | 99.0%        |
| 300 students          | 99.0%        |

This is a conservative baseline (single enrollment photo per person in the benchmark); the
production app's 5-angle enrollment should improve on it further. LFW photos are also
better-lit and more front-facing than a typical classroom webcam shot, so real-world
accuracy will vary with lighting and camera angle — see the notebook's conclusion for the
full honest caveat.

## Stack

- **Backend**: FastAPI, async SQLAlchemy (asyncpg), PostgreSQL, PyJWT + Argon2 (`pwdlib`)
- **Face recognition**: InsightFace `buffalo_s` (ONNX runtime, CPU), stored as 512-d
  embeddings per enrollment angle (`ARRAY(Float)` column, no vector DB extension needed at
  this scale — matching is plain cosine similarity, application-side)
- **Frontend**: React + TypeScript + Vite, Tailwind CSS, browser `getUserMedia` for camera
  capture (no native app needed)

## Commands

```bash
# Backend
cd backend
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL, JWT_SECRET
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (dev)
cd frontend
npm install
npm run dev   # http://localhost:5173

# Frontend (production build)
cd frontend
npm run build
```

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## API overview

| Endpoint | Purpose |
|----------|---------|
| `POST /auth/signup`, `/auth/login` | Professor account auth (JWT) |
| `POST /courses`, `GET /courses` | Course CRUD, scoped to the logged-in professor |
| `POST /courses/{id}/students` | Add a student to a course roster |
| `POST /courses/{id}/students/{id}/enroll-face?angle_label=front` | Upload one enrollment angle |
| `POST /courses/{id}/attendance/sessions` | Start a new attendance session |
| `POST /courses/{id}/attendance/sessions/{id}/mark` | Upload a classroom photo — detects and matches every face against that course's roster |
| `GET /courses/{id}/attendance/sessions/{id}` | Full present/absent roster for a session |

## Deployment

Live on Oracle Cloud's Always Free tier (`VM.Standard.A1.Flex`, 4 OCPU / 24GB ARM Ampere),
systemd service + Nginx + Postgres, matching the deployment pattern used across this
portfolio's other projects (ClauseGuard, CaReSale, PptGen, kGPT).
