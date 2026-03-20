# Ray tracing mesh optimization: what matters and what does not

**Date:** 2026-03-20

## Context

AEGIS builds an environment mesh for wireless channel ray tracing from Google 3D Tiles. The pipeline is:

1. Google 3D Tiles (dirty GLB meshes, not directly usable for RT)
2. Voxelization via Voxel Earth (regularizes geometry into clean axis-aligned blocks)
3. Greedy meshing (merges coplanar voxel faces into larger quads, reducing triangle count)
4. Ray tracing via DiffeRT

The greedy meshing step currently produces ~70,000 triangles from ~88,000 voxels. Two concerns prompted this investigation:

- The merged quads are very elongated (long skinny rectangles), a scan-order artifact of the greedy algorithm. Is this bad for ray tracing?
- All materials are merged into one monolithic "concrete" mesh. Is this a problem?

## What DiffeRT actually does

DiffeRT (by Jérome Eertmans, UCLouvain PhD project) is an independent differentiable ray tracer built on JAX. It is not a fork of Sionna. The only connection is that DiffeRT can parse Sionna's XML scene format.

DiffeRT's default path-finding method (`method="exhaustive"`) works as follows:

1. **Path candidate enumeration.** For order-K reflections with N triangles, enumerate all possible K-triangle sequences via `CompleteGraph.all_paths()` (implemented in Rust). This is O(N^K) candidates.
2. **Image method.** For each candidate path, compute the specular reflection points using mirror images.
3. **Obstruction check.** For each candidate path, test every ray segment against every triangle via Moller-Trumbore intersection, in batches of 512. No BVH, no KD-tree, no acceleration structure. Pure brute force, O(rays x triangles).

The "hybrid" mode pre-filters with SBR visibility estimation, but the core remains exhaustive. The "sbr" mode is marked unstable.

**Implication:** DiffeRT's compute cost scales as O(N^K) for path enumeration and O(N) for each obstruction check. Triangle count dominates everything. Triangle shape is irrelevant.

## What Sionna RT does (for comparison)

Sionna RT (NVIDIA) is built on Mitsuba 3 and calls `mi_scene.ray_intersect()` for all intersection tests. Mitsuba 3 has three backends, selected at compile time:

- **GPU (CUDA variants):** OptiX with hardware-accelerated BVH traversal on RTX cards
- **CPU (LLVM variants):** Intel Embree, which uses a high-performance BVH
- **CPU (scalar variants):** Built-in KD-tree

All three use spatial acceleration structures. Ray intersection is O(log N), not O(N). Triangle count still matters but logarithmically, and triangle shape affects BVH/KD-tree quality (elongated triangles produce overlapping bounding boxes, causing more traversal steps).

Sionna RT also supports specular reflection, diffuse scattering, refraction through thin surfaces, and first-order diffraction. DiffeRT currently supports specular reflection only.

## Conclusions

### Triangle shape does not matter for DiffeRT

The elongated quads from greedy meshing are not a problem. DiffeRT tests every ray against every triangle by brute force. Whether a triangle is 1x100 or 10x10 makes zero difference to intersection cost or correctness (Moller-Trumbore is exact regardless of aspect ratio). There is no BVH to degrade.

If AEGIS later switches to Sionna RT, triangle shape would matter slightly for BVH quality. But even then, the effect is modest (more BVH node traversals, not wrong results).

**Decision:** Do not implement the aspect-ratio balancing heuristic. It adds complexity for no benefit with DiffeRT, and marginal benefit with Sionna.

### Triangle count is critical for DiffeRT

Every triangle added to the scene increases:

- Path candidate count exponentially (O(N^K) for K bounces)
- Obstruction check cost linearly (O(N) per ray segment)

The greedy meshing is doing exactly the right thing: maximizing face merges to minimize triangle count. Going from ~500,000 triangles (raw voxel faces) to ~70,000 (greedy merged) is a 7x reduction that translates directly to 7x fewer obstruction tests and a 7^K reduction in path candidates.

**Decision:** Keep and improve the greedy meshing. Do not add features that increase triangle count without good reason.

### Materials must be preserved

The current greedy meshing ignores per-voxel material labels, assigning everything to "concrete". This is a correctness bug:

- Different materials have different electromagnetic properties (permittivity, conductivity)
- DiffeRT's `TriangleMesh.face_materials` field exists precisely for this purpose
- Material-unaware merging means a concrete wall touching a brick wall becomes one "concrete" quad, giving wrong reflection coefficients at the boundary

Material-aware merging will slightly increase triangle count (faces at material boundaries cannot be merged). This is an acceptable trade-off because the alternative is physically wrong results.

**Decision:** Implement material-aware greedy meshing. Only merge faces whose voxels share the same material.

### DiffeRT vs Sionna RT: feature and performance gap

| Aspect | DiffeRT | Sionna RT |
|--------|---------|-----------|
| Acceleration structure | None (brute force) | KD-tree / Embree BVH / OptiX HW BVH |
| Intersection complexity | O(N) per ray | O(log N) per ray |
| Path finding | Exhaustive O(N^K) | SBR + image method |
| Differentiability | JAX | Dr.Jit (Mitsuba 3) |
| Reflections | Specular only | Specular + diffuse |
| Diffraction | No | First-order (wedges) |
| Refraction | No | Thin surfaces |
| Scattering | No | Yes |
| GPU support | JAX (CPU/GPU/TPU) | OptiX (NVIDIA GPU) |
| Maturity | PhD project, API unstable | NVIDIA-backed, stable (v2.0) |

DiffeRT's main advantage is simplicity and JAX integration. Sionna RT is more feature-complete and performant for large scenes. For AEGIS's current needs (small urban scenes, specular reflections), DiffeRT works. For larger scenes or higher-order reflections, the O(N^K) scaling will become a bottleneck.

## Sources

- DiffeRT source: `differt` package installed at `Python312/Lib/site-packages/differt/`
- Sionna RT source: `github.com/NVlabs/sionna-rt`, inspected at `src/sionna/rt/`
- Mitsuba 3 source: `github.com/mitsuba-renderer/mitsuba3`, `include/mitsuba/render/scene.h`
- Eertmans' homepage: https://eertmans.be/
- Sionna RT technical report: https://arxiv.org/abs/2504.21719
- 0fps greedy meshing: https://0fps.net/2012/06/30/meshing-in-a-minecraft-game/
