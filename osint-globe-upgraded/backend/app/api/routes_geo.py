from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from datetime import datetime, timedelta, timezone
from shapely.geometry import Point, box
import reverse_geocoder as rg
import pycountry

from ..db import get_db
from ..models import FlightState, ConflictAreaEvent, FuelStationPrice, IpCameraCity
from ..geojson import feature_collection, feature, from_wkt
from ..ingest.flights_airplanes_live import get_opensky_rate_limit_status
from ..settings import settings
from ..data.builtin_conflicts import (
    BUILTIN_CONFLICTS,
    conflict_feature_properties,
    builtin_to_feature_properties,
)
from ..data.military_aircraft import MILITARY_AIRCRAFT_TYPES, MILITARY_ICAO24_PREFIXES
router = APIRouter(prefix="/geo", tags=["geo"])

# Common military / state flight callsign prefixes (ADS-B)
MILITARY_CALLSIGN_PREFIXES = frozenset({
    "RCH", "REACH", "EVAC", "HKY", "GAF", "IAM", "RFR", "RR", "CNV", "PAT",
    "NAVY", "ARMY", "AIRFORCE", "USAF", "RAF", "LUFTWAFFE", "RMAF", "IAF", "PAF",
    "RAAF", "RNZAF", "CAF", "KAF", "HAF", "BAF", "DAF", "NAF", "MAF",
    "SAM", "SPAR", "VVIP", "VIP", "JEEP", "BOB", "JUDY", "ASCOT", "NATO",
    "HUSKY", "COBRA", "GOLD", "VADER", "SENTRY", "SNAKE", "TAZMAN", "RAGE",
    "WOLF", "VIPER", "HAWK", "DEMON", "DEVIL", "ANVIL", "BLUE", "RED",
})

MILITARY_KEYWORDS = frozenset({
    "air force", "airforce", "navy", "army", "marines", "military",
    "defense", "defence", "ministry of defence", "nato", "state air", "government",
    "armed forces", "national guard", "coast guard",
})

CIVILIAN_KEYWORDS = frozenset({
    "airlines", "airways", "cargo", "express", "charter", "logistics"
})


def _to_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip(), 0)
        except ValueError:
            return None
    return None


def _military_assessment(
    callsign: str | None, raw: dict | None, icao24: str | None = None
) -> tuple[bool, int, list[str]]:
    """
    Military heuristic with confidence scoring.
    Threshold tuned to reduce false positives while keeping likely targets visible:
      - strong source flags/metadata can classify directly
      - callsign prefixes are medium confidence
      - supportive metadata pushes borderline cases over threshold
    """
    score = 0
    reasons: list[str] = []
    data = raw or {}

    db_flags = _to_int(data.get("dbFlags"))
    if db_flags is not None and (db_flags & 1) == 1:
        score += 100
        reasons.append("dbFlags military bit set")

    if data.get("military") is True or data.get("is_military") is True:
        score += 100
        reasons.append("explicit military flag in source")

    # Military ICAO aircraft type designator (e.g. C17, F16, K35R, C130J)
    ac_type_raw = (data.get("t") or data.get("type") or "").strip().upper().replace(" ", "")
    if ac_type_raw:
        ac_type_4 = ac_type_raw[:4]
        if ac_type_raw in MILITARY_AIRCRAFT_TYPES or ac_type_4 in MILITARY_AIRCRAFT_TYPES:
            score += 55
            reasons.append("military aircraft type")

    # OpenSky extended category: 14 = UAV (often military)
    cat = _to_int(data.get("category"))
    if cat == 14:
        score += 25
        reasons.append("UAV category")

    cs = (callsign or "").strip().upper().replace(" ", "")
    if cs:
        if len(cs) <= 4 and cs.isdigit():
            score += 20
            reasons.append("short numeric callsign")

        for prefix in MILITARY_CALLSIGN_PREFIXES:
            if cs.startswith(prefix):
                score += 50
                reasons.append(f"callsign prefix {prefix}")
                break

        if len(cs) >= 5 and cs[:3] in MILITARY_CALLSIGN_PREFIXES and cs[3:].isdigit():
            score += 25
            reasons.append("military-style alphanumeric callsign")

    text_values = []
    for k in ("ownOp", "owner", "operator", "airline", "desc", "t", "type", "origin_country"):
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            text_values.append(v.lower())
    text_blob = " | ".join(text_values)

    if text_blob:
        if any(k in text_blob for k in MILITARY_KEYWORDS):
            score += 50
            reasons.append("operator/owner metadata indicates military")
        if any(k in text_blob for k in CIVILIAN_KEYWORDS):
            score -= 30
            reasons.append("operator/owner metadata indicates civilian operator")

    # ICAO24 hex prefix hint when no strong signal from type or explicit flags
    hex_val = (icao24 or data.get("icao24") or "").strip().lower()
    if hex_val and len(hex_val) >= 2:
        prefix = hex_val[:2]
        if prefix in MILITARY_ICAO24_PREFIXES and "dbFlags military bit set" not in reasons and "explicit military flag" not in reasons and "military aircraft type" not in reasons:
            score += 35
            reasons.append("ICAO24 in military range")

    score = max(0, min(score, 100))
    is_military = score >= 50
    return is_military, score, reasons


def _likely_military(callsign: str | None, raw: dict | None, icao24: str | None = None) -> bool:
    return _military_assessment(callsign, raw, icao24)[0]

def _country_name_from_code(cc: str | None) -> str | None:
    """Return country name for ISO 3166-1 alpha-2 code, or None."""
    if not cc or len(cc) != 2:
        return None
    c = pycountry.countries.get(alpha_2=cc)
    return c.name if c else None


def _safe_opensky_rate_limit_status() -> dict:
    """Return rate limit status; on failure return safe default so /geo/flights does not 500."""
    try:
        return get_opensky_rate_limit_status()
    except Exception:
        return {"rate_limited": False, "opensky_authenticated": False, "international_coverage": True}


@router.get("/flights")
def geo_flights(db: Session = Depends(get_db), max_age_seconds: int = 900):
    now = datetime.now(timezone.utc)
    # Use extended window when we have no fresh data (rate limited, ingest down, or server restarted)
    # so planes don't disappear; otherwise use requested window.
    rate_status = _safe_opensky_rate_limit_status()
    latest_observed = db.execute(
        select(FlightState.observed_at).order_by(FlightState.observed_at.desc()).limit(1)
    ).scalar_one_or_none()
    fresh_cutoff_ts = (now - timedelta(seconds=max_age_seconds)).timestamp()
    has_fresh_data = latest_observed is not None and latest_observed.timestamp() >= fresh_cutoff_ts
    if rate_status.get("rate_limited") or not has_fresh_data:
        effective_max_age = settings.FLIGHTS_DISPLAY_MAX_AGE_WHEN_RATE_LIMITED_SECONDS
    else:
        effective_max_age = max_age_seconds
    cutoff = now - timedelta(seconds=effective_max_age)
    rows = db.execute(select(FlightState).where(FlightState.observed_at >= cutoff)).scalars().all()
    # Batch reverse-geocode (lat, lon) -> country code
    coords = [(r.lat, r.lon) for r in rows]
    country_results = rg.search(coords) if coords else []
    fresh_cutoff = now - timedelta(seconds=max_age_seconds)
    feats = []
    for i, r in enumerate(rows):
        likely_mil, mil_score, mil_reasons = _military_assessment(
            r.callsign, r.raw if hasattr(r, "raw") else None, r.icao24
        )
        cc = country_results[i].get("cc") if i < len(country_results) else None
        country_name = _country_name_from_code(cc)
        observed_at = r.observed_at
        is_stale = observed_at is not None and observed_at < fresh_cutoff
        feats.append({
            "type": "Feature",
            "id": f"flight:{r.icao24}",
            "geometry": {"type": "Point", "coordinates": [r.lon, r.lat]},
            "properties": {
                "icao24": r.icao24,
                "callsign": r.callsign,
                "lat": r.lat,
                "lon": r.lon,
                "altitude_m": r.altitude_m,
                "velocity_mps": r.velocity_mps,
                "heading_deg": r.heading_deg,
                "observed_at": observed_at.isoformat() if observed_at else None,
                "source": r.source,
                "likely_military": likely_mil,
                "military_confidence": mil_score,
                "military_reasons": mil_reasons,
                "country_code": cc,
                "country_name": country_name,
                "stale": is_stale,
                "raw": r.raw if isinstance(r.raw, dict) else {},
            }
            })
    return feature_collection(feats)


def _cell_overlaps_conflict(cell_min_lon: float, cell_max_lon: float, cell_min_lat: float, cell_max_lat: float) -> bool:
    """True if the cell box overlaps any builtin conflict box."""
    for c in BUILTIN_CONFLICTS:
        if not (cell_max_lon < c["minLon"] or cell_min_lon > c["maxLon"] or cell_max_lat < c["minLat"] or cell_min_lat > c["maxLat"]):
            return True
    return False


@router.get("/early-warning")
def geo_early_warning(
    db: Session = Depends(get_db),
    max_age_seconds: int = Query(120, ge=30, le=600),
    min_military_count: int = Query(4, ge=2, le=20),
    grid_deg: float = Query(2.0, ge=0.5, le=5.0),
):
    """Areas with high military aircraft concentration that are NOT in known conflict zones (early warning)."""
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    rows = db.execute(select(FlightState).where(FlightState.observed_at >= cutoff)).scalars().all()
    # count military flights per grid cell (lon_idx, lat_idx) -> count
    grid: dict[tuple[int, int], int] = {}
    for r in rows:
        if not _likely_military(r.callsign, r.raw if hasattr(r, "raw") else None, r.icao24):
            continue
        lon_idx = int(r.lon // grid_deg)
        lat_idx = int(r.lat // grid_deg)
        key = (lon_idx, lat_idx)
        grid[key] = grid.get(key, 0) + 1

    feats = []
    for (lon_idx, lat_idx), count in grid.items():
        if count < min_military_count:
            continue
        cell_min_lon = lon_idx * grid_deg
        cell_max_lon = cell_min_lon + grid_deg
        cell_min_lat = lat_idx * grid_deg
        cell_max_lat = cell_min_lat + grid_deg
        if _cell_overlaps_conflict(cell_min_lon, cell_max_lon, cell_min_lat, cell_max_lat):
            continue
        poly = box(cell_min_lon, cell_min_lat, cell_max_lon, cell_max_lat)
        feats.append(feature(poly, {
            "title": f"Early warning — {count} military aircraft",
            "military_count": count,
            "category": "early_warning",
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }, fid=f"early_warning:{lon_idx}:{lat_idx}"))
    return feature_collection(feats)


@router.get("/conflicts")
def geo_conflicts(db: Session = Depends(get_db), hours: int = Query(168, ge=1, le=24*90)):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    rows = db.execute(
        select(ConflictAreaEvent).where(ConflictAreaEvent.observed_at >= cutoff).order_by(desc(ConflictAreaEvent.observed_at))
    ).scalars().all()
    feats = []
    for r in rows:
        if not r.geometry_wkt or r.anchor_lon is None or r.anchor_lat is None:
            continue
        poly = from_wkt(r.geometry_wkt)
        if poly is None:
            continue
        props = conflict_feature_properties(
            title=r.title,
            category=r.category or "conflict",
            anchor_lon=r.anchor_lon,
            anchor_lat=r.anchor_lat,
            fatalities=r.fatalities,
            source=r.source,
            source_event_id=r.source_event_id,
            source_url=r.source_url,
            start_time=r.start_time,
            end_time=r.end_time,
            observed_at=r.observed_at,
            location_tier=r.location_tier or "AREA_ONLY",
            anchor_method=r.anchor_method or "representative_point",
        )
        feats.append(feature(poly, props, fid=f"conflict:{r.source}:{r.source_event_id}"))
    if not feats:
        for i, c in enumerate(BUILTIN_CONFLICTS):
            poly = box(c["minLon"], c["minLat"], c["maxLon"], c["maxLat"])
            props = builtin_to_feature_properties(c, i)
            feats.append(feature(poly, props, fid=f"conflict:builtin:builtin_{i}"))
    return feature_collection(feats)

@router.get("/fuel/france")
def geo_fuel_france(db: Session = Depends(get_db), hours: int = Query(24, ge=1, le=24*14), fuel_type: str | None = None):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = select(FuelStationPrice).where(FuelStationPrice.provider == "france", FuelStationPrice.observed_at >= cutoff)
    if fuel_type:
        q = q.where(FuelStationPrice.fuel_type == fuel_type)
    rows = db.execute(q).scalars().all()
    feats = []
    for r in rows:
        pt = Point(r.lon, r.lat)
        country_name = _country_name_from_code(r.country)
        feats.append(feature(pt, {
            "provider": r.provider,
            "station_id": r.station_id,
            "country": r.country,
            "country_name": country_name,
            "fuel_type": r.fuel_type,
            "price_per_l": r.price_per_l,
            "currency": r.currency,
            "observed_at": r.observed_at.isoformat(),
        }, fid=f"fuel:{r.provider}:{r.station_id}:{r.fuel_type}:{int(r.observed_at.timestamp())}"))
    return feature_collection(feats)


@router.get("/cameras")
def geo_cameras(db: Session = Depends(get_db)):
    """Return cities with open IP cameras from database (persistent). Data is refreshed by ingest every 5 minutes."""
    rows = db.execute(select(IpCameraCity)).scalars().all()
    feats = []
    for r in rows:
        pt = Point(r.lon, r.lat)
        city_key = f"{r.city}-{r.country_code}"
        cameras = r.cameras if isinstance(r.cameras, list) else []
        feats.append(feature(pt, {
            "city": r.city,
            "country_code": r.country_code,
            "country_name": r.country_name or "",
            "count": len(cameras),
            "cameras": cameras,
        }, fid=f"camera_city:{city_key}"))
    result = feature_collection(feats)
    if len(feats) == 0 and settings.SHODAN_API_KEY:
        result["meta"] = {
            "message": "Shodan host search requires a paid membership (free API keys cannot use search). Upgrade at https://account.shodan.io",
        }
    return result
