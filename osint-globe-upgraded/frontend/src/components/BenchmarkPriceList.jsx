import React from "react";
import SidebarSection from "./SidebarSection";

function fmt(value, fallback = "N/A") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function formatTimestamp(ts) {
  if (!ts) return "Unknown time";
  const parsed = new Date(ts);
  if (Number.isNaN(parsed.getTime())) return String(ts);
  return parsed.toLocaleString();
}

export default function BenchmarkPriceList({ prices }) {
  const priceEntries = Object.entries(prices || {});

  return (
    <SidebarSection title="Benchmark Prices">
      {priceEntries.length === 0 ? (
        <div className="empty">No price data yet.</div>
      ) : (
        <ul className="list">
          {priceEntries.map(([name, value]) => (
            <li key={name} className="listItem">
              <div className="listItemTitle">
                <span>{fmt(name, "Unnamed benchmark")}</span>
                <span className="pill">{fmt(value?.unit, "unit")}</span>
              </div>
              <div className="listItemValue">
                {fmt(value?.price)} {fmt(value?.currency, "")}
              </div>
              <div className="muted">
                {formatTimestamp(value?.ts)} - {fmt(value?.source, "Unknown source")}
              </div>
            </li>
          ))}
        </ul>
      )}
    </SidebarSection>
  );
}
