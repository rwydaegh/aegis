"""Generate 3D visualizations of all 12 roof types and save as PNG files."""

import numpy as np
import plotly.graph_objects as go
from pathlib import Path

from aegis.environment.roofs import generate_building, _ROOF_DISPATCH
from aegis.environment import MaterialType

OUT_DIR = Path(__file__).parent / "roof_renders"
OUT_DIR.mkdir(exist_ok=True)

# Material colors for visualization
MAT_COLORS = {
    MaterialType.CONCRETE: "#A0A0A0",
    MaterialType.BRICK: "#B85C38",
    MaterialType.GLASS: "#87CEEB",
    MaterialType.METAL: "#C0C0C0",
    MaterialType.WOOD: "#DEB887",
}

# Two footprint shapes to test
QUAD_FOOTPRINT = np.array([
    [0, 0],
    [12, 0],
    [12, 8],
    [0, 8],
], dtype=np.float64)

PENTAGON_FOOTPRINT = np.array([
    [0, 0],
    [10, 0],
    [13, 6],
    [5, 10],
    [-3, 6],
], dtype=np.float64)

L_SHAPE_FOOTPRINT = np.array([
    [0, 0],
    [12, 0],
    [12, 4],
    [6, 4],
    [6, 8],
    [0, 8],
], dtype=np.float64)

ROOF_TYPES = list(_ROOF_DISPATCH.keys())
HEIGHT = 6.0
ROOF_HEIGHT = 3.0


def make_mesh_trace(verts, tris, mats, name="mesh"):
    """Create a plotly Mesh3d trace from vertices, triangles, materials."""
    # Color each face by material
    face_colors = []
    for m in mats:
        mt = MaterialType(m)
        face_colors.append(MAT_COLORS.get(mt, "#808080"))

    return go.Mesh3d(
        x=verts[:, 0],
        y=verts[:, 1],
        z=verts[:, 2],
        i=tris[:, 0],
        j=tris[:, 1],
        k=tris[:, 2],
        facecolor=face_colors,
        flatshading=True,
        lighting=dict(ambient=0.4, diffuse=0.6, specular=0.2),
        lightposition=dict(x=20, y=20, z=30),
        name=name,
    )


def make_wireframe_trace(verts, tris):
    """Create edge wireframe as a Scatter3d trace."""
    xe, ye, ze = [], [], []
    for tri in tris:
        for edge in [(0, 1), (1, 2), (2, 0)]:
            a, b = tri[edge[0]], tri[edge[1]]
            xe.extend([verts[a, 0], verts[b, 0], None])
            ye.extend([verts[a, 1], verts[b, 1], None])
            ze.extend([verts[a, 2], verts[b, 2], None])
    return go.Scatter3d(
        x=xe, y=ye, z=ze,
        mode="lines",
        line=dict(color="black", width=1),
        showlegend=False,
        hoverinfo="none",
    )


def render_roof(roof_type, footprint, fp_name, camera_eye):
    """Render a single roof type and save as PNG."""
    verts, tris, mats = generate_building(
        footprint,
        height=HEIGHT,
        roof_shape=roof_type,
        roof_height=ROOF_HEIGHT,
        material=MaterialType.BRICK,
        roof_material=MaterialType.CONCRETE,
    )

    fig = go.Figure()
    fig.add_trace(make_mesh_trace(verts, tris, mats, name=roof_type))
    fig.add_trace(make_wireframe_trace(verts, tris))

    # Axis ranges
    all_min = verts.min(axis=0) - 1
    all_max = verts.max(axis=0) + 1
    mid = (all_min + all_max) / 2
    span = max(all_max - all_min) / 2

    fig.update_layout(
        title=dict(
            text=f"{roof_type} roof ({fp_name})",
            font=dict(size=20),
        ),
        scene=dict(
            xaxis=dict(range=[mid[0] - span, mid[0] + span], title="X"),
            yaxis=dict(range=[mid[1] - span, mid[1] + span], title="Y"),
            zaxis=dict(range=[0, all_max[2] + 2], title="Z"),
            aspectmode="data",
            camera=dict(eye=camera_eye),
        ),
        width=800,
        height=600,
        margin=dict(l=20, r=20, t=60, b=20),
    )

    filename = f"{roof_type}_{fp_name}.png"
    fig.write_image(str(OUT_DIR / filename), scale=2)
    print(f"  Saved {filename}")
    return str(OUT_DIR / filename)


def main():
    cameras = [
        dict(x=1.5, y=1.5, z=1.0),   # perspective
        dict(x=0.0, y=2.0, z=0.5),    # side view
        dict(x=0.01, y=0.01, z=2.5),  # top-down
    ]
    cam_names = ["persp", "side", "top"]

    print(f"Rendering {len(ROOF_TYPES)} roof types...")
    print(f"Roof types: {ROOF_TYPES}")

    all_files = []

    for roof_type in ROOF_TYPES:
        print(f"\n--- {roof_type} ---")

        # Quad footprint, 3 camera angles
        for cam, cam_name in zip(cameras, cam_names):
            f = render_roof(roof_type, QUAD_FOOTPRINT, f"quad_{cam_name}", cam)
            all_files.append(f)

        # Non-quad footprint (pentagon) - only perspective view
        f = render_roof(roof_type, PENTAGON_FOOTPRINT, "pentagon_persp", cameras[0])
        all_files.append(f)

        # L-shape footprint - only perspective view
        f = render_roof(roof_type, L_SHAPE_FOOTPRINT, "lshape_persp", cameras[0])
        all_files.append(f)

    print(f"\nDone! {len(all_files)} images saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
