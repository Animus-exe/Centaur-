import React from "react";
import SidebarSection from "./SidebarSection";

export default function IntegrityPanel() {
  return (
    <SidebarSection title="Integrity">
      <div className="muted">
        Area-only events render as polygons with floating markers. Flight tracks are displayed through CZML playback.
      </div>
    </SidebarSection>
  );
}
