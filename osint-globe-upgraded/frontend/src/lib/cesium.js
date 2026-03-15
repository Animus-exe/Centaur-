import * as Cesium from "cesium";

export function makeViewer(containerId, ionToken) {
  if (ionToken) Cesium.Ion.defaultAccessToken = ionToken;
  const viewer = new Cesium.Viewer(containerId, {
    animation: true,
    timeline: true,
    baseLayerPicker: false,
    geocoder: false,
    homeButton: true,
    sceneModePicker: true,
    navigationHelpButton: false,
    fullscreenButton: true,
    infoBox: false,
    terrainProvider: ionToken ? Cesium.createWorldTerrainAsync() : new Cesium.EllipsoidTerrainProvider()
  });
  viewer.scene.globe.depthTestAgainstTerrain = true;
  // Hide Cesium Ion credit/attribution overlay
  if (viewer.cesiumWidget && viewer.cesiumWidget.creditContainer) {
    viewer.cesiumWidget.creditContainer.style.display = "none";
  }
  return viewer;
}
