from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone, timedelta
from time import perf_counter
from sqlalchemy.orm import Session
from sqlalchemy import delete

from ..db import SessionLocal
from ..settings import settings
from ..models import IngestJobStatus, FlightTrackPoint, FuelStationPrice, IpCameraCity
from ..logging_util import log

from .flights_airplanes_live import ingest_flights_airplanes_live
from .conflicts_ucdp import ingest_conflicts_ucdp
from .prices_eia import ingest_eia_oil
from .prices_stooq import ingest_stooq_gold
from .fuel_france import ingest_fuel_france
from .cameras_shodan import ingest_cameras_shodan

_scheduler = None

def parse_aois():
    aois = []
    raw = settings.AOIS.strip()
    if not raw:
        log("aois_empty_using_default", default="worldwide")
        return _default_worldwide_aois()
    for item in raw.split(";"):
        if not item.strip():
            continue
        parts = [p.strip() for p in item.split(",")]
        if len(parts) != 5:
            log("aois_invalid_line", line=item[:80], reason="expected 5 comma-separated values")
            continue
        name, min_lat_s, min_lon_s, max_lat_s, max_lon_s = parts
        if not name:
            log("aois_invalid_line", line=item[:80], reason="name empty")
            continue
        try:
            min_lat = float(min_lat_s)
            min_lon = float(min_lon_s)
            max_lat = float(max_lat_s)
            max_lon = float(max_lon_s)
        except (TypeError, ValueError):
            log("aois_invalid_line", line=item[:80], reason="non-numeric bounds")
            continue
        aois.append({"name": name, "minLat": min_lat, "minLon": min_lon, "maxLat": max_lat, "maxLon": max_lon})
    if not aois:
        log("aois_no_valid_entries_using_default", default="worldwide")
        return _default_worldwide_aois()
    return aois


def _default_worldwide_aois():
    """Default AOIs covering all continents and subregions so planes appear in every country."""
    return [
        {"name": "EUROPE_W", "minLat": 35.0, "minLon": -10.0, "maxLat": 55.0, "maxLon": 10.0},
        {"name": "EUROPE_E", "minLat": 42.0, "minLon": 10.0, "maxLat": 60.0, "maxLon": 30.0},
        {"name": "NAMERICA_W", "minLat": 25.0, "minLon": -125.0, "maxLat": 50.0, "maxLon": -95.0},
        {"name": "NAMERICA_E", "minLat": 28.0, "minLon": -95.0, "maxLat": 50.0, "maxLon": -65.0},
        {"name": "CARIBBEAN", "minLat": 10.0, "minLon": -90.0, "maxLat": 28.0, "maxLon": -60.0},
        {"name": "SAMERICA_N", "minLat": -15.0, "minLon": -80.0, "maxLat": 15.0, "maxLon": -35.0},
        {"name": "SAMERICA_S", "minLat": -55.0, "minLon": -75.0, "maxLat": -15.0, "maxLon": -50.0},
        {"name": "AFRICA_N", "minLat": 5.0, "minLon": -20.0, "maxLat": 38.0, "maxLon": 52.0},
        {"name": "AFRICA_S", "minLat": -35.0, "minLon": 10.0, "maxLat": 0.0, "maxLon": 42.0},
        {"name": "MIDDLE_EAST", "minLat": 12.0, "minLon": 25.0, "maxLat": 42.0, "maxLon": 75.0},
        {"name": "CENTRAL_ASIA", "minLat": 25.0, "minLon": 55.0, "maxLat": 55.0, "maxLon": 95.0},
        {"name": "SOUTH_ASIA", "minLat": 5.0, "minLon": 65.0, "maxLat": 35.0, "maxLon": 95.0},
        {"name": "SE_ASIA", "minLat": -10.0, "minLon": 95.0, "maxLat": 25.0, "maxLon": 145.0},
        {"name": "EAST_ASIA", "minLat": 20.0, "minLon": 100.0, "maxLat": 55.0, "maxLon": 145.0},
        {"name": "AUSTRALIA", "minLat": -45.0, "minLon": 110.0, "maxLat": -10.0, "maxLon": 155.0},
    ]

def record_status(db: Session, job_name: str, ok: bool, duration_ms: int, item_count: int, error: str | None):
    db.add(IngestJobStatus(job_name=job_name, ran_at=datetime.now(timezone.utc), duration_ms=duration_ms, ok=ok, item_count=item_count, error=error))
    db.commit()

def retention_sweep(db: Session):
    cutoff_tracks = datetime.now(timezone.utc) - timedelta(hours=settings.FLIGHT_TRACK_RETENTION_HOURS)
    db.execute(delete(FlightTrackPoint).where(FlightTrackPoint.ts < cutoff_tracks))

    cutoff_fuel = datetime.now(timezone.utc) - timedelta(hours=settings.FUEL_PRICE_RETENTION_HOURS)
    db.execute(delete(FuelStationPrice).where(FuelStationPrice.observed_at < cutoff_fuel))

    cutoff_cameras = datetime.now(timezone.utc) - timedelta(days=settings.CAMERAS_RETENTION_DAYS)
    db.execute(delete(IpCameraCity).where(IpCameraCity.observed_at < cutoff_cameras))

    cutoff_status = datetime.now(timezone.utc) - timedelta(days=settings.STATUS_HISTORY_DAYS)
    db.execute(delete(IngestJobStatus).where(IngestJobStatus.ran_at < cutoff_status))
    db.commit()

def job_wrap(fn, name: str):
    def _inner():
        db: Session = SessionLocal()
        start = perf_counter()
        ok = True
        count = 0
        err = None
        try:
            count = fn(db=db, aois=parse_aois()) or 0
        except Exception as e:
            ok = False
            err = str(e)[:1000]
            log("ingest_error", job=name, error=err)
            try:
                db.rollback()
            except Exception:
                pass
        finally:
            duration_ms = int((perf_counter() - start) * 1000)
            try:
                record_status(db, name, ok, duration_ms, int(count), err)
                retention_sweep(db)
            except Exception as e2:
                log("status_error", job=name, error=str(e2)[:1000])
            db.close()
    return _inner

# Prevent overlapping job runs; allow late start within this many seconds
MISFIRE_GRACE_SECONDS = 600

def start_scheduler():
    global _scheduler
    if _scheduler: return
    _scheduler = BackgroundScheduler(timezone=timezone.utc)
    job_opts = {"max_instances": 1, "misfire_grace_time": MISFIRE_GRACE_SECONDS}
    _scheduler.add_job(job_wrap(ingest_flights_airplanes_live, "flights_airplanes_live"), "interval", seconds=settings.INGEST_FLIGHTS_SECONDS, **job_opts)
    _scheduler.add_job(job_wrap(ingest_eia_oil, "prices_eia_oil"), "interval", minutes=settings.INGEST_PRICES_MINUTES, **job_opts)
    _scheduler.add_job(job_wrap(ingest_stooq_gold, "prices_stooq_gold"), "interval", minutes=settings.INGEST_PRICES_MINUTES, **job_opts)
    _scheduler.add_job(job_wrap(ingest_fuel_france, "fuel_france"), "interval", minutes=settings.INGEST_FUEL_MINUTES, **job_opts)
    _scheduler.add_job(job_wrap(ingest_conflicts_ucdp, "conflicts_ucdp"), "interval", minutes=settings.INGEST_CONFLICTS_MINUTES, **job_opts)
    _scheduler.add_job(job_wrap(ingest_cameras_shodan, "cameras_shodan"), "interval", minutes=settings.INGEST_CAMERAS_MINUTES, **job_opts)
    _scheduler.start()
    log("scheduler_started")


def run_flights_ingest_once():
    """Run the flights ingest job once (e.g. on startup for immediate data)."""
    job_wrap(ingest_flights_airplanes_live, "flights_airplanes_live")()


def run_cameras_ingest_once():
    """Run the cameras ingest job once on startup so /geo/cameras has data."""
    job_wrap(ingest_cameras_shodan, "cameras_shodan")()
