# Startup Guide

This guide gives you two ways to run Centaur:

- Docker stack (fastest, recommended)
- Local dev run (backend + frontend directly)

## Prerequisites

### Docker path

- Docker Desktop (or Docker Engine + Compose plugin)

### Local path

- Python 3.11+
- Node.js 18+
- npm
- PostgreSQL 16+ (or equivalent)

## Option A: Docker (recommended)

### 1) Create env file

From the project root:

```bash
cp .env.example .env
```

On PowerShell (if `cp` alias is unavailable):

```powershell
Copy-Item .env.example .env
```

### 2) Optional env values

Edit `.env` and set any needed values:

- `VITE_CESIUM_ION_TOKEN` for Cesium terrain
- `UCDP_TOKEN` for live conflict ingestion
- `SHODAN_API_KEY` for camera layer ingestion
- `OPENSKY_USERNAME` and `OPENSKY_PASSWORD` to reduce rate limits

### 3) Start services

```bash
docker compose up --build
```

### 4) Verify

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`
- Backend ingestion status: `http://localhost:8000/status`

If status shows ingestion errors, open `/status` and inspect each job's `error` and `last_run`.

## Option B: Local development run

### 1) Database setup

Create the database and schema:

```powershell
cd backend
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -f ".\scripts\create_db.sql"
cd ..
```

If your `psql` binary is already on `PATH`, you can use:

```bash
psql -U postgres -f backend/scripts/create_db.sql
```

### 2) Backend env

Create backend env file:

```bash
cp backend/.env.example backend/.env
```

Set at minimum:

- `DATABASE_URL` (local Postgres connection)

Optionally add the same tokens described in Docker mode.

### 3) Create backend virtual env + install deps

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4) Start backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5) Start frontend (new terminal)

```powershell
cd frontend
npm install
npm run dev
```

Frontend should be available at the URL shown by Vite (typically `http://localhost:5173`).

## Common startup checks

- `http://localhost:8000/health` returns OK
- `http://localhost:8000/status` shows jobs running
- map is visible and layers appear after initial ingestion interval

## Common issues

- Port in use (`8000` or `5173`): stop existing process or change port.
- No flights showing: wait for first ingest cycle; add OpenSky credentials for higher limits.
- Conflicts missing: set `UCDP_TOKEN` or rely on built-in fallback regions.
- Cesium files missing locally: run `npm install` in `frontend` to trigger postinstall asset copy.

## Stop commands

### Docker

```bash
docker compose down
```

### Local

Use `Ctrl+C` in each running terminal (backend/frontend).
