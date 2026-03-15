from shapely.geometry import shape

def anchor_for_geojson_geometry(geom_geojson: dict) -> tuple[float, float, str]:
    g = shape(geom_geojson)
    try:
        rp = g.representative_point()
        return (float(rp.x), float(rp.y), "representative_point")
    except Exception:
        c = g.centroid
        return (float(c.x), float(c.y), "centroid")
