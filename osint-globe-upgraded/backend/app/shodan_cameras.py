"""
Fetch open IP cameras from Shodan API and aggregate by city for the globe layer.
- Streaming API (free key): connect to port 554 stream, collect banners for N seconds.
- Search API (paid): optional fallback with query port:554.
"""
from __future__ import annotations

import json
import time
import httpx

SHODAN_SEARCH_URL = "https://api.shodan.io/shodan/host/search"
SHODAN_STREAM_PORTS_URL = "https://stream.shodan.io/shodan/ports/{ports}"
# Default query: RTSP port commonly used by IP cameras
DEFAULT_QUERY = "port:554"
PAGE_SIZE = 100
# How long to collect from stream (seconds) when using stream API
STREAM_COLLECT_SECONDS = 60
STREAM_MAX_CAMERAS = 500


def _make_link(ip: str, port: int) -> str:
    """Build a link to open the stream (RTSP for 554, else HTTP)."""
    if port == 554:
        return f"rtsp://{ip}:{port}"
    return f"http://{ip}:{port}"


def _city_key(loc: dict) -> tuple[str, str]:
    """Return (city, country_code) for grouping; use fallback if city missing."""
    city = (loc.get("city") or "").strip() or "Unknown"
    country = (loc.get("country_code") or "").strip() or "XX"
    return (city, country)


def _fallback_key(lat: float | None, lon: float | None) -> tuple[str, str]:
    """When city is missing, use rounded lat/lon as a synthetic place key."""
    if lat is None or lon is None:
        return ("Unknown", "XX")
    return (f"_{round(lat, 2)}_{round(lon, 2)}", "XX")


def _banner_to_camera_entry(banner: dict) -> tuple[str, str, str, float | None, float | None, dict]:
    """Extract (city, country_code, country_name, lat, lon, camera_dict) from a stream banner."""
    loc = banner.get("location") or {}
    city, country_code = _city_key(loc)
    if city == "Unknown" and (loc.get("latitude") is not None and loc.get("longitude") is not None):
        city, _ = _fallback_key(loc.get("latitude"), loc.get("longitude"))
    country_name = (loc.get("country_name") or "").strip() or country_code
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    ip_str = banner.get("ip_str") or ""
    port = banner.get("port")
    product = (banner.get("product") or "").strip() or None
    cam = {"ip": ip_str, "port": port, "product": product, "link": _make_link(ip_str, port or 554)}
    return (city, country_code, country_name, lat, lon, cam)


def fetch_cameras_from_shodan_stream(
    api_key: str,
    ports: str = "554",
    collect_seconds: int = STREAM_COLLECT_SECONDS,
    max_cameras: int = STREAM_MAX_CAMERAS,
) -> list[dict]:
    """
    Consume Shodan's port stream (works with free API key), collect banners for a limited time,
    aggregate by city, and return same shape as fetch_cameras_from_shodan.
    """
    aggregated: dict[tuple[str, str], dict] = {}
    collected = 0
    url = SHODAN_STREAM_PORTS_URL.format(ports=ports)
    deadline = time.monotonic() + collect_seconds

    with httpx.Client(timeout=httpx.Timeout(collect_seconds + 60)) as client:
        for _ in range(3):
            with client.stream("GET", url, params={"key": api_key}) as r:
                if r.status_code == 429:
                    time.sleep(2.0)
                    continue
                if r.status_code != 200:
                    body = b"".join(r.iter_bytes()).decode("utf-8", errors="replace")[:500]
                    raise httpx.HTTPStatusError(
                        f"Stream returned {r.status_code}: {body}",
                        request=r.request,
                        response=r,
                    )
                for line in r.iter_lines():
                    if time.monotonic() >= deadline or collected >= max_cameras:
                        break
                    line = line.strip()
                    if not line or (line.startswith("{") and '"event"' in line and '"debug"' in line):
                        continue
                    try:
                        banner = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(banner, dict):
                        continue
                    ip_str = banner.get("ip_str")
                    port = banner.get("port")
                    if not ip_str or port is None:
                        continue
                    city, country_code, country_name, lat, lon, cam = _banner_to_camera_entry(banner)
                    key = (city, country_code)
                    if key not in aggregated:
                        aggregated[key] = {
                            "city": city,
                            "country_code": country_code,
                            "country_name": country_name,
                            "lat": lat,
                            "lon": lon,
                            "cameras": [],
                        }
                    agg = aggregated[key]
                    if agg["lat"] is None and lat is not None:
                        agg["lat"] = lat
                    if agg["lon"] is None and lon is not None:
                        agg["lon"] = lon
                    agg["cameras"].append(cam)
                    collected += 1
            break
        else:
            raise httpx.HTTPStatusError(
                "Stream rate limited (429) after retries",
                request=httpx.Request("GET", url),
                response=None,
            )

    result = []
    for (city, country_code), agg in aggregated.items():
        lat, lon = agg.get("lat"), agg.get("lon")
        if lat is None or lon is None:
            continue
        result.append({
            "city": agg["city"],
            "country_code": agg["country_code"],
            "country_name": agg["country_name"],
            "lon": float(lon),
            "lat": float(lat),
            "cameras": agg["cameras"],
        })
    return result


def fetch_cameras_from_shodan(
    api_key: str,
    query: str = DEFAULT_QUERY,
    max_results: int = 300,
) -> list[dict]:
    """
    Query Shodan for hosts matching the search, aggregate by city, return
    list of dicts: city, country_code, country_name, lon, lat, cameras.
    """
    aggregated: dict[tuple[str, str], list[dict]] = {}
    page = 1
    collected = 0

    with httpx.Client(timeout=30.0) as client:
        while collected < max_results:
            resp = client.get(
                SHODAN_SEARCH_URL,
                params={"key": api_key, "query": query, "page": page},
            )
            resp.raise_for_status()
            data = resp.json()
            matches = data.get("matches") or []
            if not matches:
                break

            for m in matches:
                if collected >= max_results:
                    break
                ip_str = m.get("ip_str")
                port = m.get("port")
                if not ip_str or port is None:
                    continue
                loc = m.get("location") or {}
                lat = loc.get("latitude")
                lon = loc.get("longitude")
                city, country_code = _city_key(loc)
                if city == "Unknown" and (lat is not None and lon is not None):
                    city, _ = _fallback_key(lat, lon)
                country_name = (loc.get("country_name") or "").strip() or country_code
                product = (m.get("product") or "").strip() or None

                key = (city, country_code)
                if key not in aggregated:
                    aggregated[key] = {
                        "city": city,
                        "country_code": country_code,
                        "country_name": country_name,
                        "lat": lat,
                        "lon": lon,
                        "cameras": [],
                    }
                agg = aggregated[key]
                if agg["lat"] is None and lat is not None:
                    agg["lat"] = lat
                if agg["lon"] is None and lon is not None:
                    agg["lon"] = lon
                agg["cameras"].append({
                    "ip": ip_str,
                    "port": port,
                    "product": product,
                    "link": _make_link(ip_str, port),
                })
                collected += 1

            if len(matches) < PAGE_SIZE:
                break
            page += 1

    # Drop cities without valid coordinates for the globe
    result = []
    for (city, country_code), agg in aggregated.items():
        lat, lon = agg.get("lat"), agg.get("lon")
        if lat is None or lon is None:
            continue
        result.append({
            "city": agg["city"],
            "country_code": agg["country_code"],
            "country_name": agg["country_name"],
            "lon": float(lon),
            "lat": float(lat),
            "cameras": agg["cameras"],
        })
    return result
