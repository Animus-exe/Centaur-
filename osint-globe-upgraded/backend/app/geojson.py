from shapely.geometry import mapping
from shapely import wkt

def feature(geom, props: dict, fid: str | None = None):
    return {"type": "Feature", "id": fid, "geometry": mapping(geom) if geom is not None else None, "properties": props}

def feature_collection(features: list[dict]):
    return {"type": "FeatureCollection", "features": features}

def from_wkt(wkt_string: str | None):
    """Load a Shapely geometry from a WKT string (no PostGIS)."""
    if not wkt_string:
        return None
    return wkt.loads(wkt_string)
