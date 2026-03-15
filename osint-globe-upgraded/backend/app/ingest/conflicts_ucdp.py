from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select
from shapely.geometry import box

from ..models import ConflictAreaEvent
from ..settings import settings
from ..data.builtin_conflicts import BUILTIN_CONFLICTS
from .util_http import get_client, get_with_retry
from .anchors import anchor_for_geojson_geometry

UCDP_BASE = "https://ucdpapi.pcr.uu.se/api/gedevents/25.1"


def seed_builtin_conflicts(db: Session) -> int:
    """If no conflict areas exist, insert builtin list so conflict zones always appear and persist."""
    existing = db.execute(select(ConflictAreaEvent).limit(1)).scalars().first()
    if existing:
        return 0
    now = datetime.now(timezone.utc)
    for i, c in enumerate(BUILTIN_CONFLICTS):
        poly = box(c["minLon"], c["minLat"], c["maxLon"], c["maxLat"])
        db.add(ConflictAreaEvent(
            source="builtin",
            source_event_id=f"builtin_{i}",
            title=c["title"],
            category="conflict",
            start_time=now,
            end_time=now,
            geometry_wkt=poly.wkt,
            anchor_lon=c["anchor_lon"],
            anchor_lat=c["anchor_lat"],
            location_tier="AREA_ONLY",
            anchor_method="builtin",
            fatalities=c.get("fatalities"),
            observed_at=now,
            source_url=None,
            raw={},
        ))
    db.commit()
    return len(BUILTIN_CONFLICTS)

def ingest_conflicts_ucdp(db: Session, aois: list[dict]) -> int:
    token = (settings.UCDP_TOKEN or "").strip()
    if not token or not aois: return 0
    client = get_client()
    client.headers["x-ucdp-access-token"] = token

    end = datetime.now(timezone.utc).date()
    start = (datetime.now(timezone.utc) - timedelta(days=7)).date()
    inserted = 0

    for aoi in aois:
        geo = f"{aoi['minLat']},{aoi['minLon']},{aoi['maxLat']},{aoi['maxLon']}"
        url = f"{UCDP_BASE}?pagesize=100&StartDate={start}&EndDate={end}&Geography={geo}"
        r = get_with_retry(url, client)
        if r.status_code != 200: continue
        payload = r.json()
        results = payload.get("Result", []) or payload.get("result", []) or []

        for ev in results:
            poly = box(aoi["minLon"], aoi["minLat"], aoi["maxLon"], aoi["maxLat"])
            geom_geojson = {"type": "Polygon", "coordinates": [[
                (aoi["minLon"], aoi["minLat"]),
                (aoi["maxLon"], aoi["minLat"]),
                (aoi["maxLon"], aoi["maxLat"]),
                (aoi["minLon"], aoi["maxLat"]),
                (aoi["minLon"], aoi["minLat"]),
            ]]}
            anch_lon, anch_lat, method = anchor_for_geojson_geometry(geom_geojson)

            source_id = str(ev.get("id") or ev.get("EventId") or ev.get("event_id") or "")
            if not source_id:
                source_id = f"{ev.get('date_start','')}_{ev.get('where','')}_{ev.get('type_of_violence','')}".strip()
            source_id = f"{aoi['name']}::{source_id}"

            existing = db.execute(select(ConflictAreaEvent).where(ConflictAreaEvent.source == "ucdp", ConflictAreaEvent.source_event_id == source_id)).scalar_one_or_none()
            title = (ev.get("where") or ev.get("location") or "UCDP Event").strip()
            fatalities = ev.get("best") or ev.get("deaths_b") or ev.get("deaths") or None
            try:
                fatalities_int = int(fatalities) if fatalities is not None else None
            except (TypeError, ValueError):
                fatalities_int = None

            start_time = datetime.now(timezone.utc) - timedelta(hours=1)
            end_time = datetime.now(timezone.utc)

            if existing:
                existing.title = title
                existing.fatalities = fatalities_int
                existing.geometry_wkt = poly.wkt
                existing.anchor_lon = anch_lon
                existing.anchor_lat = anch_lat
                existing.anchor_method = method
                existing.observed_at = datetime.now(timezone.utc)
                existing.raw = ev
            else:
                db.add(ConflictAreaEvent(
                    source="ucdp", source_event_id=source_id,
                    title=title, category="conflict",
                    start_time=start_time, end_time=end_time,
                    geometry_wkt=poly.wkt,
                    anchor_lon=anch_lon, anchor_lat=anch_lat,
                    location_tier="AREA_ONLY",
                    anchor_method=method,
                    fatalities=fatalities_int,
                    observed_at=datetime.now(timezone.utc),
                    source_url="", raw=ev
                ))
                inserted += 1
    db.commit()
    return inserted
