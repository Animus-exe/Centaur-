# Run Centaur Backend

The app uses plain PostgreSQL (no PostGIS required). Coordinates are stored as lat/lon columns.

## 1. Create database (one-time)

Run from the `backend` directory.
You can either use `psql` from PATH, or point directly to your local Postgres install.
If needed, set `PGPASSWORD` temporarily to avoid prompts.

```powershell
cd backend
$env:PGPASSWORD = "<your_postgres_password>"
psql -U postgres -f ".\scripts\create_db.sql"
```

If `psql` is not on PATH, use:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -f ".\scripts\create_db.sql"
```

If you previously used a PostGIS schema, drop old tables (or recreate the DB) before starting:

```powershell
psql -U postgres -d osint -c "DROP TABLE IF EXISTS flight_track_point, flight_state, conflict_area_event, fuel_station_price, ingest_job_status, commodity_price CASCADE;"
```

Then start the backend again so it recreates the tables.

## 2. Start backend

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 3. Start frontend (in another terminal)

```powershell
cd frontend
npm run dev
```

Open the URL shown (e.g. http://localhost:5173/ or 5175). Flights will appear once the backend is running and ingest has fetched data (within ~15 seconds).
