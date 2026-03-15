from datetime import datetime, timezone
import base64
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sqlalchemy.orm import Session
from sqlalchemy import select, func, text

from ..models import FlightState, FlightTrackPoint
from ..logging_util import log
from ..settings import settings
from .util_http import get_client, get_with_retry

# Longer timeout for airplanes.live (often slow or far away)
AIRPLANES_LIVE_TIMEOUT = 60.0
# API max radius (nm); use multiple points per AOI to cover the whole world
AIRPLANES_LIVE_MAX_RADIUS_NM = 250
OPENSKY_FALLBACK_URL = "https://opensky-network.org/api/states/all"
OPENSKY_FALLBACK_URL_EXTENDED = "https://opensky-network.org/api/states/all?extended=1"
INGEST_ADVISORY_LOCK_KEY = 841720319
_opensky_last_attempt_ts: float = 0.0
_opensky_cooldown_until_ts: float = 0.0
_opensky_cached_payload: dict | None = None


def _opensky_auth_headers() -> dict[str, str]:
    """
    Build Basic Auth headers for OpenSky when credentials are configured.
    OpenSky allows anonymous access but authenticated requests have better limits.
    """
    username = (settings.OPENSKY_USERNAME or "").strip()
    password = settings.OPENSKY_PASSWORD or ""
    if not username or not password:
        return {}
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _has_opensky_auth() -> bool:
    return bool((settings.OPENSKY_USERNAME or "").strip() and (settings.OPENSKY_PASSWORD or ""))


def _opensky_min_poll_seconds() -> int:
    if _has_opensky_auth():
        return settings.OPENSKY_MIN_POLL_SECONDS_AUTH
    return settings.OPENSKY_MIN_POLL_SECONDS_ANON


def _opensky_cooldown_seconds() -> int:
    if _has_opensky_auth():
        return settings.OPENSKY_RATE_LIMIT_COOLDOWN_SECONDS_AUTH
    return settings.OPENSKY_RATE_LIMIT_COOLDOWN_SECONDS_ANON


def get_opensky_rate_limit_status() -> dict:
    """Return current OpenSky rate-limit and auth state for status API."""
    import time
    now = time.time()
    cooldown_until = _opensky_cooldown_until_ts if now < _opensky_cooldown_until_ts else None
    return {
        "opensky_authenticated": _has_opensky_auth(),
        "rate_limited": cooldown_until is not None,
        "rate_limited_until_iso": datetime.fromtimestamp(_opensky_cooldown_until_ts, tz=timezone.utc).isoformat() if cooldown_until else None,
        "international_coverage": True,  # OpenSky states/all is global; AOIs default to worldwide
    }


def _base_url():
    from ..settings import settings
    # Default HTTP: works from more networks; set AIRPLANES_LIVE_BASE_URL for HTTPS if desired
    return (settings.AIRPLANES_LIVE_BASE_URL or "http://api.airplanes.live/v2").rstrip("/")


def _safe_float(val):
    """Convert to float; return None for non-numeric values (e.g. API returns 'ground' for altitude)."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

# Fallback when HTTPS is unreachable (e.g. SSL or network issues)
AIRPLANES_LIVE_HTTP_FALLBACK = "http://api.airplanes.live/v2"

def _grid_centers_for_aoi(aoi: dict, radius_nm: int) -> list[tuple[float, float]]:
    """Return (lat, lon) centers so circles of radius_nm nm cover the AOI box. API max radius 250 nm."""
    min_lat = aoi["minLat"]
    max_lat = aoi["maxLat"]
    min_lon = aoi["minLon"]
    max_lon = aoi["maxLon"]
    # ~1 deg lat ≈ 60 nm; 1 deg lon ≈ 60*cos(lat) nm. Step so diameter 2*radius covers with overlap
    step_deg = (radius_nm * 2 * 0.85) / 60.0  # degrees, slight overlap
    step_deg = max(1.5, min(step_deg, 8.0))
    centers = []
    lat = min_lat + step_deg / 2
    while lat <= max_lat:
        lon = min_lon + step_deg / 2
        while lon <= max_lon:
            centers.append((lat, lon))
            lon += step_deg
        lat += step_deg
    if not centers:
        centers = [((min_lat + max_lat) / 2, (min_lon + max_lon) / 2)]
    return centers


def _ingest_opensky_global(db: Session, client, observed_at: datetime) -> int:
    """Fallback ingest using OpenSky global state vectors when airplanes.live is unavailable."""
    global _opensky_last_attempt_ts, _opensky_cooldown_until_ts, _opensky_cached_payload
    import time

    last_opensky_observed = db.execute(
        select(func.max(FlightState.observed_at)).where(FlightState.source == "opensky")
    ).scalar_one_or_none()

    now_ts = time.time()
    if now_ts < _opensky_cooldown_until_ts:
        if _opensky_cached_payload:
            payload = _opensky_cached_payload
        else:
            return 0
    else:
        payload = None

    if payload is None and last_opensky_observed is not None:
        age_seconds = (observed_at - last_opensky_observed).total_seconds()
        if age_seconds < _opensky_min_poll_seconds():
            # Fresh enough; avoid refetching too often from OpenSky.
            return 0

    recently_attempted = (now_ts - _opensky_last_attempt_ts) < _opensky_min_poll_seconds()
    if recently_attempted and _opensky_cached_payload:
        payload = _opensky_cached_payload
    elif recently_attempted:
        return 0
    else:
        _opensky_last_attempt_ts = now_ts
        payload = payload or {}
        auth_headers = _opensky_auth_headers()
        try:
            # In some environments, direct stdlib HTTPS fetch is more reliable than the shared HTTP client.
            # extended=1 returns category at index 17 (e.g. 14 = UAV) for military classification.
            req = Request(OPENSKY_FALLBACK_URL_EXTENDED, headers=auth_headers)
            with urlopen(req, timeout=30) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                cooldown_s = _opensky_cooldown_seconds()
                _opensky_cooldown_until_ts = now_ts + cooldown_s
                log(
                    "flights_opensky_rate_limited",
                    url=OPENSKY_FALLBACK_URL_EXTENDED,
                    cooldown_seconds=cooldown_s,
                    mode="auth" if auth_headers else "anonymous",
                )
                # Avoid double-hitting OpenSky in the same cycle after a hard 429.
                if _opensky_cached_payload:
                    payload = _opensky_cached_payload
                else:
                    return 0
            elif e.code in (401, 403) and auth_headers:
                log("flights_opensky_auth_failed", url=OPENSKY_FALLBACK_URL_EXTENDED, status_code=e.code)
            else:
                log("flights_opensky_urlopen_failed", url=OPENSKY_FALLBACK_URL_EXTENDED, error=str(e)[:500])
        except Exception as e:
            log("flights_opensky_urlopen_failed", url=OPENSKY_FALLBACK_URL_EXTENDED, error=str(e)[:500])

        if not payload:
            try:
                r = get_with_retry(OPENSKY_FALLBACK_URL_EXTENDED, client, extra_headers=auth_headers)
            except RuntimeError as e:
                log("flights_opensky_get_failed", url=OPENSKY_FALLBACK_URL_EXTENDED, error=str(e)[:500])
                if _opensky_cached_payload:
                    payload = _opensky_cached_payload
                else:
                    return 0
            else:
                if r is None or r.status_code != 200:
                    if _opensky_cached_payload:
                        payload = _opensky_cached_payload
                    else:
                        return 0
                else:
                    payload = r.json() or {}

        if payload.get("states"):
            _opensky_cached_payload = payload

    states = payload.get("states") or []
    if not states:
        return 0

    existing_rows = db.execute(select(FlightState)).scalars().all()
    existing_by_icao = {row.icao24: row for row in existing_rows}
    inserted = 0

    for row in states:
        if not isinstance(row, list) or len(row) < 17:
            continue
        icao24 = (row[0] or "").strip().lower()
        callsign = (row[1] or "").strip() or None
        lon_f = _safe_float(row[5])
        lat_f = _safe_float(row[6])
        alt_f = _safe_float(row[7] if row[7] is not None else row[13])
        velocity_mps = _safe_float(row[9])
        hdg_f = _safe_float(row[10])
        if not icao24 or lat_f is None or lon_f is None:
            continue

        last_contact = row[4]
        ts = observed_at
        if isinstance(last_contact, (int, float)) and last_contact > 0:
            try:
                ts = datetime.fromtimestamp(float(last_contact), tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                ts = observed_at

        raw = {
            "icao24": icao24,
            "callsign": callsign,
            "lon": lon_f,
            "lat": lat_f,
            "altitude_m": alt_f,
            "velocity_mps": velocity_mps,
            "heading_deg": hdg_f,
            "provider": "opensky",
            "state_vector": row,
        }
        if len(row) > 2 and row[2]:
            raw["origin_country"] = row[2]
        if len(row) > 17 and row[17] is not None:
            raw["category"] = row[17]

        existing = existing_by_icao.get(icao24)
        if existing:
            existing.callsign = callsign
            existing.lat = lat_f
            existing.lon = lon_f
            existing.altitude_m = alt_f
            existing.velocity_mps = velocity_mps
            existing.heading_deg = hdg_f
            existing.observed_at = ts
            existing.source = "opensky"
            existing.raw = raw
        else:
            existing = FlightState(
                icao24=icao24,
                callsign=callsign,
                lat=lat_f,
                lon=lon_f,
                altitude_m=alt_f,
                velocity_mps=velocity_mps,
                heading_deg=hdg_f,
                observed_at=ts,
                source="opensky",
                raw=raw,
            )
            db.add(existing)
            existing_by_icao[icao24] = existing

        db.add(FlightTrackPoint(
            icao24=icao24, callsign=callsign,
            ts=ts,
            altitude_m=alt_f,
            velocity_mps=velocity_mps,
            heading_deg=hdg_f,
            lat=lat_f, lon=lon_f,
            source="opensky", raw=raw
        ))
        inserted += 1

    return inserted


def ingest_flights_airplanes_live(db: Session, aois: list[dict]) -> int:
    if not aois: return 0
    import time
    lock_acquired = bool(
        db.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": INGEST_ADVISORY_LOCK_KEY},
        ).scalar()
    )
    if not lock_acquired:
        log("flights_ingest_lock_busy", message="another instance is already polling")
        return 0

    try:
        client = get_client(timeout=AIRPLANES_LIVE_TIMEOUT)
        observed_at = datetime.now(timezone.utc)

        # Primary global feed: OpenSky provides worldwide state vectors in one call.
        opensky_count = _ingest_opensky_global(db, client, observed_at)
        if opensky_count > 0:
            db.commit()
            log("flights_primary_used", provider="opensky", item_count=opensky_count)
            return opensky_count

        latest_row = db.execute(
            select(FlightState.observed_at, FlightState.source)
            .order_by(FlightState.observed_at.desc())
            .limit(1)
        ).first()
        if latest_row is not None:
            latest_observed, latest_source = latest_row
            age_seconds = (observed_at - latest_observed).total_seconds()
            if latest_source == "opensky" and age_seconds < settings.FLIGHTS_STALE_AFTER_SECONDS:
                # Fresh OpenSky data exists; avoid unnecessary secondary polling.
                return 0

        inserted = 0
        base = _base_url()
        radius_nm = AIRPLANES_LIVE_MAX_RADIUS_NM  # 250 nm max; grid covers whole world

        for aoi_idx, aoi in enumerate(aois):
            centers = _grid_centers_for_aoi(aoi, radius_nm)
            for pt_idx, (center_lat, center_lon) in enumerate(centers):
                if aoi_idx > 0 or pt_idx > 0:
                    time.sleep(1.2)  # airplanes.live rate limit: ~1 req/s
                path = f"/point/{center_lat:.5f}/{center_lon:.5f}/{radius_nm}"
                url = f"{base}{path}"
                url_http = f"{AIRPLANES_LIVE_HTTP_FALLBACK}{path}"
                r = None
                try:
                    if base.startswith("https://"):
                        try:
                            r = get_with_retry(url_http, client)
                        except RuntimeError as e:
                            log("flights_airplanes_live_get_failed", url=url_http, error=str(e)[:500])
                            try:
                                r = get_with_retry(url, client)
                            except RuntimeError as e2:
                                log("flights_airplanes_live_get_failed", url=url, error=str(e2)[:500])
                                raise
                    else:
                        try:
                            r = get_with_retry(url, client)
                        except RuntimeError as e:
                            log("flights_airplanes_live_get_failed", url=url, error=str(e)[:500])
                            raise
                except RuntimeError:
                    log("flights_airplanes_live_unreachable", url=url, message="skipping point and continuing")
                    continue
                if r is None or r.status_code != 200:
                    continue
                observed_at = datetime.now(timezone.utc)
                data = r.json()
                aircraft = data.get("ac", []) or data.get("aircraft", []) or []
                for ac in aircraft:
                    icao24 = (ac.get("hex") or ac.get("icao") or "").strip()
                    if not icao24: continue
                    lat = ac.get("lat"); lon = ac.get("lon")
                    if lat is None or lon is None: continue
                    lat_f = _safe_float(lat); lon_f = _safe_float(lon)
                    if lat_f is None or lon_f is None: continue

                    callsign = (ac.get("flight") or ac.get("callsign") or "").strip() or None
                    alt = ac.get("alt_baro") or ac.get("alt_geom") or ac.get("altitude")
                    spd = ac.get("gs") or ac.get("speed")  # knots
                    hdg = ac.get("track") or ac.get("heading")

                    alt_f = _safe_float(alt)
                    spd_f = _safe_float(spd)
                    hdg_f = _safe_float(hdg)
                    velocity_mps = (spd_f * 0.514444) if spd_f is not None else None

                    existing = db.execute(select(FlightState).where(FlightState.icao24 == icao24)).scalar_one_or_none()
                    if existing:
                        existing.callsign = callsign
                        existing.lat = lat_f; existing.lon = lon_f
                        existing.altitude_m = alt_f
                        existing.velocity_mps = velocity_mps
                        existing.heading_deg = hdg_f
                        existing.observed_at = observed_at
                        existing.source = "airplanes.live"
                        existing.raw = ac
                    else:
                        db.add(FlightState(
                            icao24=icao24, callsign=callsign,
                            lat=lat_f, lon=lon_f,
                            altitude_m=alt_f,
                            velocity_mps=velocity_mps,
                            heading_deg=hdg_f,
                            observed_at=observed_at, source="airplanes.live", raw=ac
                        ))

                    db.add(FlightTrackPoint(
                        icao24=icao24, callsign=callsign,
                        ts=observed_at,
                        altitude_m=alt_f,
                        velocity_mps=velocity_mps,
                        heading_deg=hdg_f,
                        lat=lat_f, lon=lon_f,
                        source="airplanes.live", raw=ac
                    ))
                    inserted += 1

        db.commit()
        return inserted
    finally:
        try:
            db.execute(
                text("SELECT pg_advisory_unlock(:key)"),
                {"key": INGEST_ADVISORY_LOCK_KEY},
            )
        except Exception as e:
            log("flights_ingest_unlock_failed", error=str(e)[:500])
