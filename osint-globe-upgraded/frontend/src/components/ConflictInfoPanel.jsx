import React, { useId } from "react";

export default function ConflictInfoPanel({
  entity,
  descriptionHtml,
  onClose,
  title = "Conflict zone",
  ariaLabel = "Details",
  className = "conflictInfoPanel",
}) {
  if (!entity) return null;
  const titleId = useId();
  const closeLabel = `Close ${title || "details"} panel`;

  return (
    <div className={className} role="dialog" aria-labelledby={titleId} aria-label={ariaLabel}>
      <div className="conflictInfoPanelHeader">
        <span id={titleId} className="conflictInfoPanelTitle">
          {title}
        </span>
        <button
          type="button"
          className="iconBtn conflictInfoPanelClose"
          onClick={onClose}
          aria-label={closeLabel}
        >
          ×
        </button>
      </div>
      <div className="conflictInfoPanelBody">
        <div
          className="conflictInfoPanelDescription"
          dangerouslySetInnerHTML={{ __html: descriptionHtml || "" }}
        />
      </div>
    </div>
  );
}
