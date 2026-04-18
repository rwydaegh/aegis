import { useEffect, useMemo } from 'react'
import * as THREE from 'three'
import { useSimulationStore } from '../../stores/simulation'
import { useSceneStore } from '../../stores/scene'
import { useEnvironmentStore } from '../../stores/environment'
import { viridisColor } from '../../lib/colormap'

export function LSPHeatmap() {
  const pathSource = useSceneStore((s) => s.pathSource)
  const envSource = useEnvironmentStore((s) => s.source)
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
        const [r, g, b] = viridisColor(t)
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

  if (pathSource !== 'stochastic' || envSource !== 'none' || !visible || !texture || !data) return null

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
