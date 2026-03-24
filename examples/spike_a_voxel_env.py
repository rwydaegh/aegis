"""
Spike A: Voxel environment loading, material classification, and visualization.

Demonstrates the Python side of the voxel pipeline:
1. Load voxel JSON (from nodejs-voxelearth output, or generate synthetic)
2. Parse into numpy arrays
3. Classify materials by RGBA color
4. Render in browser (Plotly 3D scatter)

Once Google 3D Tiles are downloaded and voxelized, replace the synthetic
data with real voxel JSON files.

Usage
-----
    python examples/spike_a_voxel_env.py                    # synthetic scene
    python examples/spike_a_voxel_env.py --json voxels.json  # real data
"""

from __future__ import annotations

import argparse
import json
import time
import webbrowser
from pathlib import Path
from dataclasses import dataclass

import numpy as np


# ---------------------------------------------------------------------------
# Material classification from voxel color
# ---------------------------------------------------------------------------

@dataclass
class Material:
    name: str
    eps_r: float
    color_rgb: tuple[int, int, int]  # display color


MATERIALS = {
    "concrete": Material("concrete", 6.0, (180, 180, 180)),
    "asphalt": Material("asphalt", 5.0, (80, 80, 80)),
    "vegetation": Material("vegetation", 1.0, (40, 160, 40)),
    "water": Material("water", 80.0, (30, 100, 220)),
    "brick": Material("brick", 4.0, (180, 80, 50)),
    "glass": Material("glass", 6.5, (150, 200, 230)),
    "unknown": Material("unknown", 4.0, (200, 200, 200)),
}


def classify_material(r: int, g: int, b: int) -> str:
    """
    Classify a material from its RGB color.

    Heuristic rules based on photogrammetry color patterns:
    - Gray/brown (r~g~b) -> concrete
    - Dark gray -> asphalt
    - Green dominant -> vegetation
    - Blue dominant -> water
    - Red/terracotta -> brick
    """
    brightness = (int(r) + int(g) + int(b)) / 3

    # Check for strong color dominance
    max_c = max(int(r), int(g), int(b))
    min_c = min(int(r), int(g), int(b))
    saturation = (max_c - min_c) / max(max_c, 1)

    if saturation < 0.15:
        # Achromatic: concrete or asphalt based on brightness
        if brightness < 90:
            return "asphalt"
        return "concrete"

    # Chromatic colors
    if g > r and g > b and g - r > 20:
        return "vegetation"

    if b > r and b > g and b - r > 30:
        return "water"

    if r > g and r > b and r - g > 30:
        return "brick"

    # Light blue -> glass
    if b > 150 and g > 150 and r < g:
        return "glass"

    return "concrete"


# ---------------------------------------------------------------------------
# Voxel data loading
# ---------------------------------------------------------------------------

@dataclass
class VoxelScene:
    """A scene of colored voxels with material labels."""
    positions: np.ndarray   # (N, 3) world positions
    colors: np.ndarray      # (N, 4) RGBA 0-255
    materials: np.ndarray   # (N,) string labels
    voxel_size: float       # meters per voxel

    @property
    def n_voxels(self) -> int:
        return len(self.positions)

    def material_counts(self) -> dict[str, int]:
        unique, counts = np.unique(self.materials, return_counts=True)
        return dict(zip(unique, counts))

    @classmethod
    def from_json(
        cls,
        path: str | Path,
        voxel_size: float = 1.0,
        max_voxels: int | None = None,
        use_world_coords: bool = True,
    ) -> VoxelScene:
        """Load from nodejs-voxelearth JSON output.

        Parameters
        ----------
        path : path to JSON file
        voxel_size : meters per voxel (for local coords)
        max_voxels : subsample to this many voxels if set
        use_world_coords : use wx/wy/wz (ECEF) instead of x/y/z (local grid)
        """
        with open(str(path)) as f:
            data = json.load(f)

        voxels = data if isinstance(data, list) else data.get("voxels", [])

        # Subsample if too many voxels
        if max_voxels and len(voxels) > max_voxels:
            step = len(voxels) // max_voxels
            voxels = voxels[::step][:max_voxels]

        n = len(voxels)
        positions = np.zeros((n, 3))
        colors = np.zeros((n, 4), dtype=np.uint8)
        mat_labels = []

        for i, v in enumerate(voxels):
            if use_world_coords and "wx" in v:
                positions[i] = [v["wx"], v["wy"], v["wz"]]
            else:
                positions[i] = [
                    v.get("x", 0) * voxel_size,
                    v.get("y", 0) * voxel_size,
                    v.get("z", 0) * voxel_size,
                ]
            r = int(v.get("r", 128))
            g = int(v.get("g", 128))
            b = int(v.get("b", 128))
            a = int(v.get("a", 255))
            colors[i] = [r, g, b, a]
            mat_labels.append(classify_material(r, g, b))

        # Center positions (ECEF coords are huge, need local frame)
        center = positions.mean(axis=0)
        positions -= center

        return cls(
            positions=positions,
            colors=colors,
            materials=np.array(mat_labels),
            voxel_size=voxel_size,
        )

    @classmethod
    def synthetic_urban(cls, size: int = 40, voxel_size: float = 1.0) -> VoxelScene:
        """Generate a synthetic urban scene for testing."""
        rng = np.random.default_rng(42)
        voxels_pos = []
        voxels_rgb = []

        # Ground plane (asphalt)
        for x in range(-size, size):
            for y in range(-size, size):
                voxels_pos.append([x, y, 0])
                gray = rng.integers(60, 100)
                voxels_rgb.append([gray, gray, gray, 255])

        # Buildings (concrete blocks)
        buildings = [
            ((-15, -10), (5, 8), 12),
            ((8, -12), (6, 10), 18),
            ((-8, 10), (7, 5), 8),
            ((12, 8), (4, 6), 15),
            ((-20, -20), (8, 4), 10),
        ]
        for (bx, by), (bw, bh), height in buildings:
            for x in range(bx, bx + bw):
                for y in range(by, by + bh):
                    for z in range(1, height + 1):
                        voxels_pos.append([x, y, z])
                        # Walls are concrete gray, some brick
                        if rng.random() < 0.2:
                            voxels_rgb.append([180 + rng.integers(-20, 20),
                                               80 + rng.integers(-10, 10),
                                               50 + rng.integers(-10, 10), 255])
                        else:
                            gray = rng.integers(150, 210)
                            voxels_rgb.append([gray, gray, gray + rng.integers(-10, 10), 255])

        # Trees (vegetation)
        tree_positions = [(-5, 5), (5, -5), (-18, 15), (20, -15), (0, 20)]
        for tx, ty in tree_positions:
            # Trunk
            for z in range(1, 5):
                voxels_pos.append([tx, ty, z])
                voxels_rgb.append([100, 70, 40, 255])
            # Canopy (sphere-ish)
            for dx in range(-3, 4):
                for dy in range(-3, 4):
                    for dz in range(-2, 4):
                        if dx*dx + dy*dy + dz*dz <= 10:
                            voxels_pos.append([tx + dx, ty + dy, 5 + dz])
                            g = rng.integers(100, 200)
                            voxels_rgb.append([30 + rng.integers(0, 30), g, 20 + rng.integers(0, 30), 255])

        positions = np.array(voxels_pos, dtype=np.float64) * voxel_size
        colors = np.array(voxels_rgb, dtype=np.uint8)

        mat_labels = [classify_material(c[0], c[1], c[2]) for c in colors]

        return cls(
            positions=positions,
            colors=colors,
            materials=np.array(mat_labels),
            voxel_size=voxel_size,
        )


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def render_voxel_scene(
    scene: VoxelScene,
    out_path: Path,
    title: str = "Voxel environment",
) -> None:
    """Render voxel scene as interactive Plotly 3D scatter."""
    import plotly.graph_objects as go

    pos = scene.positions
    colors = scene.colors

    # Color strings
    color_strs = [
        f"rgb({c[0]},{c[1]},{c[2]})"
        for c in colors
    ]

    hover = [
        f"({p[0]:.0f}, {p[1]:.0f}, {p[2]:.0f})<br>"
        f"Material: {m}<br>"
        f"RGB: ({c[0]}, {c[1]}, {c[2]})"
        for p, m, c in zip(pos, scene.materials, colors)
    ]

    scatter = go.Scatter3d(
        x=pos[:, 0],
        y=pos[:, 1],
        z=pos[:, 2],
        mode="markers",
        marker=dict(
            size=3,
            color=color_strs,
            opacity=0.9,
        ),
        hovertext=hover,
        hoverinfo="text",
    )

    mat_counts = scene.material_counts()
    counts_str = " | ".join(f"{k}: {v}" for k, v in sorted(mat_counts.items()))

    fig = go.Figure(data=[scatter])
    fig.update_layout(
        title=dict(
            text=(
                f"{title}<br>"
                f"<span style='font-size:12px;color:#888'>"
                f"{scene.n_voxels:,} voxels | {counts_str}</span>"
            ),
            x=0.5,
            font=dict(size=16),
        ),
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title="Z (m)",
            aspectmode="data",
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=0.8),
                up=dict(x=0, y=0, z=1),
            ),
            bgcolor="rgb(20,20,25)",
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        width=1200,
        height=900,
        paper_bgcolor="rgb(20,20,25)",
        font_color="white",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path), include_plotlyjs=True)
    print(f"  Wrote: {out_path}")


def render_material_map(
    scene: VoxelScene,
    out_path: Path,
) -> None:
    """Render voxels colored by classified material (not original color)."""
    import plotly.graph_objects as go

    pos = scene.positions

    # Color by material
    mat_colors = {
        "concrete": "rgb(180,180,180)",
        "asphalt": "rgb(80,80,80)",
        "vegetation": "rgb(40,180,40)",
        "water": "rgb(30,100,220)",
        "brick": "rgb(200,80,50)",
        "glass": "rgb(150,210,240)",
        "unknown": "rgb(200,200,200)",
    }

    color_strs = [mat_colors.get(m, "rgb(200,200,200)") for m in scene.materials]

    scatter = go.Scatter3d(
        x=pos[:, 0],
        y=pos[:, 1],
        z=pos[:, 2],
        mode="markers",
        marker=dict(size=3, color=color_strs, opacity=0.9),
        hovertext=[f"Material: {m}" for m in scene.materials],
        hoverinfo="text",
    )

    fig = go.Figure(data=[scatter])
    fig.update_layout(
        title=dict(
            text="Material classification from voxel color",
            x=0.5,
            font=dict(size=16),
        ),
        scene=dict(
            xaxis_title="X (m)",
            yaxis_title="Y (m)",
            zaxis_title="Z (m)",
            aspectmode="data",
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.8), up=dict(x=0, y=0, z=1)),
            bgcolor="rgb(20,20,25)",
        ),
        margin=dict(l=0, r=0, t=80, b=0),
        width=1200,
        height=900,
        paper_bgcolor="rgb(20,20,25)",
        font_color="white",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path), include_plotlyjs=True)
    print(f"  Wrote: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Spike A: voxel environment pipeline")
    parser.add_argument("--json", default=None, help="Path to voxel JSON file")
    parser.add_argument("--size", type=int, default=30, help="Synthetic scene half-size")
    parser.add_argument("--voxel-size", type=float, default=1.0, help="Meters per voxel")
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    out_dir = root / "examples" / "_output"

    print("=" * 60)
    print("  SPIKE A: Voxel environment pipeline")
    print("=" * 60)

    if args.json:
        print(f"\nLoading voxel JSON: {args.json}")
        t0 = time.perf_counter()
        scene = VoxelScene.from_json(args.json, voxel_size=args.voxel_size)
        t_load = time.perf_counter() - t0
        print(f"  {scene.n_voxels:,} voxels loaded in {t_load*1e3:.0f} ms")
    else:
        print(f"\nGenerating synthetic urban scene (size={args.size})...")
        t0 = time.perf_counter()
        scene = VoxelScene.synthetic_urban(size=args.size, voxel_size=args.voxel_size)
        t_gen = time.perf_counter() - t0
        print(f"  {scene.n_voxels:,} voxels generated in {t_gen*1e3:.0f} ms")

    # Material classification report
    print("\nMaterial classification:")
    for mat, count in sorted(scene.material_counts().items()):
        pct = count / scene.n_voxels * 100
        eps_r = MATERIALS[mat].eps_r if mat in MATERIALS else "?"
        print(f"  {mat:<15s} {count:>6,}  ({pct:5.1f}%)  eps_r={eps_r}")

    # Render original colors
    print("\nRendering original-color view...")
    out_orig = out_dir / "spike_a_voxels_original.html"
    t0 = time.perf_counter()
    render_voxel_scene(scene, out_orig, title="Spike A: Voxel environment (original color)")
    print(f"  Render time: {time.perf_counter() - t0:.1f} s")

    # Render material classification
    print("Rendering material-classified view...")
    out_mat = out_dir / "spike_a_voxels_materials.html"
    t0 = time.perf_counter()
    render_material_map(scene, out_mat)
    print(f"  Render time: {time.perf_counter() - t0:.1f} s")

    if not args.no_open:
        webbrowser.open(str(out_orig))

    print("\nDone.")
    print(f"\nNext steps for real data:")
    print(f"  1. Get Google Maps API key (3D Tiles API)")
    print(f"  2. Download tiles: python 3dtiles-dl/scripts/download_tiles.py ...")
    print(f"  3. Voxelize: node nodejs-voxelearth/voxelize_tiles.js tiles/ voxels/ 200")
    print(f"  4. Re-run: python examples/spike_a_voxel_env.py --json voxels/output.json")


if __name__ == "__main__":
    main()
