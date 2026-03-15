import React from "react";
import SidebarSection from "./SidebarSection";

const LEGEND_ENTRIES = [
  { type: "icon", src: "/plane.svg", label: "Civilian flight" },
  { type: "icon", src: "/military.svg", label: "Military flight" },
  {
    type: "swatch-icon",
    swatchColor: "#852d2d",
    src: "/conflict.svg",
    label: "Conflict area"
  },
  {
    type: "swatch-icon",
    swatchColor: "#c87a38",
    src: "/conflict.svg",
    iconStyle: { filter: "sepia(0.4) saturate(1.2) hue-rotate(-10deg)" },
    label: "Early warning area"
  },
  { type: "icon", src: "/fuel.svg", label: "Fuel station (France)" },
  { type: "icon", src: "/camera.svg", label: "IP camera (city)" }
];

export default function Legend() {
  return (
    <SidebarSection title="Legend">
      <div className="legend" aria-label="Map legend">
        <ul className="legendList">
          {LEGEND_ENTRIES.map((entry) => (
            <li key={entry.label} className="legendRow">
              {entry.type === "swatch-icon" && (
                <>
                  <span
                    className="legendSwatch"
                    style={{ backgroundColor: entry.swatchColor }}
                    aria-hidden="true"
                  />
                  <img
                    src={entry.src}
                    alt=""
                    className="legendIcon"
                    style={entry.iconStyle}
                    aria-hidden="true"
                  />
                </>
              )}
              {entry.type === "icon" && (
                <img src={entry.src} alt="" className="legendIcon" aria-hidden="true" />
              )}
              <span className="legendLabel">{entry.label}</span>
            </li>
          ))}
        </ul>
      </div>
    </SidebarSection>
  );
}
