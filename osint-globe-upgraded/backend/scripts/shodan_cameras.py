#!/usr/bin/env python3
"""
Standalone script to pull open IP cameras from Shodan using SHODAN_API_KEY from backend .env.
Outputs GeoJSON to stdout (same format as GET /geo/cameras). Run from project root or backend:

  cd backend && python scripts/shodan_cameras.py
  python -c "import sys; sys.path.insert(0, 'backend'); exec(open('backend/scripts/shodan_cameras.py').read())"
"""
import json
import sys
from pathlib import Path

# Ensure backend is on path so app.settings and app.shodan_cameras resolve
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from shapely.geometry import Point

from app.settings import settings
from app.shodan_cameras import fetch_cameras_from_shodan, DEFAULT_QUERY
from app.geojson import feature_collection, feature


def main():
    if not settings.SHODAN_API_KEY:
        print("SHODAN_API_KEY not set. Add it to backend/.env to use this script.", file=sys.stderr)
        sys.exit(1)
    try:
        rows = fetch_cameras_from_shodan(
            api_key=settings.SHODAN_API_KEY,
            query=DEFAULT_QUERY,
            max_results=300,
        )
    except Exception as e:
        print(f"Shodan request failed: {e}", file=sys.stderr)
        sys.exit(1)
    feats = []
    for r in rows:
        pt = Point(r["lon"], r["lat"])
        city_key = f"{r['city']}-{r['country_code']}"
        feats.append(feature(pt, {
            "city": r["city"],
            "country_code": r["country_code"],
            "country_name": r["country_name"],
            "count": len(r["cameras"]),
            "cameras": r["cameras"],
        }, fid=f"camera_city:{city_key}"))
    out = feature_collection(feats)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
