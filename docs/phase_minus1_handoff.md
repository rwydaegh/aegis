# Phase -1 hand-off: spike / proof of concept

This document summarizes all work done in Phase -1 of the AEGIS project. The goal was to validate two core capabilities before investing in architecture: (A) loading a real-world 3D environment from Google Maps, and (B) computing and rendering a dosimetry heatmap on a human body mesh.

Both spikes are complete. The decision point is resolved: Three.js with instanced rendering is the frontend approach for visualization.

## What was built

### Pipeline overview

```
Google Maps 3D Tiles API
        |
        v
   3dtiles-dl          (Python, downloads GLB tiles)
        |
        v
  nodejs-voxelearth    (Node.js, voxelizes GLB meshes)
        |
        v
   merged.json         (voxel grid: x,y,z,r,g,b per voxel)
        |
        v
  spike_viewer.py      (Python, generates Three.js HTML)
        |
        v
  spike_viewer.html    (self-contained 3D viewer in browser)
```

### Repository layout

```
Geometric Dosimetry/
  aegis/                          <-- main AEGIS package
    examples/
      spike_a_voxel_env.py        Spike A: voxel environment (Plotly version)
      spike_b_heatmap.py          Spike B: dosimetry heatmap on body mesh
      spike_combined.py           Combined A+B in one Plotly scene
      spike_viewer.py             Production Three.js viewer (replaces all above)
      _output/                    Generated HTML viewers and screenshots
    src/aegis/                    Package skeleton (Phase 0)
    tests/                        Test skeleton (Phase 0)
    docs/                         This document
  3dtiles-dl/                     Google 3D Tiles downloader
    src/tile_api.py               Tile hierarchy traversal + OBB culling
    src/wgs84.py                  WGS84/ECEF coordinate transforms
    src/threaded_api.py           Parallel download CLI
  nodejs-voxelearth/              Voxelization pipeline
    run_pipeline.js               One-command pipeline (download + voxelize)
    tile_downloader.js            BFS tile download with bounding volume culling
    voxelize_tiles.js             GLB to voxel conversion orchestrator
    voxelizer.worker.js           Ray-casting voxelizer (54 KB, the heavy lifter)
    visualizer.html               Standalone Three.js voxel viewer
  data/
    Thelonious.stl                Human body phantom (23,826 triangles)
  monograph/                      Theory (LaTeX, single source of truth)
  scripts/                        40+ research scripts (oracle/ground truth)
```

## Spike A: voxel environment

### Goal

Load a real-world 3D scene from Google Maps, voxelize it, classify materials by color, and render it in a browser.

### How it works

1. **Tile download** (`3dtiles-dl`): Given a lat/lon center and radius, downloads GLB tiles from Google's Map Tiles API. Uses BFS traversal of the tile hierarchy with oriented bounding box culling to fetch only tiles within the radius. Parallel downloads (4 workers). Output: individual `.glb` files.

2. **Voxelization** (`nodejs-voxelearth`): For each GLB tile, loads the mesh via Three.js GLTFLoader, decodes textures (sharp + jpeg-js), and ray-casts at a configurable resolution (default 200 rays per axis) to produce a voxel grid. Each voxel stores world coordinates (wx, wy, wz) and sampled color (r, g, b, a). Output: per-tile `_voxels.json` files, merged into `merged.json`.

3. **Material classification**: Each voxel's RGB color is converted to HSV and classified:

   | Material   | Hue range     | Saturation  | Value      | eps_r |
   |-----------|---------------|-------------|------------|-------|
   | Asphalt   | any           | < 0.08      | < 0.35     | ~5    |
   | Concrete  | any           | < 0.08      | >= 0.35    | ~6    |
   | Vegetation| 40-160 (green)| > 0.15      | > 0.2      | ~1    |
   | Brick     | 0-40, 330-360 | > 0.15      | any        | ~4    |
   | Glass     | 200-260 (blue)| > 0.45      | > 0.55     | ~6    |
   | Water     | 200-260 (blue)| > 0.6       | > 0.4      | ~80   |

   Key insight: most blue in photogrammetry is shadow on concrete, not water. The classifier is conservative about water (requires deep saturation > 0.6) because misclassifying shadow as water produces eps_r = 80 instead of 6, a 13x error in dielectric constant.

4. **Rendering** (`spike_viewer.py`): Generates a self-contained HTML file with Three.js. Voxels are rendered as instanced cubes (0.95 scale to prevent z-fighting). The viewer supports layer toggles, color mode switching (original photogrammetry colors vs. material classification), and orbit controls.

### Test scene

The test scene is a ~40m radius around (51.0228, 3.7106) in Ghent, Belgium. Contains a large building, trees, sidewalks, and road. 271,913 voxels total (subsampled to 150k for browser performance).

Classification on the Ghent scene:

| Material   | Percentage |
|-----------|-----------|
| Concrete  | 39%       |
| Asphalt   | 26%       |
| Vegetation| 15%       |
| Brick     | 8%        |
| Glass     | 1%        |
| Water     | < 1%      |

### Known limitations

- **Tile gaps**: Some tiles don't perfectly align in world coordinates, leaving small gaps between chunks. This is a coordinate transform issue in the voxelizer (WGS84 to local frame). Not a blocker for dosimetry since the voxels are used for ray-tracing obstruction, not watertight geometry.
- **Resolution vs. performance**: 200 resolution produces ~272k voxels for a 40m radius. The Three.js viewer handles 150k instanced cubes smoothly. Beyond 300k, browser performance degrades.
- **Material classification is approximate**: Color-based classification cannot distinguish, for example, painted concrete from brick. For AEGIS this is acceptable because the dielectric constants of common building materials are within 2x of each other (eps_r 4-8), and the dominant factor in dosimetry is geometry (angle of incidence, obstruction), not material.

## Spike B: dosimetry heatmap

### Goal

Compute absorbed power density (Sab) on a human body mesh and render it as a heatmap.

### How it works

1. **Load body mesh**: Reads `Thelonious.stl` (5 MB, 23,826 triangles). Computes face normals and centroids.

2. **Compute Sab**: For a single plane wave with incident power density S_inc and propagation direction k_hat:

   ```
   Sab(r) = S_inc * T_0(theta) * max(0, n_hat(r) . (-k_hat))
   ```

   Where:
   - `n_hat(r)` is the outward surface normal at each face
   - `theta` is the angle between the surface normal and the wave direction
   - `T_0(theta)` is the Fresnel power transmission coefficient for unpolarized light at the skin-air interface (computed from the monograph's tissue model)

3. **Fresnel transmission**: Uses the monograph's tissue parameters for skin at the target frequency. Computes parallel and perpendicular polarization transmission coefficients, then averages them for unpolarized incidence. This is extracted from `scripts/_fresnel.py`.

4. **Rendering**: Per-face coloring using the inferno colormap, normalized to peak Sab. Rendered as Plotly Mesh3d (Spike B standalone) or Three.js mesh (combined viewer).

### Validation

- Peak Sab = 5.39 W/m^2 at S_inc = 10 W/m^2 (consistent with Fresnel loss and oblique incidence)
- Sab >= 0 everywhere (ReLU enforced)
- Back-facing triangles correctly have Sab = 0
- Results match `scripts/apd_pipeline.py` output

## Spike viewer (combined)

The final viewer (`spike_viewer.py`) combines both spikes in a single Three.js scene:

- Voxel environment rendered as instanced cubes
- Body mesh rendered with dosimetry heatmap (inferno colormap)
- Layer toggles: show/hide environment, body, individual materials
- Color modes: original photogrammetry colors, material classification
- Orbit controls (left-drag rotate, right-drag pan, scroll zoom)
- Dark theme, sidebar with material statistics
- Self-contained HTML (no external dependencies, Three.js loaded from CDN)

### Running the viewer

```bash
# Full pipeline from scratch (requires Google Maps API key):
cd nodejs-voxelearth
node run_pipeline.js --key YOUR_API_KEY --lat 51.0228 --lng 3.7106 --radius 40 --out pipeline_street --resolution 150

# Generate the viewer:
cd aegis
py -3.12 examples/spike_viewer.py \
    --voxel-json "../nodejs-voxelearth/pipeline_street/voxels/merged.json" \
    --max-voxels 150000

# Output: examples/_output/spike_viewer.html (open in browser)
```

### Command-line options

| Flag | Default | Description |
|------|---------|-------------|
| `--voxel-json` | (required) | Path to merged voxel JSON |
| `--stl` | `../../data/Thelonious.stl` | Path to body mesh STL |
| `--max-voxels` | 80000 | Max voxels to render (subsamples if exceeded) |
| `--no-open` | false | Don't auto-open browser |

## Technology decisions

### Three.js over Plotly

The project started with Plotly (scatter3d for voxels, mesh3d for body). Plotly is fast to prototype but produces poor voxel rendering (dots, not cubes) and struggles above 50k points. Three.js with instanced meshes handles 150k cubes at 60fps and produces actual solid geometry.

### VoxelEarth tools

We use two VoxelEarth-derived tools:

- **3dtiles-dl** (Python): Tile download and coordinate transforms. Thin wrapper around Google's Map Tiles API. The key contribution is BFS traversal with OBB culling.
- **nodejs-voxelearth** (Node.js): Voxelization of GLB meshes. The core algorithm is a ray-casting voxelizer that samples mesh textures. This is the part that turns photogrammetric meshes into a regular voxel grid suitable for ray tracing.

We do NOT use VoxelEarth's web viewer or Minecraft export. Those are downstream consumers of the voxel data that aren't relevant for AEGIS.

### HSV over RGB for classification

The initial RGB-based classifier assigned 86% of voxels to concrete. Switching to HSV with hue-based zones produces a realistic distribution (39% concrete, 26% asphalt, 15% vegetation). The critical fix was recognizing that blue-shifted shadows in photogrammetry are not water.

## API keys

The Google Maps API key is required for tile downloads. The Map Tiles API has a free tier (~25k tile requests/month). A 40m radius download uses ~12 tiles.

Keys used during development are not stored in the repository. Set them via command-line flags only.

## What comes next (Phase 1)

Phase -1 validated that the core loop works: real-world environment + body mesh + dosimetry computation + interactive visualization. Phase 1 extracts the physics into the `src/aegis/` package:

1. **Tissue module** (`src/aegis/tissue/`): Cole-Cole model, IT'IS database, Fresnel coefficients
2. **Geometry module** (`src/aegis/geometry/`): STL loading, normals, centroids, ambient occlusion
3. **Golden tests**: Monograph table values as regression tests
4. **Mie regression test**: CI canary for physics correctness

The spike scripts in `examples/` remain as integration tests and demos. The production code moves to `src/aegis/`.
