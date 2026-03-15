from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from sqlalchemy import text
import threading
import traceback

from .db import engine, Base, SessionLocal
from .api.routes_health import router as health_router
from .ingest.conflicts_ucdp import seed_builtin_conflicts
from .api.routes_geo import router as geo_router
from .api.routes_prices import router as prices_router
from .api.routes_status import router as status_router
from .api.routes_czml import router as czml_router
from .ingest.scheduler import start_scheduler, run_flights_ingest_once, run_cameras_ingest_once

app = FastAPI(title="Centaur Backend", version="0.2.0")


@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    tb = traceback.format_exc()
    print(f"500 error: {exc}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    try:
        with engine.begin() as conn:
            conn.execute(text("SELECT create_hypertable('flight_track_point', 'ts', if_not_exists => TRUE);"))
    except Exception:
        pass
    # Seed builtin conflict zones so they persist in DB and always appear
    try:
        db = SessionLocal()
        seed_builtin_conflicts(db)
        db.close()
    except Exception:
        pass
    start_scheduler()
    # Run camera ingest once in main thread so first page load has IP camera data
    try:
        run_cameras_ingest_once()
    except Exception:
        pass
    _run_initial_ingests()

def _run_initial_ingests():
    """Run flight and camera ingests once immediately so the first page load has data."""
    def _run():
        try:
            run_flights_ingest_once()
        except Exception:
            pass
        try:
            run_cameras_ingest_once()
        except Exception:
            pass
    t = threading.Thread(target=_run, daemon=True)
    t.start()

app.include_router(health_router)
app.include_router(status_router)
app.include_router(geo_router)
app.include_router(prices_router)
app.include_router(czml_router)

def run():
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)

if __name__ == "__main__":
    run()
