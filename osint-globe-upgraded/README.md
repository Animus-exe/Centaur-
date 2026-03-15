# Centaur

Centaur is a practical OSINT mapping stack built with a FastAPI ingestion backend, a Cesium frontend, and Postgres/Timescale.

The goal is simple: keep a live geospatial view of public sources while making data quality and ingest health easy to inspect.

---

## At a glance

| Area | Details |
| --- | --- |
| Frontend | React + Cesium |
| Backend | FastAPI + scheduled ingestion jobs |
| Database | Postgres / Timescale |
| Main outputs | GeoJSON, CZML, status telemetry |
| Core goal | Reliable OSINT map operations with clear data behavior |

## What you get

- Live flights scoped by AOIs from public flight feeds.
- Time-playback flight tracks served as CZML.
- Fuel prices for France from open data.
- Commodity snapshots (Brent, WTI, gold proxy).
- Conflict areas (optional UCDP token) rendered as area truth plus UI anchor.
- Operational metrics via `/status` for job success, duration, and error context.

## Architecture

`frontend (React + Cesium)` -> `backend (FastAPI)` -> `db (Postgres/Timescale)`

- `frontend`: map rendering, layer controls, playback UI.
- `backend`: ingestion scheduling, normalization, and API delivery.
- `db`: persistence for tracks, prices, areas, and ingestion state.

---

## Quickstart

### 1) Create env file

```bash
cp .env.example .env
```

### 2) Optional tokens in `.env`

- `VITE_CESIUM_ION_TOKEN` for terrain
- `UCDP_TOKEN` for live conflict ingestion
- `SHODAN_API_KEY` for camera ingestion
- `OPENSKY_USERNAME` and `OPENSKY_PASSWORD` for improved flight-source limits

### 3) Start with Docker

```bash
docker compose up --build
```

### 4) Open services

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`
- Ingestion status: `http://localhost:8000/status`

For full local and Windows-first startup steps, see `STARTUP_GUIDE.md`.

---

## API quick reference

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Backend health check |
| `GET /status` | Ingestion job health, timings, and errors |
| `GET /geo/flights?max_age_seconds=90` | Live flight markers |
| `GET /czml/flights?hours=6&max_aircraft=120` | Flight playback tracks |
| `GET /geo/conflicts?hours=168` | Conflict area layer |
| `GET /geo/fuel/france?hours=24` | Fuel station prices |
| `GET /prices/latest` | Commodity snapshot |

## Data integrity rules

- Area geometry is truth for conflict-style events.
- UI anchors are display-only and not analytical coordinates.
- No hidden geocoding inference from free-text locations.
- Any derived coordinate logic should be explicitly tagged.

## Troubleshooting

- Blank globe: check `http://localhost:8000/health` and `http://localhost:8000/status`.
- Conflicts missing: verify `UCDP_TOKEN` and inspect `/status`.
- Slow or missing flights: add OpenSky credentials and tune polling values in `.env`.
- Stale frontend assets: run `docker compose build frontend --no-cache`.

## Project layout

- `frontend/`: React + Cesium app
- `backend/`: FastAPI app, ingestion jobs, models
- `docker-compose.yml`: local multi-service stack
- `.env.example`: root environment template
- `backend/.env.example`: backend-only environment template

---

## Operational note

Public OSINT providers are rate-limited and can change without notice. Centaur is built to fail soft where possible, but upstream licensing and ToS compliance remain your responsibility.
