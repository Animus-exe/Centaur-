"""
Ingest IP cameras from Shodan and persist to ip_camera_city for /geo/cameras.
"""
from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..models import IpCameraCity
from ..settings import settings
from ..logging_util import log
from .. import shodan_cameras as shodan_cameras_module


def _safe_float(val) -> float | None:
    """Return float or None for missing/non-numeric values."""
    if val is None:
        return None
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def ingest_cameras_shodan(db: Session, aois: list) -> int:
    """Fetch cameras from Shodan (stream API first for free keys, then search), upsert into IpCameraCity."""
    if not settings.SHODAN_API_KEY:
        return 0
    rows: list[dict] = []
    # Try stream first (works with free API key): pull port 554 stream for a short period
    try:
        rows = shodan_cameras_module.fetch_cameras_from_shodan_stream(
            api_key=settings.SHODAN_API_KEY,
            ports="554",
            collect_seconds=shodan_cameras_module.STREAM_COLLECT_SECONDS,
            max_cameras=shodan_cameras_module.STREAM_MAX_CAMERAS,
        )
        if rows:
            log("cameras_shodan_ingest_source", source="stream", cities=len(rows))
    except Exception as e:
        err_msg = str(e)[:500]
        log("cameras_shodan_ingest_stream_failed", error=err_msg)
        # Fallback to search API (requires paid membership)
        try:
            rows = shodan_cameras_module.fetch_cameras_from_shodan(
                api_key=settings.SHODAN_API_KEY,
                query=shodan_cameras_module.DEFAULT_QUERY,
                max_results=300,
            )
            if rows:
                log("cameras_shodan_ingest_source", source="search", cities=len(rows))
        except Exception as e2:
            log("cameras_shodan_ingest_failed", error=str(e2)[:500])
            return 0
    if not rows:
        return 0
    now = datetime.now(timezone.utc)
    count = 0
    for r in rows:
        city = (r.get("city") or "").strip() or "Unknown"
        country_code = (r.get("country_code") or "").strip() or "XX"
        country_name = (r.get("country_name") or "").strip() or ""
        lon = _safe_float(r.get("lon"))
        lat = _safe_float(r.get("lat"))
        if lon is None or lat is None:
            continue
        cameras = r.get("cameras") or []
        existing = db.execute(
            select(IpCameraCity).where(
                IpCameraCity.city == city,
                IpCameraCity.country_code == country_code,
            )
        ).scalars().first()
        if existing is None:
            db.add(IpCameraCity(
                city=city,
                country_code=country_code,
                country_name=country_name,
                lon=lon,
                lat=lat,
                cameras=cameras,
                observed_at=now,
            ))
            count += 1
        else:
            existing.country_name = country_name
            existing.lon = lon
            existing.lat = lat
            existing.cameras = cameras
            existing.observed_at = now
    db.commit()
    return count
