"""
Built-in conflict zone definitions (fallback when UCDP is not configured or DB is empty).
Each entry has a bounding box and anchor for the label. When country_codes (ISO 3166-1 alpha-2)
is set, the frontend draws the actual country boundary from Natural Earth instead of the bbox.
"""

from datetime import datetime

# Entry: title, bbox (minLon, minLat, maxLon, maxLat), anchor (anchor_lon, anchor_lat),
# optional fatalities, optional country_codes (list of ISO A2; when set, frontend uses country shapes)
BUILTIN_CONFLICTS: list[dict] = [
    # Europe & Caucasus
    {"title": "Ukraine (conflict zone)", "minLon": 30.0, "minLat": 46.0, "maxLon": 40.0, "maxLat": 52.0, "anchor_lon": 35.0, "anchor_lat": 49.0, "fatalities": None, "country_codes": ["UA"]},
    {"title": "Nagorno-Karabakh / Armenia-Azerbaijan", "minLon": 45.5, "minLat": 39.2, "maxLon": 47.2, "maxLat": 40.2, "anchor_lon": 46.5, "anchor_lat": 39.7, "fatalities": None, "country_codes": ["AM", "AZ"]},
    # Middle East
    {"title": "Gaza Strip", "minLon": 34.2, "minLat": 31.2, "maxLon": 34.6, "maxLat": 31.6, "anchor_lon": 34.4, "anchor_lat": 31.4, "fatalities": None, "country_codes": None},
    {"title": "West Bank", "minLon": 34.9, "minLat": 31.3, "maxLon": 35.6, "maxLat": 32.6, "anchor_lon": 35.2, "anchor_lat": 32.0, "fatalities": None, "country_codes": None},
    {"title": "Syria (conflict zone)", "minLon": 35.5, "minLat": 32.3, "maxLon": 42.0, "maxLat": 37.3, "anchor_lon": 38.5, "anchor_lat": 35.0, "fatalities": None, "country_codes": ["SY"]},
    {"title": "Yemen (conflict zone)", "minLon": 43.0, "minLat": 12.5, "maxLon": 54.0, "maxLat": 19.0, "anchor_lon": 48.0, "anchor_lat": 15.5, "fatalities": None, "country_codes": ["YE"]},
    {"title": "Iraq (conflict-affected)", "minLon": 42.0, "minLat": 29.0, "maxLon": 48.5, "maxLat": 37.5, "anchor_lon": 44.0, "anchor_lat": 33.0, "fatalities": None, "country_codes": ["IQ"]},
    {"title": "Israel-Lebanon border", "minLon": 35.1, "minLat": 33.0, "maxLon": 35.7, "maxLat": 33.5, "anchor_lon": 35.4, "anchor_lat": 33.2, "fatalities": None, "country_codes": None},
    # Africa – Sahel & West
    {"title": "Sahel (Mali)", "minLon": -12.0, "minLat": 12.0, "maxLon": 4.0, "maxLat": 25.0, "anchor_lon": -4.0, "anchor_lat": 17.0, "fatalities": None, "country_codes": ["ML"]},
    {"title": "Burkina Faso (conflict zone)", "minLon": -5.5, "minLat": 10.5, "maxLon": 2.5, "maxLat": 15.0, "anchor_lon": -1.5, "anchor_lat": 12.5, "fatalities": None, "country_codes": ["BF"]},
    {"title": "Niger (conflict zone)", "minLon": 0.0, "minLat": 11.0, "maxLon": 14.0, "maxLat": 18.0, "anchor_lon": 8.0, "anchor_lat": 14.5, "fatalities": None, "country_codes": ["NE"]},
    {"title": "Nigeria (NE conflict zone)", "minLon": 10.0, "minLat": 10.0, "maxLon": 14.5, "maxLat": 13.5, "anchor_lon": 12.5, "anchor_lat": 11.5, "fatalities": None, "country_codes": None},
    {"title": "Cameroon (anglophone crisis)", "minLon": 8.8, "minLat": 5.5, "maxLon": 11.0, "maxLat": 7.0, "anchor_lon": 9.5, "anchor_lat": 6.2, "fatalities": None, "country_codes": ["CM"]},
    # Africa – Central & East
    {"title": "Libya (conflict zone)", "minLon": 9.0, "minLat": 24.0, "maxLon": 25.0, "maxLat": 33.0, "anchor_lon": 17.0, "anchor_lat": 28.5, "fatalities": None, "country_codes": ["LY"]},
    {"title": "Sudan (conflict zone)", "minLon": 22.0, "minLat": 9.0, "maxLon": 38.0, "maxLat": 22.0, "anchor_lon": 30.0, "anchor_lat": 15.0, "fatalities": None, "country_codes": ["SD"]},
    {"title": "South Sudan", "minLon": 24.0, "minLat": 3.5, "maxLon": 36.0, "maxLat": 12.0, "anchor_lon": 30.0, "anchor_lat": 7.5, "fatalities": None, "country_codes": ["SS"]},
    {"title": "DRC (eastern conflict zone)", "minLon": 26.0, "minLat": -5.0, "maxLon": 31.0, "maxLat": 2.0, "anchor_lon": 28.5, "anchor_lat": -1.5, "fatalities": None, "country_codes": None},
    {"title": "Central African Republic", "minLon": 14.0, "minLat": 4.0, "maxLon": 27.0, "maxLat": 11.0, "anchor_lon": 20.5, "anchor_lat": 7.0, "fatalities": None, "country_codes": ["CF"]},
    {"title": "Somalia (conflict zone)", "minLon": 41.0, "minLat": -1.5, "maxLon": 51.0, "maxLat": 12.0, "anchor_lon": 46.0, "anchor_lat": 5.0, "fatalities": None, "country_codes": ["SO"]},
    {"title": "Ethiopia (conflict-affected)", "minLon": 35.0, "minLat": 4.0, "maxLon": 48.0, "maxLat": 14.0, "anchor_lon": 40.0, "anchor_lat": 9.0, "fatalities": None, "country_codes": ["ET"]},
    {"title": "Mozambique (Cabo Delgado)", "minLon": 38.0, "minLat": -12.0, "maxLon": 41.0, "maxLat": -10.0, "anchor_lon": 39.5, "anchor_lat": -11.0, "fatalities": None, "country_codes": ["MZ"]},
    {"title": "Chad (conflict-affected)", "minLon": 13.0, "minLat": 8.0, "maxLon": 24.0, "maxLat": 23.0, "anchor_lon": 18.0, "anchor_lat": 15.0, "fatalities": None, "country_codes": ["TD"]},
    # Asia
    {"title": "Afghanistan (conflict zone)", "minLon": 60.5, "minLat": 29.5, "maxLon": 74.5, "maxLat": 38.5, "anchor_lon": 67.0, "anchor_lat": 34.0, "fatalities": None, "country_codes": ["AF"]},
    {"title": "Kashmir (conflict zone)", "minLon": 73.5, "minLat": 33.0, "maxLon": 78.5, "maxLat": 36.0, "anchor_lon": 76.0, "anchor_lat": 34.5, "fatalities": None, "country_codes": None},
    {"title": "Pakistan (Balochistan/KPK)", "minLon": 61.0, "minLat": 25.0, "maxLon": 74.0, "maxLat": 35.0, "anchor_lon": 67.0, "anchor_lat": 30.0, "fatalities": None, "country_codes": ["PK"]},
    {"title": "Myanmar (conflict zone)", "minLon": 92.0, "minLat": 15.0, "maxLon": 101.0, "maxLat": 28.0, "anchor_lon": 96.5, "anchor_lat": 21.5, "fatalities": None, "country_codes": ["MM"]},
    {"title": "Philippines (Mindanao)", "minLon": 121.5, "minLat": 5.5, "maxLon": 126.5, "maxLat": 10.0, "anchor_lon": 124.0, "anchor_lat": 7.5, "fatalities": None, "country_codes": None},
    # Americas
    {"title": "Colombia (conflict-affected)", "minLon": -79.0, "minLat": -4.0, "maxLon": -66.0, "maxLat": 12.0, "anchor_lon": -73.0, "anchor_lat": 4.0, "fatalities": None, "country_codes": ["CO"]},
    {"title": "Haiti (gang violence)", "minLon": -74.5, "minLat": 18.0, "maxLon": -71.5, "maxLat": 20.0, "anchor_lon": -72.5, "anchor_lat": 19.0, "fatalities": None, "country_codes": ["HT"]},
    {"title": "Mexico (cartel conflict zones)", "minLon": -117.0, "minLat": 14.0, "maxLon": -86.0, "maxLat": 32.5, "anchor_lon": -100.0, "anchor_lat": 23.0, "fatalities": None, "country_codes": None},
]


def conflict_feature_properties(
    *,
    title: str,
    category: str = "conflict",
    anchor_lon: float,
    anchor_lat: float,
    fatalities: int | None = None,
    source: str = "builtin",
    source_event_id: str = "",
    source_url: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    observed_at: datetime | None = None,
    location_tier: str = "AREA_ONLY",
    anchor_method: str = "builtin",
    country_codes: list[str] | None = None,
) -> dict:
    """Build a single GeoJSON feature properties dict for a conflict area (shared shape for DB and builtin)."""
    out = {
        "title": title,
        "category": category,
        "anchor_lon": float(anchor_lon),
        "anchor_lat": float(anchor_lat),
        "fatalities": fatalities,
        "source": source,
        "source_event_id": source_event_id,
        "source_url": source_url,
        "start_time": start_time.isoformat() if start_time else None,
        "end_time": end_time.isoformat() if end_time else None,
        "observed_at": observed_at.isoformat() if observed_at else None,
        "location_tier": location_tier,
        "anchor_method": anchor_method,
    }
    if country_codes is not None:
        out["country_codes"] = country_codes
    return out


def builtin_to_feature_properties(c: dict, index: int) -> dict:
    """Convert one builtin conflict dict to feature properties."""
    return conflict_feature_properties(
        title=c["title"],
        anchor_lon=c["anchor_lon"],
        anchor_lat=c["anchor_lat"],
        fatalities=c.get("fatalities"),
        source="builtin",
        source_event_id=f"builtin_{index}",
        source_url=None,
        observed_at=None,
        location_tier="AREA_ONLY",
        anchor_method="builtin",
        country_codes=c.get("country_codes"),
    )
