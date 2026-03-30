# Things that are NOT bugs

Do not report, fix, or spend time investigating these.

## Browser/rendering noise

- ResizeObserver errors in console (browser internals, harmless)
- THREE.js deprecation warnings (upstream library, not our code)
- WebGL context loss on low-end GPUs (expected browser behavior)
- Console warnings about passive event listeners

## Known tradeoffs

- WASD camera movement precision (first-person mode is approximate)
- Overpass API timeouts on large radii (external service, we retry)
- Slow initial load of large phantom meshes (inherent to STL size)
- Compute time scaling with mesh resolution (physics, not a bug)

## Things Sentry already catches

- JavaScript unhandled exceptions and promise rejections
- 5xx server errors
- Do not file issues for JS errors, Sentry creates them automatically

## Physics edge cases that are correct

- Fresnel T_avg exceeding T0 near the pseudo-Brewster angle (~5-12% for lossy tissue).
  This is physically correct for TM polarization.
- Level 5 curvature_H can be negative (concave surfaces). This is intentional.
- Spatial averaging producing slightly different values than raw Sab. This is the
  point of spatial averaging.
