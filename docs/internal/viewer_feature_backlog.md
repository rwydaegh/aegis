# Viewer feature backlog

Essential frontend improvements identified during E2E testing (2026-03-17). All items implemented 2026-03-17.

## Implemented

### WASD controls to move Thelonious
WASD keys translate the body mesh in the XZ plane. Q/E move up/down. Orbit target follows the body. Dosimetry recomputes (debounced 200ms) after each move. Body offset is sent to the backend so distance and illumination update correctly.

### Arrow key antenna nudge
Arrow keys nudge the antenna position in the XZ plane (0.5m steps). Replaces the "draggable antenna" request. Avoids conflicts with orbit controls. Triggers debounced recompute.

### Ground plane
Semi-transparent dark ground plane at y=0 with shadow receiving. Grid lines upgraded for better visibility. Fixes the "floating in void" feeling.

### Heatmap color scale legend
Vertical gradient bar (inferno colormap) on the right side of the viewport. Shows min/mid/max S_ab values in W/m². Appears after first computation. Updates on every recompute.

### Distance line
Dashed white line from antenna to body centroid. Distance label (sprite) at the midpoint showing distance in meters. Updates on antenna placement and body movement.

### Preset camera views
Front, Side, and Top buttons in a Camera section. Each snaps the camera to frame the body from that direction at a fixed distance. Replaces the old single "Reset camera" button.

### Focus on body
Button that moves the camera to tightly frame the body at the current orbit direction. Useful after zooming out to explore the full voxel environment.

### Live recompute on body movement
WASD movement triggers debounced recompute (200ms). Same for arrow-key antenna nudge. Computing overlay shows while the request is in flight.

### Loading spinner for recomputation
"Computing..." overlay with spinner displayed during all dosimetry fetch calls. Disappears when the response arrives. Does not block camera interaction (pointer-events: none).
