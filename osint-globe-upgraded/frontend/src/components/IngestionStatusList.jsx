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

export default function IngestionStatusList({ statusJobs }) {
  const statusEntries = Object.entries(statusJobs || {});

  return (
    <SidebarSection title="Ingestion Status">
      {statusEntries.length === 0 ? (
        <div className="empty">No status yet.</div>
      ) : (
        <div className="status">
          {statusEntries.map(([name, job]) => (
            <div key={name} className="statusRow">
              <div className="statusHeader">
                <b>{fmt(name, "Unnamed job")}</b>
                <span className={job.ok ? "statusBadge ok" : "statusBadge fail"}>
                  {job.ok ? "Healthy" : "Failed"}
                </span>
              </div>
              <div className="muted">
                {formatTimestamp(job?.ran_at)} - {fmt(job?.duration_ms, "0")}ms - {fmt(job?.item_count, "0")} items
              </div>
              {!job?.ok && job?.error ? <div className="errorText">Error: {fmt(job.error, "Unknown error")}</div> : null}
            </div>
          ))}
        </div>
      )}
    </SidebarSection>
  );
}
