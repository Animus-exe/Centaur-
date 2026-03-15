import React from "react";
import SidebarSection from "./SidebarSection";

export default function LayerToggleList({
  layerMeta,
  layers,
  onLayerChange,
  onRefreshTracks,
  canRefreshTracks,
  flightFilters,
  onFlightFilterChange
}) {
  return (
    <SidebarSection title="Layers">
      <div className="stack">
        {layerMeta.map((layer) => (
          <label key={layer.id} className="row">
            <input
              type="checkbox"
              checked={Boolean(layers[layer.id])}
              onChange={(e) => onLayerChange(layer.id, e.target.checked)}
            />
            <span className="rowContent">
              <span className="rowTitle">{layer.label}</span>
              <span className="muted">{layer.help}</span>
            </span>
          </label>
        ))}
      </div>

      <div className="stack" style={{ marginTop: "12px" }}>
        <label className="row">
          <input
            type="checkbox"
            checked={Boolean(flightFilters?.civilian)}
            onChange={(e) => onFlightFilterChange("civilian", e.target.checked)}
            disabled={!layers.flights}
          />
          <span className="rowContent">
            <span className="rowTitle">Show civilian flights</span>
            <span className="muted">Toggle non-military aircraft visibility.</span>
          </span>
        </label>

        <label className="row">
          <input
            type="checkbox"
            checked={Boolean(flightFilters?.military)}
            onChange={(e) => onFlightFilterChange("military", e.target.checked)}
            disabled={!layers.flights}
          />
          <span className="rowContent">
            <span className="rowTitle">Show military flights</span>
            <span className="muted">Toggle suspected military aircraft visibility.</span>
          </span>
        </label>
      </div>

      <button type="button" className="btn" onClick={onRefreshTracks} disabled={!canRefreshTracks}>
        Refresh flight tracks
      </button>
    </SidebarSection>
  );
}
