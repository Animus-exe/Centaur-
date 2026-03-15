import React from "react";
import LayerToggleList from "./LayerToggleList";
import Legend from "./Legend";
import BenchmarkPriceList from "./BenchmarkPriceList";
import IngestionStatusList from "./IngestionStatusList";
import IntegrityPanel from "./IntegrityPanel";

export default function Sidebar({
  panelId,
  title,
  isOpen,
  layers,
  flightFilters,
  layerMeta,
  prices,
  statusJobs,
  lastUpdated,
  loadError,
  camerasMessage,
  onLayerChange,
  onFlightFilterChange,
  onRefreshTracks,
  canRefreshTracks,
  onClose
}) {
  const parsed = lastUpdated ? new Date(lastUpdated) : null;
  const updatedLabel = parsed && !Number.isNaN(parsed.getTime()) ? parsed.toLocaleTimeString() : "Waiting for sync";

  return (
    <aside id={panelId} className={`panel ${isOpen ? "open" : ""}`} aria-label="Control panel">
      <div className="panelHeader">
        <div className="panelHeaderMain">
          <span className="panelHeaderIcon" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
          </span>
          <div className="panelHeaderText">
            <h2>{title}</h2>
            <div className="panelHeaderMeta">
              <span className="panelHeaderMetaDot" aria-hidden="true" />
              <span className="muted">Last refresh: {updatedLabel}</span>
            </div>
          </div>
        </div>
        <button type="button" className="iconBtn panelCloseBtn" onClick={onClose} aria-label="Close panel">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      {loadError ? (
        <div className="loadError" role="alert">
          Cannot load layers: {loadError}. Is the backend running at {import.meta.env.VITE_API_BASE ?? (import.meta.env.DEV ? "http://localhost:8000 (proxied from /api)" : "http://localhost:8000")}?
        </div>
      ) : null}

      {camerasMessage ? (
        <div className="camerasMessage muted" role="status">
          IP cameras: {camerasMessage}
        </div>
      ) : null}

      <LayerToggleList
        layerMeta={layerMeta}
        layers={layers}
        flightFilters={flightFilters}
        onLayerChange={onLayerChange}
        onFlightFilterChange={onFlightFilterChange}
        onRefreshTracks={onRefreshTracks}
        canRefreshTracks={canRefreshTracks}
      />
      <Legend />
      <BenchmarkPriceList prices={prices} />
      <IngestionStatusList statusJobs={statusJobs} />
      <IntegrityPanel />
    </aside>
  );
}
