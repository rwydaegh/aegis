/**
 * Module-level camera state tracker for reading Three.js camera
 * position/target from outside the R3F canvas (e.g., share links).
 *
 * Updated every frame by CameraSyncer in SceneRoot. Plain object
 * (not Zustand) to avoid triggering React re-renders.
 */

export const cameraState = {
  position: [0, 2, 5] as [number, number, number],
  target: [0, 0.6, 0] as [number, number, number],
}
