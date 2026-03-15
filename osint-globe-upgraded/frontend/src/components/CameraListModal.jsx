import React, { useState, useRef, useEffect, useCallback } from "react";

const OVERLAY_TRANSITION_MS = 200;

export default function CameraListModal({ open, onClose, cityName, country, cameras }) {
  const [isClosing, setIsClosing] = useState(false);
  const closeTimeoutRef = useRef(null);
  const closeButtonRef = useRef(null);

  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current) clearTimeout(closeTimeoutRef.current);
    };
  }, []);

  const handleClose = useCallback(() => {
    if (isClosing) return;
    setIsClosing(true);
    closeTimeoutRef.current = setTimeout(() => {
      closeTimeoutRef.current = null;
      onClose();
      setIsClosing(false);
    }, OVERLAY_TRANSITION_MS);
  }, [isClosing, onClose]);

  useEffect(() => {
    if (!open || isClosing) return undefined;

    const handleEscape = (event) => {
      if (event.key === "Escape") handleClose();
    };

    document.addEventListener("keydown", handleEscape);
    closeButtonRef.current?.focus();

    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open, isClosing, handleClose]);

  if (!open && !isClosing) return null;
  const list = Array.isArray(cameras) ? cameras : [];

  return (
    <>
      <div
        className={`cameraModalBackdrop ${isClosing ? "closing" : ""}`}
        onClick={handleClose}
      />
      <div
        className={`cameraModal ${isClosing ? "closing" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="cameraModalTitle"
      >
        <div className="cameraModalHeader">
          <h2 id="cameraModalTitle">IP cameras – {cityName}</h2>
          {country ? <span className="muted">{country}</span> : null}
          <button
            ref={closeButtonRef}
            type="button"
            className="cameraModalClose"
            onClick={handleClose}
            aria-label="Close camera list"
          >
            ×
          </button>
        </div>
        <p className="cameraModalDisclaimer">
          For authorized research only; respect privacy and applicable laws.
        </p>
        <ul className="cameraModalList">
          {list.length === 0 ? (
            <li className="empty">No cameras in this location.</li>
          ) : (
            list.map((cam, i) => (
              <li key={`${cam.ip}-${cam.port}-${i}`} className="cameraModalItem">
                <div className="cameraModalItemHeader">
                  <span className="cameraModalItemAddr">{cam.ip}:{cam.port}</span>
                  {cam.product ? <span className="pill">{cam.product}</span> : null}
                </div>
                <a
                  href={cam.link || `http://${cam.ip}:${cam.port}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="cameraModalLink"
                >
                  Open stream
                </a>
              </li>
            ))
          )}
        </ul>
      </div>
    </>
  );
}
