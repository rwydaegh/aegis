// Shared types for the AnnotationCanvas component and its helpers.

export interface Point {
  x: number
  y: number
}

export interface Stroke {
  points: Point[]
}

export interface AnnotationCanvasHandle {
  getCompositeImage: () => Promise<Blob>
}

export const MIN_ZOOM = 1
export const MAX_ZOOM = 10
export const STROKE_COLOR = '#ff3333'
export const STROKE_WIDTH = 3
