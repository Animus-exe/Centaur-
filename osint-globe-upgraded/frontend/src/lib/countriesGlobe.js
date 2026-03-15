import * as Cesium from "cesium";

const COUNTRIES_GEOJSON_URL =
  "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson";

function polygonCentroid(outerCartesians) {
  const n = outerCartesians.length;
  if (n === 0) return null;
  let sumX = 0,
    sumY = 0,
    sumZ = 0;
  for (let i = 0; i < n; i++) {
    const c = outerCartesians[i];
    sumX += c.x;
    sumY += c.y;
    sumZ += c.z;
  }
  const cartesian = new Cesium.Cartesian3(sumX / n, sumY / n, sumZ / n);
  const carto = Cesium.Cartographic.fromCartesian(cartesian);
  return {
    lon: Cesium.Math.toDegrees(carto.longitude),
    lat: Cesium.Math.toDegrees(carto.latitude)
  };
}

function getCountryName(properties) {
  if (!properties) return "Country";
  return (
    properties.NAME ||
    properties.name ||
    properties.ADMIN ||
    properties.admin ||
    properties.COUNTRY ||
    properties.country ||
    "Country"
  );
}

/**
 * Add country boundaries (outlines) and country name labels to the Cesium globe.
 * Loads Natural Earth 110m countries GeoJSON and creates one boundary entity + one label per country.
 */
export async function addCountryBoundariesAndLabels(viewer) {
  const prefix = "country:";
  const labelPrefix = "country_label:";

  let geojson;
  try {
    const res = await fetch(COUNTRIES_GEOJSON_URL);
    if (!res.ok) throw new Error(res.statusText);
    geojson = await res.json();
  } catch (err) {
    console.warn("Countries GeoJSON load failed:", err);
    return;
  }

  const features = geojson.features || [];
  const boundaryColor = new Cesium.Color(0.85, 0.9, 0.95, 0.9);
  const labelFill = Cesium.Color.WHITE;
  const labelOutline = new Cesium.Color(0.05, 0.05, 0.12, 1);

  for (let i = 0; i < features.length; i++) {
    const f = features[i];
    const props = f.properties || {};
    const geom = f.geometry;
    const name = getCountryName(props);

    let rings;
    if (geom.type === "Polygon") {
      rings = [geom.coordinates];
    } else if (geom.type === "MultiPolygon") {
      rings = geom.coordinates;
    } else {
      continue;
    }

    let firstCentroid = null;

    // Draw boundary for every part (main landmass + islands)
    for (let r = 0; r < rings.length; r++) {
      const outer = rings[r][0].map(([lon, lat]) =>
        Cesium.Cartesian3.fromDegrees(lon, lat, 0)
      );
      const hierarchy = new Cesium.PolygonHierarchy(outer);
      const id = r === 0 ? (f.id ?? `${prefix}${i}`) : `${prefix}${i}_${r}`;

      viewer.entities.add({
        id,
        name,
        polygon: {
          hierarchy,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          outline: true,
          outlineColor: boundaryColor,
          outlineWidth: 1.5,
          fill: false,
          perPositionHeight: false
        },
        show: true
      });

      if (r === 0) firstCentroid = polygonCentroid(outer);
    }

    // One label per country at centroid of first polygon
    if (firstCentroid) {
      const id = f.id ?? `${prefix}${i}`;
      viewer.entities.add({
        id: `${labelPrefix}${id}`,
        position: Cesium.Cartesian3.fromDegrees(
          firstCentroid.lon,
          firstCentroid.lat,
          0
        ),
        label: {
          text: name,
          font: "14px sans-serif",
          fillColor: labelFill,
          outlineColor: labelOutline,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.CENTER,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          scaleByDistance: new Cesium.NearFarScalar(2e5, 1.2, 1e7, 0.4),
          disableDepthTestDistance: Number.POSITIVE_INFINITY
        },
        show: true
      });
    }
  }
}
