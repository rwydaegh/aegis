import { useEffect, useMemo, useRef } from 'react'
import * as THREE from 'three'
import { toScene } from '@/api/coordinates'
import { useStudioStore } from '../store'
import { useStudioScales } from '../useStudioScales'
import { colormapRgb } from './studioHelpers'
import { scaleNormalise } from './colorScale'

// The focal lobe rendered as a 3D field cloud: one small cube per voxel of the
// reconstructed field-volume box whose power density clears the declutter
// threshold, coloured by the studio colormap. The box arrives in server Z-up
// metres (origin = min-corner voxel centre, isotropic spacing); each voxel
// centre is converted to scene Y-up via toScene (a rigid axis permutation, so
// the cube size is preserved).
//
// Returns null while the cloud is off or no volume has been fetched, so the
// component is cheap to keep mounted.
export default function StudioVolume() {
  const volumeResult = useStudioStore((s) => s.volumeResult)
  const threshold = useStudioStore((s) => s.volumeThreshold)
  const opacity = useStudioStore((s) => s.volumeOpacity)
  const { volume: scale } = useStudioScales()

  const meshRef = useRef<THREE.InstancedMesh>(null)

  // Select the above-threshold voxels and precompute their scene-space centres
  // and colours. Keyed on the inputs that change the cloud; the per-instance
  // matrices/colours are written into the InstancedMesh in the effect below.
  const cloud = useMemo(() => {
    if (!volumeResult) return null
    const { scalar, shape, origin, spacing, vmax } = volumeResult
    const [nx, ny, nz] = shape
    // The declutter cut stays a fraction of THIS box's own peak (intuitive), while
    // the colour mapping follows the resolved (possibly shared / robust) scale.
    const cut = vmax * Math.min(Math.max(threshold, 0), 1)

    const centres: [number, number, number][] = []
    const colours: [number, number, number][] = []
    // scalar is row-major [i, j, k] with i->x, j->y, k->z.
    let flat = 0
    for (let i = 0; i < nx; i++) {
      for (let j = 0; j < ny; j++) {
        for (let k = 0; k < nz; k++, flat++) {
          const v = scalar[flat]
          if (!(v >= cut) || v <= 0) continue
          const server: [number, number, number] = [
            origin[0] + i * spacing,
            origin[1] + j * spacing,
            origin[2] + k * spacing,
          ]
          centres.push(toScene(server))
          const t = scaleNormalise(v, scale)
          const [r, g, b] = colormapRgb(scale.colormap, t)
          colours.push([r / 255, g / 255, b / 255])
        }
      }
    }
    return { centres, colours, spacing }
  }, [volumeResult, threshold, scale])

  // Push the instance matrices and colours into the mesh once the cloud changes.
  useEffect(() => {
    const mesh = meshRef.current
    if (!mesh || !cloud) return
    const m = new THREE.Matrix4()
    const c = new THREE.Color()
    for (let n = 0; n < cloud.centres.length; n++) {
      m.makeTranslation(...cloud.centres[n])
      mesh.setMatrixAt(n, m)
      const [r, g, b] = cloud.colours[n]
      c.setRGB(r, g, b)
      mesh.setColorAt(n, c)
    }
    mesh.count = cloud.centres.length
    mesh.instanceMatrix.needsUpdate = true
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true
  }, [cloud])

  if (!cloud || cloud.centres.length === 0) return null

  // A voxel cube is drawn slightly smaller than the pitch so neighbours read as
  // distinct points rather than a solid block. Capacity is the full count so the
  // buffer never needs reallocation as the threshold changes.
  const side = cloud.spacing * 0.7
  return (
    <instancedMesh
      ref={meshRef}
      args={[undefined, undefined, cloud.centres.length]}
      frustumCulled={false}
      // Draw after the other translucent surfaces (slice, lobes) so the cloud
      // blends on top of them with a stable, angle-independent order.
      renderOrder={3}
    >
      <boxGeometry args={[side, side, side]} />
      <meshBasicMaterial transparent opacity={opacity} depthWrite={false} toneMapped={false} />
    </instancedMesh>
  )
}
