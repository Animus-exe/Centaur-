from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta, timezone

from ..db import get_db
from ..models import FlightTrackPoint

router = APIRouter(prefix="/czml", tags=["czml"])

@router.get("/flights")
def czml_flights(db: Session = Depends(get_db), hours: int = Query(6, ge=1, le=24), max_aircraft: int = Query(120, ge=1, le=1000)):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    icao_rows = db.execute(select(FlightTrackPoint.icao24).where(FlightTrackPoint.ts >= cutoff).distinct().limit(max_aircraft)).all()
    icaos = [r[0] for r in icao_rows]

    all_starts = []
    all_stops = []
    czml = []

    for icao in icaos:
        pts = db.execute(
            select(FlightTrackPoint).where(FlightTrackPoint.icao24 == icao, FlightTrackPoint.ts >= cutoff).order_by(FlightTrackPoint.ts.asc())
        ).scalars().all()
        if len(pts) < 2:
            continue

        start = pts[0].ts
        stop = pts[-1].ts
        all_starts.append(start)
        all_stops.append(stop)
        carto = []
        for p in pts:
            seconds = (p.ts - start).total_seconds()
            alt = float(p.altitude_m) if p.altitude_m is not None else 0.0
            carto.extend([seconds, float(p.lon), float(p.lat), alt])

        czml.append({
            "id": f"flight-{icao}",
            "name": pts[-1].callsign or icao,
            "availability": f"{start.isoformat()}/{stop.isoformat()}",
            "position": {"epoch": start.isoformat(), "cartographicDegrees": carto},
            "path": {
                "leadTime": 0,
                "trailTime": hours * 3600,
                "width": 3,
                "resolution": 60,
                "material": {"solidColor": {"color": {"rgba": [50, 200, 255, 180]}}}
            }
        })

    clock_interval = None
    if all_starts and all_stops:
        doc_start = min(all_starts).isoformat()
        doc_stop = max(all_stops).isoformat()
        clock_interval = f"{doc_start}/{doc_stop}"
    if not clock_interval:
        doc_start = cutoff.isoformat()
        now = datetime.now(timezone.utc).isoformat()
        clock_interval = f"{doc_start}/{now}"
    doc = {"id": "document", "name": "Flight Tracks", "version": "1.0"}
    doc["clock"] = {
        "interval": clock_interval,
        "currentTime": clock_interval.split("/")[1],
        "multiplier": 1,
        "range": "LOOP_STOP",
        "step": "SYSTEM_CLOCK_STEP"
    }
    return [doc] + czml
