"""
Spike viewer: Three.js-based 3D visualization with instanced cubes and layers.

Generates a self-contained HTML file with:
- Voxel environment as instanced cubes (not scatter dots)
- Body mesh with Sab heatmap
- Layer toggle buttons (by material, body, etc.)
- Proper lighting, camera controls, dark theme

Usage
-----
    python examples/spike_viewer.py
    python examples/spike_viewer.py --voxel-json path/to/merged.json
    python examples/spike_viewer.py --voxel-json path/to/merged.json --max-voxels 80000
"""

from __future__ import annotations

import argparse
import json
import struct
import time
import webbrowser
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def load_stl_binary(path: str | Path):
    with open(str(path), "rb") as f:
        f.read(80)
        n = struct.unpack("<I", f.read(4))[0]
        vertices = np.zeros((n, 3, 3), dtype=np.float64)
        normals = np.zeros((n, 3), dtype=np.float64)
        for i in range(n):
            normals[i] = struct.unpack("<3f", f.read(12))
            for j in range(3):
                vertices[i, j] = struct.unpack("<3f", f.read(12))
            f.read(2)
    centroids = np.mean(vertices, axis=1)
    nrm = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(nrm > 0, nrm, 1.0)
    return vertices, normals, centroids


def triangle_areas(vertices):
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    return 0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)


EPS_0 = 8.854187817e-12

def tissue_T0(eps_r, sigma, freq_hz):
    omega = 2 * np.pi * freq_hz
    eps_c = eps_r - 1j * sigma / (omega * EPS_0)
    n = np.sqrt(eps_c)
    if np.real(n) < 0:
        n = -n
    r = (1 - n) / (1 + n)
    return float(1 - abs(r) ** 2)


def classify_material(r, g, b):
    """Classify material from RGB using HSV color space."""
    import colorsys
    r, g, b = int(r), int(g), int(b)
    rf, gf, bf = r / 255, g / 255, b / 255
    h, s, v = colorsys.rgb_to_hsv(rf, gf, bf)
    hue = h * 360  # 0-360

    # Achromatic: low saturation
    if s < 0.08:
        if v < 0.35:
            return "asphalt"
        return "concrete"

    # Very dark regardless of hue
    if v < 0.15:
        return "asphalt"

    # Vegetation: hue 60-150 (green), require more saturation to avoid gray-green ground
    if 60 < hue < 150 and s > 0.15 and v > 0.2:
        return "vegetation"

    # Yellow-green (hue 40-60): vegetation only if clearly saturated
    if 40 < hue < 60 and s > 0.25 and v > 0.25:
        return "vegetation"

    # Brick/terracotta: hue 0-40 or 330-360 (red-orange range)
    if (hue < 40 or hue > 330) and s > 0.15:
        return "brick"

    # Blue: hue 160-280 - almost always shadow in photogrammetry
    if 160 < hue < 280:
        if s > 0.6 and v > 0.4:
            return "water"  # only deep saturated blue = actual water
        if s > 0.45 and v > 0.55:
            return "glass"  # bright blue = window/sky reflection
        return "concrete"  # everything else is shadowed surface

    # Low saturation with some color: still concrete/asphalt
    if s < 0.15:
        if v < 0.35:
            return "asphalt"
        return "concrete"

    # Moderate saturation warm tones (brownish buildings)
    if 20 < hue < 50 and s < 0.4:
        return "brick"

    return "concrete"


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

def ecef_to_enu_matrix(lon_deg, lat_deg):
    """Rotation matrix from ECEF to local East-North-Up at given lon/lat."""
    lon = np.radians(lon_deg)
    lat = np.radians(lat_deg)
    sl, cl = np.sin(lon), np.cos(lon)
    sp, cp = np.sin(lat), np.cos(lat)
    # Rows: East, North, Up
    return np.array([
        [-sl,       cl,      0  ],
        [-sp * cl, -sp * sl, cp ],
        [ cp * cl,  cp * sl, sp ],
    ])


def load_voxels(path, max_voxels=None):
    """Load voxel JSON, transform ECEF to local ENU, classify materials."""
    print(f"  Loading {path}...")
    with open(str(path)) as f:
        data = json.load(f)

    voxels = data if isinstance(data, list) else data.get("voxels", [])
    total = len(voxels)

    if max_voxels and total > max_voxels:
        step = total // max_voxels
        voxels = voxels[::step][:max_voxels]
        print(f"  Subsampled {total:,} -> {len(voxels):,} voxels")

    n = len(voxels)
    positions = np.zeros((n, 3))
    colors = np.zeros((n, 3), dtype=np.uint8)
    materials = []

    for i, v in enumerate(voxels):
        if "wx" in v:
            positions[i] = [v["wx"], v["wy"], v["wz"]]
        else:
            positions[i] = [v.get("x", 0), v.get("y", 0), v.get("z", 0)]
        r, g, b = int(v.get("r", 128)), int(v.get("g", 128)), int(v.get("b", 128))
        colors[i] = [r, g, b]
        materials.append(classify_material(r, g, b))

    # Transform ECEF to local ENU only if positions are in ECEF (huge numbers)
    has_ecef = any("wx" in v for v in voxels[:10])
    max_coord = np.abs(positions).max()
    is_ecef = has_ecef and max_coord > 100000  # ECEF coords are ~4-10 million
    if is_ecef:
        center_ecef = positions.mean(axis=0)
        positions -= center_ecef

        # ECEF center -> geodetic lon/lat for rotation
        # Approximate: lon = atan2(y, x), lat = atan2(z, sqrt(x²+y²))
        lon_rad = np.arctan2(center_ecef[1], center_ecef[0])
        lat_rad = np.arctan2(center_ecef[2], np.sqrt(center_ecef[0]**2 + center_ecef[1]**2))
        lon_deg = np.degrees(lon_rad)
        lat_deg = np.degrees(lat_rad)
        print(f"  ECEF center -> lon={lon_deg:.4f}, lat={lat_deg:.4f}")

        R = ecef_to_enu_matrix(lon_deg, lat_deg)
        positions = positions @ R.T  # Now: X=East, Y=North, Z=Up
        print(f"  Rotated to ENU: E=[{positions[:,0].min():.0f},{positions[:,0].max():.0f}] "
              f"N=[{positions[:,1].min():.0f},{positions[:,1].max():.0f}] "
              f"U=[{positions[:,2].min():.0f},{positions[:,2].max():.0f}]")
    else:
        center = positions.mean(axis=0)
        positions -= center

    return positions, colors, materials


def prepare_body_mesh(stl_path, k_hat, T_0, S_inc, offset=(0, 0, 0)):
    """Load STL, compute Sab, prepare for Three.js."""
    vertices, normals, centroids = load_stl_binary(stl_path)
    mu = normals @ (-np.array(k_hat))
    sab = S_inc * T_0 * np.maximum(0, mu)

    # Flatten vertices for Three.js BufferGeometry
    flat_v = vertices.reshape(-1, 3)
    flat_v += np.array(offset)

    # Per-vertex color from Sab (inferno colormap)
    from matplotlib.cm import inferno
    sab_norm = np.clip(sab / (S_inc * T_0), 0, 1)
    # Each face has 3 vertices, same color
    face_colors = inferno(sab_norm)[:, :3]
    vert_colors = np.repeat(face_colors, 3, axis=0)

    # Per-vertex normals (flat shading = face normal for each vertex)
    flat_n = np.repeat(normals, 3, axis=0)

    return flat_v, flat_n, vert_colors, sab


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def generate_html(
    voxel_positions=None,
    voxel_colors=None,
    voxel_materials=None,
    body_vertices=None,
    body_normals=None,
    body_colors=None,
    title="AEGIS Viewer",
    stats=None,
) -> str:
    """Generate self-contained Three.js HTML with embedded data."""

    # Prepare voxel data grouped by material
    material_groups = {}
    if voxel_positions is not None:
        for mat in set(voxel_materials):
            idx = [i for i, m in enumerate(voxel_materials) if m == mat]
            material_groups[mat] = {
                "positions": voxel_positions[idx].tolist(),
                "colors": voxel_colors[idx].tolist(),
                "count": len(idx),
            }

    # Prepare body mesh data
    body_data = None
    if body_vertices is not None:
        body_data = {
            "vertices": body_vertices.tolist(),
            "normals": body_normals.tolist(),
            "colors": body_colors.tolist(),
        }

    material_colors = {
        "concrete": [180, 180, 180],
        "asphalt": [80, 80, 80],
        "vegetation": [40, 160, 40],
        "water": [30, 100, 220],
        "brick": [200, 80, 50],
        "glass": [150, 210, 240],
        "unknown": [200, 200, 200],
    }

    stats_html = ""
    if stats:
        stats_html = "<br>".join(f"<small>{k}: {v}</small>" for k, v in stats.items())

    # Build layer button HTML
    layer_buttons = []
    for mat, grp in sorted(material_groups.items()):
        c = material_colors.get(mat, [200, 200, 200])
        layer_buttons.append(
            f'<button class="layer-btn active" data-layer="{mat}" '
            f'style="border-left: 4px solid rgb({c[0]},{c[1]},{c[2]})">'
            f'{mat} ({grp["count"]:,})</button>'
        )
    if body_data:
        layer_buttons.append(
            '<button class="layer-btn active" data-layer="body" '
            'style="border-left: 4px solid rgb(255,140,0)">'
            'body mesh</button>'
        )

    layer_buttons_html = "\n            ".join(layer_buttons)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ overflow: hidden; background: #111; color: #eee; font-family: 'Segoe UI', sans-serif; }}
        #panel {{
            position: absolute; top: 12px; left: 12px; z-index: 100;
            background: rgba(0,0,0,0.85); padding: 16px; border-radius: 8px;
            max-width: 280px; backdrop-filter: blur(8px);
        }}
        #panel h2 {{ font-size: 15px; color: #7eb4ff; margin-bottom: 8px; }}
        #stats {{ font-size: 11px; color: #888; line-height: 1.6; margin-bottom: 12px; }}
        .layer-btn {{
            display: block; width: 100%; text-align: left;
            background: #222; color: #ccc; border: 1px solid #444;
            padding: 6px 10px; margin: 3px 0; cursor: pointer;
            border-radius: 4px; font-size: 12px; transition: all 0.15s;
        }}
        .layer-btn:hover {{ background: #333; }}
        .layer-btn.active {{ background: #2a2a3a; color: #fff; border-color: #667eea; }}
        .layer-btn.inactive {{ opacity: 0.4; background: #1a1a1a; }}
        #color-mode {{
            margin-top: 10px; padding-top: 10px; border-top: 1px solid #333;
        }}
        #color-mode label {{ font-size: 12px; color: #aaa; }}
        select {{
            width: 100%; background: #222; color: #ccc; border: 1px solid #444;
            padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-top: 4px;
        }}
        #controls {{
            margin-top: 10px; padding-top: 10px; border-top: 1px solid #333;
        }}
        .ctrl-btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; border: none; padding: 6px 12px; cursor: pointer;
            border-radius: 4px; font-size: 12px; margin: 3px 2px;
        }}
        .ctrl-btn:hover {{ transform: translateY(-1px); box-shadow: 0 2px 6px rgba(102,126,234,0.4); }}
        .hint {{ font-size: 10px; color: #666; margin-top: 8px; }}
    </style>
    <script type="importmap">
    {{
        "imports": {{
            "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
            "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
        }}
    }}
    </script>
</head>
<body>
    <div id="panel">
        <h2>{title}</h2>
        <div id="stats">{stats_html}</div>
        <div><strong style="font-size:12px; color:#aaa;">Layers</strong></div>
        <div id="layers">
            {layer_buttons_html}
        </div>
        <div id="color-mode">
            <label>Voxel coloring</label>
            <select id="colorSelect">
                <option value="material">Material classification</option>
                <option value="original">Original color (photogrammetry)</option>
            </select>
        </div>
        <div id="controls">
            <button class="ctrl-btn" onclick="resetCamera()">Reset camera</button>
            <button class="ctrl-btn" onclick="toggleWireframe()">Wireframe</button>
        </div>
        <div class="hint">Mouse: orbit | Scroll: zoom | Right-click: pan</div>
    </div>

    <script type="module">
        import * as THREE from 'three';
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

        // Embedded data
        const MATERIAL_GROUPS = {json.dumps(material_groups)};
        const BODY_DATA = {json.dumps(body_data) if body_data else 'null'};
        const MATERIAL_COLORS = {json.dumps(material_colors)};

        let scene, camera, renderer, controls;
        let voxelMeshes = {{}};  // material -> {{ original: InstancedMesh, classified: InstancedMesh }}
        let bodyMesh = null;
        let wireframe = false;
        let colorMode = 'material';

        init();
        buildScene();
        animate();

        function init() {{
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x111115);

            camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 5000);
            camera.position.set(150, 120, 150);

            renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 1.2;
            document.body.appendChild(renderer.domElement);

            controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.minDistance = 2;
            controls.maxDistance = 2000;

            // Lighting
            const ambient = new THREE.AmbientLight(0x404050, 0.6);
            scene.add(ambient);

            const sun = new THREE.DirectionalLight(0xfff5e6, 1.2);
            sun.position.set(100, 200, 80);
            sun.castShadow = true;
            sun.shadow.mapSize.width = 2048;
            sun.shadow.mapSize.height = 2048;
            scene.add(sun);

            const fill = new THREE.DirectionalLight(0x6688cc, 0.4);
            fill.position.set(-30, 20, -40);
            scene.add(fill);

            const hemi = new THREE.HemisphereLight(0x8899bb, 0x444422, 0.3);
            scene.add(hemi);

            // Ground grid
            const grid = new THREE.GridHelper(600, 60, 0x333333, 0x222222);
            grid.position.y = -1;
            scene.add(grid);

            window.addEventListener('resize', () => {{
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            }});
        }}

        function buildScene() {{
            const geometry = new THREE.BoxGeometry(0.95, 0.95, 0.95);
            const dummy = new THREE.Object3D();
            const color = new THREE.Color();

            let allPositions = [];

            // Build voxel layers
            for (const [mat, data] of Object.entries(MATERIAL_GROUPS)) {{
                const n = data.count;
                const mc = MATERIAL_COLORS[mat] || [200, 200, 200];

                // Original color mesh
                const matOrig = new THREE.MeshStandardMaterial({{
                    roughness: 0.85, metalness: 0.05, flatShading: true,
                }});
                const meshOrig = new THREE.InstancedMesh(geometry, matOrig, n);
                meshOrig.castShadow = true;
                meshOrig.receiveShadow = true;

                // Classified color mesh (initially hidden)
                const matClass = new THREE.MeshStandardMaterial({{
                    color: new THREE.Color(mc[0]/255, mc[1]/255, mc[2]/255),
                    roughness: 0.85, metalness: 0.05, flatShading: true,
                }});
                const meshClass = new THREE.InstancedMesh(geometry, matClass, n);
                meshClass.castShadow = true;
                meshClass.receiveShadow = true;
                meshOrig.visible = false;

                for (let i = 0; i < n; i++) {{
                    const p = data.positions[i];
                    dummy.position.set(p[0], p[1], p[2]);  // Already in local coords (X, Y=up, Z)
                    dummy.updateMatrix();
                    meshOrig.setMatrixAt(i, dummy.matrix);
                    meshClass.setMatrixAt(i, dummy.matrix);

                    const c = data.colors[i];
                    color.setRGB(c[0]/255, c[1]/255, c[2]/255);
                    meshOrig.setColorAt(i, color);

                    allPositions.push([p[0], p[2], -p[1]]);
                }}

                meshOrig.instanceMatrix.needsUpdate = true;
                if (meshOrig.instanceColor) meshOrig.instanceColor.needsUpdate = true;
                meshClass.instanceMatrix.needsUpdate = true;

                scene.add(meshOrig);
                scene.add(meshClass);
                voxelMeshes[mat] = {{ original: meshOrig, classified: meshClass }};
            }}

            // Build body mesh
            if (BODY_DATA) {{
                const verts = BODY_DATA.vertices;
                const norms = BODY_DATA.normals;
                const cols = BODY_DATA.colors;
                const n = verts.length;

                const geom = new THREE.BufferGeometry();
                const posArr = new Float32Array(n * 3);
                const normArr = new Float32Array(n * 3);
                const colArr = new Float32Array(n * 3);

                for (let i = 0; i < n; i++) {{
                    // Swap Y/Z for Three.js Y-up
                    posArr[i*3]   = verts[i][0];
                    posArr[i*3+1] = verts[i][2];
                    posArr[i*3+2] = -verts[i][1];
                    normArr[i*3]   = norms[i][0];
                    normArr[i*3+1] = norms[i][2];
                    normArr[i*3+2] = -norms[i][1];
                    colArr[i*3]   = cols[i][0];
                    colArr[i*3+1] = cols[i][1];
                    colArr[i*3+2] = cols[i][2];

                    allPositions.push([verts[i][0], verts[i][2], -verts[i][1]]);
                }}

                geom.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
                geom.setAttribute('normal', new THREE.BufferAttribute(normArr, 3));
                geom.setAttribute('color', new THREE.BufferAttribute(colArr, 3));

                const bodyMat = new THREE.MeshStandardMaterial({{
                    vertexColors: true, roughness: 0.6, metalness: 0.1,
                    side: THREE.DoubleSide,
                }});
                bodyMesh = new THREE.Mesh(geom, bodyMat);
                bodyMesh.castShadow = true;
                scene.add(bodyMesh);
            }}

            // Center camera on scene
            if (allPositions.length > 0) {{
                let cx = 0, cy = 0, cz = 0;
                for (const p of allPositions) {{
                    cx += p[0]; cy += p[1]; cz += p[2];
                }}
                cx /= allPositions.length;
                cy /= allPositions.length;
                cz /= allPositions.length;

                controls.target.set(cx, cy, cz);

                // Estimate scene size
                let maxDist = 0;
                for (const p of allPositions) {{
                    const d = Math.sqrt((p[0]-cx)**2 + (p[1]-cy)**2 + (p[2]-cz)**2);
                    if (d > maxDist) maxDist = d;
                }}
                const dist = maxDist * 1.5;
                camera.position.set(cx + dist * 0.7, cy + dist * 0.5, cz + dist * 0.7);
            }}
        }}

        // Layer toggles
        document.querySelectorAll('.layer-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const layer = btn.dataset.layer;
                const isActive = btn.classList.contains('active');

                if (isActive) {{
                    btn.classList.remove('active');
                    btn.classList.add('inactive');
                }} else {{
                    btn.classList.remove('inactive');
                    btn.classList.add('active');
                }}

                if (layer === 'body') {{
                    if (bodyMesh) bodyMesh.visible = !isActive;
                }} else if (voxelMeshes[layer]) {{
                    const show = !isActive;
                    if (colorMode === 'original') {{
                        voxelMeshes[layer].original.visible = show;
                        voxelMeshes[layer].classified.visible = false;
                    }} else {{
                        voxelMeshes[layer].original.visible = false;
                        voxelMeshes[layer].classified.visible = show;
                    }}
                }}
            }});
        }});

        // Color mode switch
        document.getElementById('colorSelect').addEventListener('change', (e) => {{
            colorMode = e.target.value;
            for (const [mat, meshes] of Object.entries(voxelMeshes)) {{
                const btn = document.querySelector(`.layer-btn[data-layer="${{mat}}"]`);
                const isActive = btn && btn.classList.contains('active');
                if (colorMode === 'original') {{
                    meshes.original.visible = isActive;
                    meshes.classified.visible = false;
                }} else {{
                    meshes.original.visible = false;
                    meshes.classified.visible = isActive;
                }}
            }}
        }});

        // Controls
        window.resetCamera = () => controls.reset();
        window.toggleWireframe = () => {{
            wireframe = !wireframe;
            for (const meshes of Object.values(voxelMeshes)) {{
                meshes.original.material.wireframe = wireframe;
                meshes.classified.material.wireframe = wireframe;
            }}
            if (bodyMesh) bodyMesh.material.wireframe = wireframe;
        }};

        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }}
    </script>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="AEGIS Three.js viewer")
    parser.add_argument("--stl", default=None)
    parser.add_argument("--voxel-json", default=None)
    parser.add_argument("--max-voxels", type=int, default=80000)
    parser.add_argument("--sinc", type=float, default=10.0)
    parser.add_argument("--freq", type=float, default=28e9)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    data_dir = root.parent / "data"
    stl_path = Path(args.stl) if args.stl else data_dir / "thelonious.stl"
    out_dir = root / "examples" / "_output"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  AEGIS Three.js Viewer")
    print("=" * 60)

    stats = {}

    # Load voxels
    voxel_positions = voxel_colors = voxel_materials = None
    if args.voxel_json:
        print("\nLoading voxels...")
        t0 = time.perf_counter()
        voxel_positions, voxel_colors, voxel_materials = load_voxels(
            args.voxel_json, max_voxels=args.max_voxels
        )
        t_load = time.perf_counter() - t0
        print(f"  {len(voxel_positions):,} voxels in {t_load:.1f}s")

        # Material counts
        from collections import Counter
        mat_counts = Counter(voxel_materials)
        for mat, count in sorted(mat_counts.items()):
            stats[mat] = f"{count:,} voxels"

    # Load body mesh
    body_vertices = body_normals = body_colors = None
    if stl_path.exists():
        print("\nLoading body mesh...")
        eps_r, sigma = 17.0, 25.0
        T_0 = tissue_T0(eps_r, sigma, args.freq)
        k_hat = [0.0, -1.0, 0.0]

        t0 = time.perf_counter()
        body_vertices, body_normals, body_colors, sab = prepare_body_mesh(
            stl_path, k_hat, T_0, args.sinc
        )
        t_load = time.perf_counter() - t0
        n_tri = len(body_vertices) // 3
        stats["body"] = f"{n_tri:,} triangles"
        stats["peak Sab"] = f"{np.max(sab):.3f} W/m²"
        stats["T0"] = f"{T_0:.4f}"
        print(f"  {n_tri:,} triangles in {t_load:.1f}s")

    # Generate HTML
    print("\nGenerating Three.js viewer...")
    t0 = time.perf_counter()
    html = generate_html(
        voxel_positions=voxel_positions,
        voxel_colors=voxel_colors,
        voxel_materials=voxel_materials,
        body_vertices=body_vertices,
        body_normals=body_normals,
        body_colors=body_colors,
        title="AEGIS Viewer",
        stats=stats,
    )

    out_path = out_dir / "spike_viewer.html"
    with open(str(out_path), "w") as f:
        f.write(html)
    t_gen = time.perf_counter() - t0
    file_size_mb = out_path.stat().st_size / 1e6
    print(f"  Wrote: {out_path}")
    print(f"  Size: {file_size_mb:.1f} MB, generated in {t_gen:.1f}s")

    if not args.no_open:
        webbrowser.open(str(out_path))

    print("\nDone.")


if __name__ == "__main__":
    main()
