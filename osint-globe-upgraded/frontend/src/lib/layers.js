import * as Cesium from "cesium";

const COUNTRIES_GEOJSON_URL =
  "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson";
let cachedCountriesGeojson = null;

async function getCountriesGeojson() {
  if (cachedCountriesGeojson) return cachedCountriesGeojson;
  try {
    const res = await fetch(COUNTRIES_GEOJSON_URL);
    if (!res.ok) throw new Error(res.statusText);
    cachedCountriesGeojson = await res.json();
    return cachedCountriesGeojson;
  } catch (err) {
    console.warn("Countries GeoJSON load failed:", err);
    return null;
  }
}

function getIsoA2(props) {
  if (!props) return null;
  const code = props.ISO_A2 ?? props.iso_a2 ?? props.ISO_A2_EH;
  return code && String(code).trim() !== "" && String(code) !== "-99" ? String(code).toUpperCase() : null;
}

function isValidPointCoords(coords) {
  if (!Array.isArray(coords) || coords.length < 2) return false;
  const lon = coords[0], lat = coords[1];
  return typeof lon === "number" && typeof lat === "number" && Number.isFinite(lon) && Number.isFinite(lat);
}

function metersToFeet(m) {
  if (typeof m !== "number" || !Number.isFinite(m)) return "—";
  return Math.round(m * 3.28084).toLocaleString() + " ft";
}
function mpsToKnots(mps) {
  if (typeof mps !== "number" || !Number.isFinite(mps)) return "—";
  return Math.round(mps * 1.94384) + " kt";
}

function escHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatFieldValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) {
    return value.length > 0 ? value.join(", ") : "—";
  }
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "—";
  if (typeof value === "object") return escHtml(JSON.stringify(value));
  return escHtml(String(value));
}

function renderFieldRow(label, value) {
  return `<tr><td style="padding:3px 10px 3px 0;color:#9eb0c7;vertical-align:top;white-space:nowrap;">${escHtml(label)}</td><td style="padding:3px 0;color:#e4ebf5;">${formatFieldValue(value)}</td></tr>`;
}

// Plane overlay: soft amber for military, off-white for civilian
const PLANE_MILITARY_COLOR = new Cesium.Color(0.92, 0.72, 0.32, 0.98);
const PLANE_CIVILIAN_COLOR = new Cesium.Color(0.96, 0.97, 0.98, 0.95);
const PLANE_MIL_LABEL_COLOR = new Cesium.Color(0.9, 0.7, 0.35, 0.95);
const PLANE_MIL_LABEL_OUTLINE = new Cesium.Color(0.12, 0.1, 0.06, 0.9);

function buildFlightDescription(p, labelText, headingDeg, isMilitary) {
  const rows = [];
  rows.push(renderFieldRow("Callsign", labelText));
  rows.push(renderFieldRow("ICAO24", p.icao24));
  rows.push(renderFieldRow("Country", p.country_name ?? p.country_code));
  rows.push(renderFieldRow("Latitude", p.lat));
  rows.push(renderFieldRow("Longitude", p.lon));
  rows.push(renderFieldRow("Altitude", metersToFeet(p.altitude_m)));
  rows.push(renderFieldRow("Speed", mpsToKnots(p.velocity_mps)));
  rows.push(renderFieldRow("Heading", headingDeg != null ? `${Math.round(headingDeg)}°` : "—"));
  rows.push(renderFieldRow("Observed", p.observed_at));
  rows.push(renderFieldRow("Source", p.source));
  rows.push(renderFieldRow("Stale", p.stale));
  rows.push(renderFieldRow("Likely military", p.likely_military));
  rows.push(renderFieldRow("Military confidence", p.military_confidence));
  rows.push(renderFieldRow("Military reasons", p.military_reasons));

  const raw = p.raw && typeof p.raw === "object" ? p.raw : {};
  const rawJson = escHtml(JSON.stringify(raw, null, 2));
  const badge = isMilitary ? '<span style="color:#d4a84b;">Military aircraft</span>' : '<span style="color:#b4c4d8;">Civilian aircraft</span>';

  return `<div style="max-width:420px;padding:10px;background:rgba(18,22,30,0.94);border:1px solid rgba(60,75,100,0.5);border-radius:8px;color:#e0e6ef;font-size:13px;line-height:1.45;">
    <div style="margin-bottom:6px;font-weight:600;">${badge}</div>
    <table style="width:100%;border-collapse:collapse;">${rows.join("")}</table>
    <details style="margin-top:8px;">
      <summary style="cursor:pointer;color:#9eb0c7;">Raw source data</summary>
      <pre style="margin-top:6px;padding:8px;max-height:180px;overflow:auto;background:rgba(0,0,0,0.3);border:1px solid rgba(80,96,120,0.35);border-radius:6px;color:#dbe5f3;">${rawJson}</pre>
    </details>
  </div>`;
}

export async function upsertFlights(viewer, geojson) {
  const prefix = "flight:";
  const toRemove = [...viewer.entities.values].filter(e => (e.id || "").startsWith(prefix));
  toRemove.forEach(e => viewer.entities.remove(e));
  for (const f of geojson.features || []) {
    const coords = f.geometry?.coordinates;
    if (!isValidPointCoords(coords)) continue;
    const [lon, lat] = coords;
    const p = f.properties || {};
    const altM = typeof p.altitude_m === "number" && p.altitude_m > 0 ? p.altitude_m : 0;
    const headingDeg = typeof p.heading_deg === "number" && Number.isFinite(p.heading_deg) ? p.heading_deg : null;
    const labelText = (p.callsign && String(p.callsign).trim()) || p.icao24 || "—";
    const confidence = Number(p.military_confidence ?? 0);
    const isMilitary = p.military_display === true || p.likely_military === true || confidence >= 40;
    const entity = {
      id: f.id,
      name: isMilitary ? `\u2694 ${labelText}` : labelText,
      position: Cesium.Cartesian3.fromDegrees(lon, lat, altM),
      billboard: {
        image: isMilitary ? "/military.svg" : "/plane.svg",
        width: isMilitary ? 38 : 26,
        height: isMilitary ? 38 : 26,
        color: isMilitary ? PLANE_MILITARY_COLOR : PLANE_CIVILIAN_COLOR,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        heightReference: altM > 0 ? Cesium.HeightReference.NONE : Cesium.HeightReference.CLAMP_TO_GROUND,
        scaleByDistance: isMilitary
          ? new Cesium.NearFarScalar(1.5e4, 1.5, 6e5, 0.5)
          : new Cesium.NearFarScalar(1.5e4, 1.2, 6e5, 0.28),
        disableDepthTestDistance: altM > 0 ? Number.POSITIVE_INFINITY : undefined
      },
      point: isMilitary ? {
        pixelSize: 8,
        color: PLANE_MILITARY_COLOR,
        outlineColor: new Cesium.Color(0.15, 0.12, 0.08, 0.9),
        outlineWidth: 1,
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      } : undefined,
      label: isMilitary ? {
        text: "MIL",
        font: "600 10px sans-serif",
        fillColor: PLANE_MIL_LABEL_COLOR,
        outlineColor: PLANE_MIL_LABEL_OUTLINE,
        outlineWidth: 1.5,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.TOP,
        pixelOffset: new Cesium.Cartesian2(0, -20),
        scaleByDistance: new Cesium.NearFarScalar(1.5e4, 0.95, 6e5, 0.5),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      } : undefined,
      description: buildFlightDescription(p, labelText, headingDeg, isMilitary)
    };
    if (headingDeg != null) {
      entity.billboard.rotation = -Cesium.Math.toRadians(headingDeg);
    }
    viewer.entities.add(entity);
  }
}

function altitudeForArea(positions) {
  const sphere = Cesium.BoundingSphere.fromPoints(positions);
  const radius = sphere.radius;
  return Math.max(1500, Math.min(20000, radius * 0.35));
}

function polygonCentroid(outerCartesians) {
  const n = outerCartesians.length;
  if (n === 0) return null;
  let sumX = 0, sumY = 0, sumZ = 0;
  for (let i = 0; i < n; i++) {
    const c = outerCartesians[i];
    sumX += c.x; sumY += c.y; sumZ += c.z;
  }
  const cartesian = new Cesium.Cartesian3(sumX / n, sumY / n, sumZ / n);
  const carto = Cesium.Cartographic.fromCartesian(cartesian);
  return { lon: Cesium.Math.toDegrees(carto.longitude), lat: Cesium.Math.toDegrees(carto.latitude) };
}

// Conflict zones: subtle muted red fill so they’re visible but not overwhelming
const CONFLICT_RED = new Cesium.Color(0.52, 0.24, 0.24, 0.48);
const CONFLICT_RED_LIGHT = new Cesium.Color(0.62, 0.34, 0.34, 0.36);
function conflictFill(fatalities) {
  const n = fatalities != null && Number.isFinite(fatalities) ? Number(fatalities) : 0;
  if (n > 0) {
    const t = Math.min(1, n / 500);
    return Cesium.Color.lerp(CONFLICT_RED_LIGHT, CONFLICT_RED, t, new Cesium.Color());
  }
  return CONFLICT_RED_LIGHT;
}
const CONFLICT_OUTLINE = new Cesium.Color(0.42, 0.2, 0.2, 0.6);
const CONFLICT_EXTRUSION_M = 400;

// Early warning: areas with high military aircraft count, not in conflict zones
const EARLY_WARNING_ORANGE = new Cesium.Color(0.78, 0.48, 0.22, 0.38);
const EARLY_WARNING_OUTLINE = new Cesium.Color(0.48, 0.32, 0.18, 0.65);
const EARLY_WARNING_EXTRUSION_M = 350;

const CONFLICT_DEFAULT_TITLE = "Conflict area";

function buildConflictDescription(title, props, fatalities) {
  const fat = fatalities != null && Number.isFinite(fatalities) ? Number(fatalities) : null;
  const parts = [];
  if (fat != null && fat > 0) parts.push(`Fatalities: ${fat}`);
  if (props.start_time) parts.push(`Start: ${props.start_time}`);
  if (props.end_time) parts.push(`End: ${props.end_time}`);
  if (props.observed_at) parts.push(`Observed: ${props.observed_at}`);
  if (props.source && props.source !== "builtin") parts.push(`Source: ${props.source}`);
  const body = parts.length ? parts.join("<br/>") : "Reported conflict zone.";
  const sourceLink = props.source_url
    ? `<br/><a href="${props.source_url}" target="_blank" rel="noopener noreferrer" style="color:#c8a0a0;">View source</a>`
    : "";
  return `<div style="max-width:340px;padding:10px;background:rgba(28,18,18,0.92);border:1px solid rgba(120,70,70,0.5);border-radius:8px;color:#f0e8e8;">
    <div style="font-size:1.05em;font-weight:bold;margin-bottom:6px;color:#e8c8c8;">⚠ ${title}</div>
    <div style="font-size:0.9em;line-height:1.4;">${body}${sourceLink}</div>
  </div>`;
}

function ringsFromGeometry(geom) {
  if (!geom) return [];
  if (geom.type === "Polygon") return [geom.coordinates[0]];
  if (geom.type === "MultiPolygon") return geom.coordinates.map((p) => p[0]);
  return [];
}

export async function upsertConflictAreas(viewer, geojson) {
  const areaPrefix = "conflict:";
  const toRemove = [...viewer.entities.values].filter((e) => (e.id || "").startsWith(areaPrefix));
  toRemove.forEach((e) => viewer.entities.remove(e));

  const countryCodes = Array.isArray(geojson?.features) && geojson.features.some((f) => {
    const cc = f.properties?.country_codes;
    return Array.isArray(cc) && cc.length > 0;
  });
  const countriesGeojson = countryCodes ? await getCountriesGeojson() : null;

  for (const f of geojson.features || []) {
    try {
      const props = f.properties || {};
      const fatalities = props.fatalities;
      const fill = conflictFill(fatalities);
      const title = (props.title && String(props.title).trim()) || CONFLICT_DEFAULT_TITLE;
      const description = buildConflictDescription(title, props, fatalities);

      const codes = props.country_codes;
      const useCountryShapes = Array.isArray(codes) && codes.length > 0 && countriesGeojson?.features?.length > 0;
      const codeSet = useCountryShapes ? new Set(codes.map((c) => String(c).toUpperCase())) : null;

      let rings = [];
      if (useCountryShapes && codeSet) {
        for (const cf of countriesGeojson.features) {
          const iso = getIsoA2(cf.properties);
          if (!iso || !codeSet.has(iso)) continue;
          rings.push(...ringsFromGeometry(cf.geometry));
        }
      }
      if (rings.length === 0) {
        const geom = f.geometry;
        if (geom?.type === "Polygon") rings = [geom.coordinates[0]];
        else if (geom?.type === "MultiPolygon") rings = [geom.coordinates[0][0]];
      }

      for (let partIdx = 0; partIdx < rings.length; partIdx++) {
        const outer = rings[partIdx].map(([lon, lat]) => Cesium.Cartesian3.fromDegrees(Number(lon), Number(lat), 0));
        const hierarchy = new Cesium.PolygonHierarchy(outer);
        const partId = rings.length > 1 ? `${f.id}_part_${partIdx}` : f.id;
        viewer.entities.add({
          id: partId,
          name: title,
          polygon: {
            hierarchy,
            heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            extrudedHeight: CONFLICT_EXTRUSION_M,
            outline: true,
            outlineColor: CONFLICT_OUTLINE,
            outlineWidth: 2,
            material: fill,
            fill: true,
            stRotation: 0,
            perPositionHeight: false
          },
          description
        });
      }

      const firstRing = rings[0];
      if (!firstRing?.length) continue;
      const outer = firstRing.map(([lon, lat]) => Cesium.Cartesian3.fromDegrees(Number(lon), Number(lat), 0));
      const lonA = props.anchor_lon;
      const latA = props.anchor_lat;
      let iconLon = lonA;
      let iconLat = latA;
      if (typeof lonA !== "number" || typeof latA !== "number") {
        const centroid = polygonCentroid(outer);
        if (centroid) {
          iconLon = centroid.lon;
          iconLat = centroid.lat;
        } else continue;
      }
      const alt = altitudeForArea(outer) + CONFLICT_EXTRUSION_M;
      const labelText = title.length <= 28 ? title : title.slice(0, 25) + "...";
      const fatLabel = fatalities != null && Number.isFinite(fatalities) && fatalities > 0 ? ` · ${fatalities}` : "";
      viewer.entities.add({
        id: `${f.id}__icon`,
        position: Cesium.Cartesian3.fromDegrees(iconLon, iconLat, alt),
        billboard: {
          image: "/conflict.svg",
          width: 40,
          height: 40,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          scaleByDistance: new Cesium.NearFarScalar(8e3, 1.25, 4e5, 0.38),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          color: new Cesium.Color(0.92, 0.82, 0.82, 0.92)
        },
        label: {
          text: labelText + fatLabel,
          font: "600 13px sans-serif",
          verticalOrigin: Cesium.VerticalOrigin.TOP,
          pixelOffset: new Cesium.Cartesian2(0, 14),
          fillColor: new Cesium.Color(0.98, 0.95, 0.94, 0.98),
          outlineColor: new Cesium.Color(0.25, 0.18, 0.18, 0.85),
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          scaleByDistance: new Cesium.NearFarScalar(8e3, 1.05, 4e5, 0.42),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          showBackground: true,
          backgroundColor: new Cesium.Color(0.22, 0.14, 0.14, 0.82),
          backgroundPadding: new Cesium.Cartesian2(8, 4)
        },
        description
      });
    } catch (_) {}
  }
}

export async function upsertEarlyWarningAreas(viewer, geojson) {
  const prefix = "early_warning:";
  const toRemove = [...viewer.entities.values].filter(e => (e.id || "").startsWith(prefix));
  toRemove.forEach(e => viewer.entities.remove(e));

  for (const f of geojson.features || []) {
    try {
      const props = f.properties || {};
      const geom = f.geometry;
      let rings = [];
      if (geom?.type === "Polygon" && Array.isArray(geom.coordinates)) rings = geom.coordinates;
      else if (geom?.type === "MultiPolygon" && Array.isArray(geom.coordinates?.[0])) rings = geom.coordinates[0];
      else continue;

      const ring0 = rings[0];
      if (!Array.isArray(ring0) || ring0.length < 3) continue;
      const outer = ring0.map(([lon, lat]) => Cesium.Cartesian3.fromDegrees(Number(lon), Number(lat), 0));
      const hierarchy = new Cesium.PolygonHierarchy(outer);
      const title = (props.title && String(props.title).trim()) || "Early warning";
      const count = props.military_count != null ? Number(props.military_count) : 0;

      const earlyWarningDescription = `<div style="max-width:320px;padding:10px;background:rgba(32,24,18,0.92);border:1px solid rgba(100,75,50,0.45);border-radius:8px;color:#ebe4dc;">
      <div style="font-size:1em;font-weight:600;margin-bottom:6px;color:#d4a574;">&#9888; ${title}</div>
      <div style="font-size:0.9em;line-height:1.4;">
        High concentration of military aircraft (not in a reported conflict zone).<br/>
        ${count > 0 ? `Military aircraft in area: ${count}<br/>` : ""}
        ${props.observed_at ? `Observed: ${props.observed_at}` : ""}
      </div>
    </div>`;
      viewer.entities.add({
        id: f.id,
        name: title,
        polygon: {
          hierarchy,
          heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
          extrudedHeight: EARLY_WARNING_EXTRUSION_M,
          outline: true,
          outlineColor: EARLY_WARNING_OUTLINE,
          outlineWidth: 2,
          material: EARLY_WARNING_ORANGE,
          fill: true,
          stRotation: 0,
          perPositionHeight: false
        },
        description: earlyWarningDescription
      });

      const centroid = polygonCentroid(outer);
      if (!centroid) continue;
      const alt = altitudeForArea(outer) + EARLY_WARNING_EXTRUSION_M;
      const labelText = count > 0 ? `Early warning — ${count} mil` : "Early warning";
      viewer.entities.add({
        id: `${f.id}__icon`,
        position: Cesium.Cartesian3.fromDegrees(centroid.lon, centroid.lat, alt),
        billboard: {
          image: "/conflict.svg",
          width: 34,
          height: 34,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          scaleByDistance: new Cesium.NearFarScalar(8e3, 1.1, 4e5, 0.32),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
          color: new Cesium.Color(0.9, 0.75, 0.5, 0.9)
        },
        label: {
          text: labelText,
          font: "600 12px sans-serif",
          verticalOrigin: Cesium.VerticalOrigin.TOP,
          pixelOffset: new Cesium.Cartesian2(0, 14),
          fillColor: new Cesium.Color(0.98, 0.94, 0.88, 0.96),
          outlineColor: new Cesium.Color(0.22, 0.16, 0.1, 0.85),
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          scaleByDistance: new Cesium.NearFarScalar(8e3, 1, 4e5, 0.42),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
          showBackground: true,
          backgroundColor: new Cesium.Color(0.28, 0.2, 0.12, 0.82),
          backgroundPadding: new Cesium.Cartesian2(8, 4)
        },
        description: earlyWarningDescription
      });
    } catch (_) {}
  }
}

export async function upsertFuel(viewer, geojson) {
  const prefix = "fuel:";
  const toRemove = [...viewer.entities.values].filter(e => (e.id || "").startsWith(prefix));
  toRemove.forEach(e => viewer.entities.remove(e));
  for (const f of geojson.features || []) {
    const coords = f.geometry?.coordinates;
    if (!isValidPointCoords(coords)) continue;
    const [lon, lat] = coords;
    const p = f.properties || {};
    viewer.entities.add({
      id: f.id,
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
      billboard: {
        image: "/fuel.svg",
        width: 24,
        height: 24,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
      },
      description: `<b>Fuel Station</b><br/>${p.country_name ? `Country: ${p.country_name}<br/>` : ""}Fuel: ${p.fuel_type ?? ""}<br/>Price: ${p.price_per_l ?? ""} ${p.currency ?? ""}<br/>Observed: ${p.observed_at ?? ""}`
    });
  }
}

/**
 * Upsert camera-city markers from GeoJSON (Shodan IP cameras aggregated by city).
 * Fills camerasByEntityIdRef.current[entityId] = { cityName, country, cameras } for click handler.
 */
export async function upsertCameraCities(viewer, geojson, camerasByEntityIdRef) {
  const prefix = "camera_city:";
  const toRemove = [...viewer.entities.values].filter(e => (e.id || "").startsWith(prefix));
  toRemove.forEach(e => viewer.entities.remove(e));
  const ref = camerasByEntityIdRef?.current;
  if (ref) Object.keys(ref).forEach(k => { if (k.startsWith(prefix)) delete ref[k]; });
  for (const f of geojson.features || []) {
    const coords = f.geometry?.coordinates;
    if (!isValidPointCoords(coords)) continue;
    const [lon, lat] = coords;
    const p = f.properties || {};
    const cityKey = `${p.city ?? "Unknown"}-${p.country_code ?? "XX"}`;
    const entityId = f.id ?? `${prefix}${cityKey}`;
    const count = p.count ?? (p.cameras?.length ?? 0);
    const cityName = p.city ?? "Unknown";
    const country = p.country_name ?? p.country_code ?? "";
    const cameras = p.cameras ?? [];
    if (ref) ref[entityId] = { cityName, country, cameras };
    viewer.entities.add({
      id: entityId,
      position: Cesium.Cartesian3.fromDegrees(lon, lat, 0),
      billboard: {
        image: "/camera.svg",
        width: 28,
        height: 28,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND
      },
      label: {
        text: `${cityName} (${count})`,
        font: "12px sans-serif",
        verticalOrigin: Cesium.VerticalOrigin.TOP,
        pixelOffset: new Cesium.Cartesian2(0, 18),
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.BLACK,
        outlineWidth: 2,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        scaleByDistance: new Cesium.NearFarScalar(1e4, 1, 5e5, 0.5),
        disableDepthTestDistance: Number.POSITIVE_INFINITY
      },
      description: `<b>IP cameras – ${cityName}</b><br/>${country ? `Country: ${country}<br/>` : ""}Count: ${count}<br/>Click to open list.`
    });
  }
}
