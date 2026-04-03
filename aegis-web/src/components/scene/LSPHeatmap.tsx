import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { useSimulationStore } from '../../stores/simulation'

// Viridis-inspired colormap
const COLORMAP: [number, number, number][] = [
  [68, 1, 84], [72, 35, 116], [64, 67, 135], [52, 94, 141],
  [41, 120, 142], [32, 144, 140], [34, 167, 132], [68, 190, 112],
  [121, 209, 81], [189, 222, 38], [253, 231, 37],
]

function interpolateColor(t: number): [number, number, number] {
  const idx = Math.min(t * (COLORMAP.length - 1), COLORMAP.length - 1.001)
  const lo = Math.floor(idx)
  const hi = Math.ceil(idx)
  const f = idx - lo
  return [
    Math.round(COLORMAP[lo][0] * (1 - f) + COLORMAP[hi][0] * f),
    Math.round(COLORMAP[lo][1] * (1 - f) + COLORMAP[hi][1] * f),
    Math.round(COLORMAP[lo][2] * (1 - f) + COLORMAP[hi][2] * f),
  ]
}

export function LSPHeatmap() {
  const visible = useSimulationStore((s) => s.lspHeatmapVisible)
  const data = useSimulationStore((s) => s.lspHeatmapData)
  const bounds = useSimulationStore((s) => s.lspHeatmapBounds)
  const range = useSimulationStore((s) => s.lspHeatmapRange)

  const texture = useMemo(() => {
    if (!data || data.length === 0) return null
    const h = data.length
    const w = data[0].length
    const canvas = document.createElement('canvas')
    canvas.width = w
    canvas.height = h
    const ctx = canvas.getContext('2d')!
    const imageData = ctx.createImageData(w, h)

    const [vmin, vmax] = range
    const span = vmax - vmin || 1

    for (let row = 0; row < h; row++) {
      for (let col = 0; col < w; col++) {
        const t = Math.max(0, Math.min(1, (data[h - 1 - row][col] - vmin) / span))
        const [r, g, b] = interpolateColor(t)
        const idx = (row * w + col) * 4
        imageData.data[idx] = r
        imageData.data[idx + 1] = g
        imageData.data[idx + 2] = b
        imageData.data[idx + 3] = 180
      }
    }

    ctx.putImageData(imageData, 0, 0)
    const tex = new THREE.CanvasTexture(canvas)
    tex.minFilter = THREE.LinearFilter
    tex.magFilter = THREE.LinearFilter
    return tex
  }, [data, range])

  useEffect(() => () => { texture?.dispose() }, [texture])

  if (!visible || !texture || !data) return null

  const [xMin, xMax, yMin, yMax] = bounds
  const width = xMax - xMin
  const depth = yMax - yMin
  const centerX = (xMin + xMax) / 2
  const centerZ = (yMin + yMax) / 2

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[centerX, 0.02, centerZ]}>
      <planeGeometry args={[width, depth]} />
      <meshBasicMaterial
        map={texture}
        transparent
        opacity={0.7}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  )
}
