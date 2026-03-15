import React, { useEffect, useRef, useState } from "react";
import { makeViewer } from "./lib/cesium";
import { getJSON } from "./lib/api";
import { upsertFlights, upsertConflictAreas, upsertEarlyWarningAreas, upsertFuel, upsertCameraCities } from "./lib/layers";
import { addCountryBoundariesAndLabels } from "./lib/countriesGlobe";
import * as Cesium from "cesium";
import Sidebar from "./components/Sidebar";
import CameraListModal from "./components/CameraListModal";
import ConflictInfoPanel from "./components/ConflictInfoPanel";

const LAYER_META = [
  {
    id: "flights",
    label: "Live flights",
    help: "Current aircraft positions from live ingestion."
  },
  {
    id: "flightTracks",
    label: "Flight tracks",
    help: "Recent CZML playback for aircraft movement."
  },
  {
    id: "conflicts",
    label: "Conflict areas",
    help: "Region-level incidents rendered as polygons."
  },
  {
    id: "earlyWarning",
    label: "Early warning",
    help: "Areas with many military aircraft that are not in reported conflict zones (orange)."
  },
  {
    id: "fuelFR",
    label: "Fuel stations (France)",
    help: "Latest station-level fuel pricing markers."
  },
  {
    id: "cameras",
    label: "IP cameras (Shodan)",
    help: "Cities with open IP cameras; click icon for list."
  }
];

export default function App() {
  const viewerRef = useRef(null);
  const trackDsRef = useRef(null);
  const militaryAutoFocusDoneRef = useRef(false);
  const cameraCitiesRef = useRef({});
  const [cameraModal, setCameraModal] = useState(null);

  const [prices, setPrices] = useState({});
  const [status, setStatus] = useState({});
  const [layers, setLayers] = useState({ flights: true, flightTracks: true, conflicts: true, earlyWarning: true, fuelFR: false, cameras: true });
  const [flightFilters, setFlightFilters] = useState({ civilian: true, military: true });
  const [panelOpen, setPanelOpen] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [viewerReady, setViewerReady] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [camerasMessage, setCamerasMessage] = useState(null);
  const [selectedConflict, setSelectedConflict] = useState({ entity: null, descriptionHtml: "" });
  const [selectedFlight, setSelectedFlight] = useState({ entity: null, descriptionHtml: "" });

  const ionToken = import.meta.env.VITE_CESIUM_ION_TOKEN;

  function getConflictEntityAt(viewer, windowPosition) {
    const picked = viewer.scene.drillPick(windowPosition);
    for (const obj of picked) {
      if (obj.id && typeof obj.id === "object" && (obj.id.id || "").toString().startsWith("conflict:")) {
        return obj.id;
      }
    }
    return null;
  }

  function getDescriptionFromEntity(entity, viewer) {
    if (!entity || !viewer) return "";
    const desc = entity.description;
    if (!desc) return "";
    if (typeof desc.getValue === "function") {
      return desc.getValue(viewer.clock.currentTime) ?? "";
    }
    return typeof desc === "string" ? desc : "";
  }

  useEffect(() => {
    const mql = window.matchMedia("(max-width: 1024px)");
    const syncPanelMode = (event) => {
      setPanelOpen(!event.matches);
    };
    syncPanelMode(mql);
    mql.addEventListener("change", syncPanelMode);
    return () => mql.removeEventListener("change", syncPanelMode);
  }, []);

  useEffect(() => {
    const viewer = makeViewer("globe", ionToken);
    viewerRef.current = viewer;
    setViewerReady(true);

    try {
      const gibs = new Cesium.WebMapTileServiceImageryProvider({
        url: "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/wmts.cgi",
        layer: "MODIS_Terra_CorrectedReflectance_TrueColor",
        style: "default",
        format: "image/jpeg",
        tileMatrixSetID: "EPSG4326_250m",
        maximumLevel: 9
      });
      viewer.imageryLayers.addImageryProvider(gibs);
    } catch {}

    addCountryBoundariesAndLabels(viewer);

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((movement) => {
      setTimeout(() => {
        const conflictEntity = getConflictEntityAt(viewer, movement.position);
        if (conflictEntity) {
          viewer.selectedEntity = conflictEntity;
        }
      }, 0);
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    const removeSelectedEntityListener = viewer.selectedEntityChanged.addEventListener((entity) => {
      if (entity && (entity.id || "").toString().startsWith("conflict:")) {
        const descriptionHtml = getDescriptionFromEntity(entity, viewer);
        setSelectedConflict({ entity, descriptionHtml });
        setSelectedFlight({ entity: null, descriptionHtml: "" });
      } else if (entity && (entity.id || "").toString().startsWith("flight:")) {
        const descriptionHtml = getDescriptionFromEntity(entity, viewer);
        setSelectedFlight({ entity, descriptionHtml });
        setSelectedConflict({ entity: null, descriptionHtml: "" });
      } else {
        setSelectedConflict({ entity: null, descriptionHtml: "" });
        setSelectedFlight({ entity: null, descriptionHtml: "" });
      }
    });

    return () => {
      try {
        handler.destroy();
      } catch (_) {}
      try {
        removeSelectedEntityListener();
      } catch (_) {}
      try {
        viewer.destroy();
      } catch (_) {}
      setViewerReady(false);
    };
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !viewerReady) return;
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((event) => {
      const picked = viewer.scene.pick(event.position);
      if (Cesium.defined(picked) && picked.id && String(picked.id).startsWith("camera_city:")) {
        const data = cameraCitiesRef.current[picked.id];
        if (data) setCameraModal({ cityName: data.cityName, country: data.country, cameras: data.cameras });
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    return () => handler.destroy();
  }, [viewerReady]);

  async function refreshTracks() {
    const viewer = viewerRef.current;
    if (!viewer) return;

    if (trackDsRef.current) {
      viewer.dataSources.remove(trackDsRef.current, true);
      trackDsRef.current = null;
    }

    try {
      const czml = await getJSON("/czml/flights?hours=6&max_aircraft=120");
      const ds = await Cesium.CzmlDataSource.load(czml);
      viewer.dataSources.add(ds);
      trackDsRef.current = ds;
      if (ds.clock) {
        viewer.clock.currentTime = Cesium.JulianDate.clone(ds.clock.currentTime);
        viewer.clock.startTime = Cesium.JulianDate.clone(ds.clock.startTime);
        viewer.clock.stopTime = Cesium.JulianDate.clone(ds.clock.stopTime);
        viewer.clock.clockRange = ds.clock.clockRange ?? Cesium.ClockRange.LOOP_STOP;
        if (viewer.timeline) viewer.timeline.updateFromClock();
      }
    } catch (err) {
      const msg = err?.message || String(err);
      console.error("Centaur track load error:", msg);
      setLoadError(msg);
      if (viewer.dataSources && trackDsRef.current) {
        viewer.dataSources.remove(trackDsRef.current, true);
        trackDsRef.current = null;
      }
    }
  }

  useEffect(() => {
    let alive = true;

    async function tick() {
      const viewer = viewerRef.current;
      if (!viewer || !viewerReady) return;

      try {
        setLoadError(null);
        if (layers.flights) {
          const flights = await getJSON("/geo/flights?max_age_seconds=900");
          if (!alive) return;
          const features = (flights.features || []).filter((feature) => {
            const confidence = Number(feature?.properties?.military_confidence ?? 0);
            const isMilitary = feature?.properties?.likely_military === true || confidence >= 40;
            if (feature?.properties) feature.properties.military_display = isMilitary;
            if (isMilitary && !flightFilters.military) return false;
            if (!isMilitary && !flightFilters.civilian) return false;
            return true;
          });
          await upsertFlights(viewer, { ...flights, features });

          const militaryOnlyMode = flightFilters.military && !flightFilters.civilian;
          if (militaryOnlyMode && features.length > 0 && !militaryAutoFocusDoneRef.current) {
            const points = features.map((feature) => {
              const [lon, lat] = feature.geometry.coordinates;
              return Cesium.Cartesian3.fromDegrees(lon, lat, 0);
            });
            if (points.length > 0) {
              const sphere = Cesium.BoundingSphere.fromPoints(points);
              viewer.camera.flyToBoundingSphere(sphere, { duration: 1.6 });
              militaryAutoFocusDoneRef.current = true;
            }
          }
          if (!militaryOnlyMode) {
            militaryAutoFocusDoneRef.current = false;
          }
        } else {
          await upsertFlights(viewer, { type: "FeatureCollection", features: [] });
          militaryAutoFocusDoneRef.current = false;
        }

        if (layers.conflicts) {
          const conflicts = await getJSON("/geo/conflicts?hours=168");
          if (!alive) return;
          await upsertConflictAreas(viewer, conflicts);
        } else {
          await upsertConflictAreas(viewer, { type: "FeatureCollection", features: [] });
        }

        if (layers.earlyWarning) {
          const earlyWarning = await getJSON("/geo/early-warning?max_age_seconds=120&min_military_count=4");
          if (!alive) return;
          await upsertEarlyWarningAreas(viewer, earlyWarning);
        } else {
          await upsertEarlyWarningAreas(viewer, { type: "FeatureCollection", features: [] });
        }

        if (layers.fuelFR) {
          const fuel = await getJSON("/geo/fuel/france?hours=24");
          if (!alive) return;
          await upsertFuel(viewer, fuel);
        } else {
          await upsertFuel(viewer, { type: "FeatureCollection", features: [] });
        }

        if (layers.cameras) {
          try {
            const camerasData = await getJSON("/geo/cameras");
            if (!alive) return;
            setCamerasMessage(camerasData.meta?.message ?? null);
            await upsertCameraCities(viewer, camerasData, cameraCitiesRef);
          } catch (_) {
            setCamerasMessage(null);
            await upsertCameraCities(viewer, { type: "FeatureCollection", features: [] }, cameraCitiesRef);
          }
        } else {
          setCamerasMessage(null);
          await upsertCameraCities(viewer, { type: "FeatureCollection", features: [] }, cameraCitiesRef);
        }

        if (layers.flightTracks) {
          if (!trackDsRef.current) await refreshTracks();
        } else if (trackDsRef.current) {
          viewer.dataSources.remove(trackDsRef.current, true);
          trackDsRef.current = null;
        }

        const p = await getJSON("/prices/latest");
        if (!alive) return;
        setPrices(p);

        const s = await getJSON("/status");
        if (!alive) return;
        setStatus(s);
        setLastUpdated(new Date().toISOString());
      } catch (err) {
        const msg = err?.message || String(err);
        console.error("Centaur layer load error:", msg);
        setLoadError(msg);
      }
    }

    tick();
    const POLL_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes
    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => { alive = false; clearInterval(id); };
  }, [layers, flightFilters, viewerReady]);

  return (
    <div className="layout">
      <div id="globe" className="globe"></div>

      <button
        type="button"
        className="panelToggle"
        onClick={() => setPanelOpen((prev) => !prev)}
        aria-expanded={panelOpen}
        aria-controls="control-panel"
        aria-label={panelOpen ? "Hide controls" : "Show controls"}
      >
        <span className="panelToggleIcon" aria-hidden="true">
          {panelOpen ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="18" x2="20" y2="18" />
            </svg>
          )}
        </span>
        <span className="panelToggleLabel">{panelOpen ? "Hide controls" : "Show controls"}</span>
      </button>

      {panelOpen ? <button type="button" className="panelBackdrop" onClick={() => setPanelOpen(false)} aria-label="Close controls" /> : null}

      <ConflictInfoPanel
        entity={selectedConflict.entity}
        descriptionHtml={selectedConflict.descriptionHtml}
        title="Conflict zone"
        ariaLabel="Conflict zone details"
        onClose={() => {
          if (viewerRef.current) viewerRef.current.selectedEntity = undefined;
          setSelectedConflict({ entity: null, descriptionHtml: "" });
        }}
      />
      <ConflictInfoPanel
        entity={selectedFlight.entity}
        descriptionHtml={selectedFlight.descriptionHtml}
        title="Aircraft details"
        ariaLabel="Aircraft details"
        className="conflictInfoPanel flightInfoPanel"
        onClose={() => {
          if (viewerRef.current) viewerRef.current.selectedEntity = undefined;
          setSelectedFlight({ entity: null, descriptionHtml: "" });
        }}
      />

      <Sidebar
        panelId="control-panel"
        title="Centaur controls"
        isOpen={panelOpen}
        layers={layers}
        flightFilters={flightFilters}
        layerMeta={LAYER_META}
        prices={prices}
        statusJobs={status.jobs}
        lastUpdated={lastUpdated}
        loadError={loadError}
        camerasMessage={camerasMessage}
        onLayerChange={(layerId, checked) => setLayers((prev) => ({ ...prev, [layerId]: checked }))}
        onFlightFilterChange={(filterId, checked) => setFlightFilters((prev) => ({ ...prev, [filterId]: checked }))}
        onRefreshTracks={refreshTracks}
        canRefreshTracks={layers.flightTracks}
        onClose={() => setPanelOpen(false)}
      />

      <CameraListModal
        open={cameraModal != null}
        onClose={() => setCameraModal(null)}
        cityName={cameraModal?.cityName ?? ""}
        country={cameraModal?.country ?? ""}
        cameras={cameraModal?.cameras ?? []}
      />
    </div>
  );
}
