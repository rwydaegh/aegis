"""Render the provenance-locked Prague simulation configuration.

Run from any directory with::

    uv run --project /home/user/tools/devpc-python \
        semantic_twin/paper/figures/configuration/configuration.py

The script refuses changed source bytes before writing ``configuration.pdf``,
``configuration.png``, and ``configuration_assets.json`` beside itself.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
from pathlib import Path
from typing import Any

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.collections import LineCollection, PolyCollection  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402


HERE = Path(__file__).resolve().parent
SEMANTIC_TWIN_ROOT = HERE.parents[2]
REPOSITORY_ROOT = SEMANTIC_TWIN_ROOT.parent
PIPELINE_DIRECTORY = SEMANTIC_TWIN_ROOT / "outputs" / "propagation_viz" / "prague_360_pipeline_v2"
CAMPAIGN_DIRECTORY = (
    SEMANTIC_TWIN_ROOT
    / "outputs"
    / "roofline_campaign"
    / "prague_staromestske_provider_corridor_v1_first_material_interaction_v1_convergence_cuda_iid"
)
MESH_PATH = SEMANTIC_TWIN_ROOT / "data" / "geometry" / "prague_staromestske" / "inhouse_leaf_250m_f64.ply"
BODY_PATH = REPOSITORY_ROOT.parents[1] / "data" / "duke.stl"

PHOTO_PATH = PIPELINE_DIRECTORY / "panorama_pipeline_registered_photograph.png"
SUPPORT_PATH = PIPELINE_DIRECTORY / "panorama_pipeline_full_traced_support.png"
MATERIAL_PATH = PIPELINE_DIRECTORY / "panorama_pipeline_rf_material_atlas_(posterior_display).png"
CURTAIN_MANIFEST = PIPELINE_DIRECTORY / "prague_360_publication_curtain.json"
CAMPAIGN_IDENTITY = CAMPAIGN_DIRECTORY / "campaign_identity.json"
LOCATIONS_PATH = CAMPAIGN_DIRECTORY / "locations.jsonl"
SOURCE_CURVE_JSON = CAMPAIGN_DIRECTORY / "source_curve_audit.json"
SOURCE_CURVE_NPZ = CAMPAIGN_DIRECTORY / "source_curve_audit.npz"

EXPECTED_SHA256 = {
    PHOTO_PATH: "059a3bde49239a8bcbc5cd2cb881b9b89fe69fd4bcc894f06dda7494b26d59b3",
    SUPPORT_PATH: "c1db560d268789b7268434f527e63f8afed32bed9446a6c0024de2693cc199da",
    MATERIAL_PATH: "b94ed326ded0c85f0a8bda5ecc896878470fbe473f4d4e42f4d2279ba724ff53",
    MESH_PATH: "a2533b5d589f3604b63e905a5673873df2db7a41d396c8cef03389e72d08b6f4",
    BODY_PATH: "781e65ef3882f1347669e0ddca5dafa82cd6368dddd6b9e801dc49613822fe3b",
    LOCATIONS_PATH: "dfe271c4e099e87eb8f2b32af25baafbe140a2967fc4d72b724e43ffe958ad34",
    SOURCE_CURVE_NPZ: "f27c039eba5f5dfc4cbb350d1b0855944c8daf30781d49f09067e6a1199182d1",
}
EXPECTED_CAMPAIGN_IDENTITY = "68cbbd269af2e2bc29681ba9b82510a5a046ba5fe991ac221823b2971617e206"
EXPECTED_SOURCE_CURVE = "9805ef88d174edbe0ef57facf8cf17ea915f570ea2c7191d65a3e99bf8067fd0"

OUTPUT_PDF = HERE / "configuration.pdf"
OUTPUT_PNG = HERE / "configuration.png"
ASSET_MANIFEST = HERE / "configuration_assets.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return os.path.relpath(path, start=REPOSITORY_ROOT)


def _authenticate_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    observed_hashes: dict[str, str] = {}
    for path, expected in EXPECTED_SHA256.items():
        actual = _sha256(path)
        assert actual == expected, f"source hash mismatch for {path}: {actual} != {expected}"
        observed_hashes[_relative(path)] = actual

    curtain = json.loads(CURTAIN_MANIFEST.read_text(encoding="utf-8"))
    curtain_panels = {Path(panel["path"]).name: panel for panel in curtain["panels"]}
    for path in (PHOTO_PATH, SUPPORT_PATH, MATERIAL_PATH):
        panel = curtain_panels[path.name]
        assert panel["sha256"] == EXPECTED_SHA256[path]
        assert panel["status"] == "available"
    assert curtain["render_dimensions"] == [1664, 832]

    identity = json.loads(CAMPAIGN_IDENTITY.read_text(encoding="utf-8"))
    assert identity["sha256"] == EXPECTED_CAMPAIGN_IDENTITY
    contract = identity["data"]
    assert contract["configuration"]["site"] == "prague_staromestske"
    assert contract["configuration"]["route_contract"] == "provider_corridor_v1"
    assert contract["configuration"]["material_mode"] == "atlas"
    assert contract["body"]["phantom"] == "duke"
    assert contract["body"]["level"] == 2
    assert contract["body"]["surface_elements"] == 56024
    assert contract["walk"]["standpoints"] == 22
    assert contract["sources"]["provenance"]["edge_count"] == 502
    assert contract["sources"]["provenance"]["curve_hash_sha256"] == EXPECTED_SOURCE_CURVE

    source_audit = json.loads(SOURCE_CURVE_JSON.read_text(encoding="utf-8"))
    assert source_audit["curve_source_hash_sha256"] == EXPECTED_SOURCE_CURVE
    assert source_audit["npz"]["sha256"] == EXPECTED_SHA256[SOURCE_CURVE_NPZ]
    assert source_audit["segments"] == 502
    assert source_audit["selected_source_measure_rule"] == "physical_3d_edge_length"
    return contract, {"sha256": observed_hashes, "curtain": curtain, "source": source_audit}


def _load_locations() -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    rows = [json.loads(line) for line in LOCATIONS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert [row["standpoint"] for row in rows] == list(range(22))
    distance = np.asarray([row["route_distance_m"] for row in rows], dtype=np.float64)
    assert np.all(np.diff(distance) > 0.0)
    positions = np.asarray([row["position_m"] for row in rows], dtype=np.float64)
    yaws = np.asarray([row["body_yaw_deg"] for row in rows], dtype=np.float64)
    kinds = [row["point_kind"] for row in rows]
    assert kinds[0] == kinds[-1] == "camera_registered"
    assert all(kind == "stride_interpolated" for kind in kinds[1:-1])
    return positions, distance, yaws, kinds


def _load_source_curve() -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    with np.load(SOURCE_CURVE_NPZ, allow_pickle=False) as data:
        starts = np.asarray(data["segment_starts_m"], dtype=np.float64)
        ends = np.asarray(data["segment_ends_m"], dtype=np.float64)
        total = float(data["physical_3d_total_m"])
        selected_rule = str(data["selected_measure_rule"])
    assert starts.shape == ends.shape == (502, 3)
    assert selected_rule == "physical_3d_edge_length"
    assert np.isclose(total, 267.15180247365765, rtol=0.0, atol=1.0e-10)
    return starts, ends, {"segments": 502, "physical_3d_total_m": total}


def _load_binary_triangle_ply() -> tuple[np.ndarray, np.ndarray]:
    header = bytearray()
    with MESH_PATH.open("rb") as stream:
        while not header.endswith(b"end_header\n"):
            line = stream.readline()
            assert line, "unterminated PLY header"
            header.extend(line)
    header_text = header.decode("ascii")
    assert "format binary_little_endian 1.0" in header_text
    vertex_count = int(next(line.split()[2] for line in header_text.splitlines() if line.startswith("element vertex")))
    face_count = int(next(line.split()[2] for line in header_text.splitlines() if line.startswith("element face")))
    assert vertex_count == 823889
    assert face_count == 664619
    vertex_offset = len(header)
    vertices = np.memmap(
        MESH_PATH,
        mode="r",
        dtype="<f4",
        offset=vertex_offset,
        shape=(vertex_count, 3),
    )
    face_dtype = np.dtype([("count", "u1"), ("indices", "<i4", (3,))])
    faces = np.memmap(
        MESH_PATH,
        mode="r",
        dtype=face_dtype,
        offset=vertex_offset + 12 * vertex_count,
        shape=(face_count,),
    )
    assert np.all(faces["count"] == 3)
    return vertices, faces["indices"]


def _load_binary_stl() -> np.ndarray:
    with BODY_PATH.open("rb") as stream:
        stream.seek(80)
        triangle_count = struct.unpack("<I", stream.read(4))[0]
    dtype = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attr", "<u2")])
    records = np.fromfile(BODY_PATH, dtype=dtype, count=triangle_count, offset=84)
    assert triangle_count == records.shape[0] == 56024
    return np.asarray(records["vertices"], dtype=np.float64)


def _configure_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Latin Modern Roman", "Computer Modern Roman", "DejaVu Serif"],
            "font.size": 8.5,
            "axes.titlesize": 8.5,
            "axes.labelsize": 8.5,
            "xtick.labelsize": 7.5,
            "ytick.labelsize": 7.5,
            "legend.fontsize": 7.5,
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )


def _plot_panorama_panel(ax: plt.Axes, path: Path, title: str) -> None:
    image = plt.imread(path)
    assert image.shape[:2] == (832, 1664)
    ax.imshow(image, interpolation="lanczos")
    ax.set_title(title, loc="left", fontweight="bold", pad=3.0)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color("0.2")
        spine.set_linewidth(0.5)


def _plot_body_panel(ax: plt.Axes, body_triangles: np.ndarray) -> None:
    projected = body_triangles[:, :, (0, 2)]
    depth = body_triangles[:, :, 1].mean(axis=1)
    order = np.argsort(depth)
    # A fixed stride preserves the exact outline while keeping the PDF compact.
    chosen = order[::2]
    norm = mpl.colors.Normalize(vmin=float(depth.min()), vmax=float(depth.max()))
    colours = mpl.colormaps["Oranges"](0.35 + 0.55 * norm(depth[chosen]))
    ax.add_collection(PolyCollection(projected[chosen], facecolors=colours, edgecolors="none", rasterized=True))
    lower = projected.reshape(-1, 2).min(axis=0)
    upper = projected.reshape(-1, 2).max(axis=0)
    padding = 0.04 * (upper - lower)
    ax.set_xlim(lower[0] - padding[0], upper[0] + padding[0])
    ax.set_ylim(lower[1] - 0.08, upper[1] + padding[1])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("(e) Body coupling", loc="left", fontweight="bold", pad=4.0)
    ax.text(
        0.5,
        0.025,
        "56,024 elements  |  Level 2\nat every standpoint\nroute-tangent yaw",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=7.3,
        linespacing=1.25,
        bbox={"facecolor": "white", "edgecolor": "0.7", "linewidth": 0.45, "pad": 3.0},
        zorder=5,
    )
    for spine in ax.spines.values():
        spine.set_color("0.2")
        spine.set_linewidth(0.55)


def _plot_configuration(
    positions: np.ndarray,
    distance: np.ndarray,
    yaws: np.ndarray,
    source_starts: np.ndarray,
    source_ends: np.ndarray,
    vertices: np.ndarray,
    faces: np.ndarray,
    body_triangles: np.ndarray,
) -> None:
    _configure_style()
    fig = plt.figure(figsize=(7.16, 4.55), constrained_layout=False)
    grid = fig.add_gridspec(
        2,
        12,
        height_ratios=(1.0, 2.72),
        left=0.065,
        right=0.985,
        bottom=0.095,
        top=0.975,
        hspace=0.08,
        wspace=0.055,
    )
    _plot_panorama_panel(fig.add_subplot(grid[0, 0:4]), PHOTO_PATH, "(a) Registered panorama")
    _plot_panorama_panel(fig.add_subplot(grid[0, 4:8]), SUPPORT_PATH, "(b) Traced support")
    _plot_panorama_panel(fig.add_subplot(grid[0, 8:12]), MATERIAL_PATH, "(c) Material field")

    ax = fig.add_subplot(grid[1, 0:9])
    body_ax = fig.add_subplot(grid[1, 9:12])
    all_xy = np.vstack((source_starts[:, :2], source_ends[:, :2], positions[:, :2]))
    lower = all_xy.min(axis=0) - np.array([12.0, 12.0])
    upper = all_xy.max(axis=0) + np.array([12.0, 12.0])
    span = upper - lower
    if span[0] < span[1]:
        padding = 0.5 * (span[1] - span[0])
        lower[0] -= padding
        upper[0] += padding

    face_centres = vertices[faces].mean(axis=1)
    inside = (
        (face_centres[:, 0] >= lower[0])
        & (face_centres[:, 0] <= upper[0])
        & (face_centres[:, 1] >= lower[1])
        & (face_centres[:, 1] <= upper[1])
    )
    candidate_indices = np.flatnonzero(inside)
    stride = max(1, int(np.ceil(candidate_indices.size / 55000)))
    selected = candidate_indices[::stride]
    plan_triangles = vertices[faces[selected]][:, :, :2]
    height = face_centres[selected, 2]
    height_norm = mpl.colors.Normalize(vmin=233.0, vmax=290.0, clip=True)
    geometry_colours = mpl.colormaps["Greys"](0.18 + 0.48 * height_norm(height))
    ax.add_collection(
        PolyCollection(
            plan_triangles,
            facecolors=geometry_colours,
            edgecolors="none",
            rasterized=True,
            zorder=1,
        )
    )

    source_segments = np.stack((source_starts[:, :2], source_ends[:, :2]), axis=1)
    ax.add_collection(
        LineCollection(
            source_segments,
            colors="#D55E00",
            linewidths=1.15,
            alpha=0.94,
            capstyle="round",
            zorder=3,
        )
    )
    ax.plot(
        positions[:, 0],
        positions[:, 1],
        color="#0072B2",
        linewidth=1.45,
        zorder=4,
    )
    ax.scatter(
        positions[:, 0],
        positions[:, 1],
        s=13.0,
        facecolor="white",
        edgecolor="#0072B2",
        linewidth=0.65,
        zorder=5,
    )
    endpoint_mask = np.array([True] + [False] * 20 + [True])
    ax.scatter(
        positions[endpoint_mask, 0],
        positions[endpoint_mask, 1],
        s=25.0,
        marker="s",
        facecolor="#0072B2",
        edgecolor="white",
        linewidth=0.6,
        zorder=6,
    )

    middle = len(positions) // 2
    theta = np.deg2rad(90.0 - yaws[middle])
    arrow_start = positions[middle, :2]
    arrow_delta = 14.0 * np.array([np.cos(theta), np.sin(theta)])
    ax.annotate(
        "",
        xy=arrow_start + arrow_delta,
        xytext=arrow_start,
        arrowprops={"arrowstyle": "-|>", "color": "#0072B2", "lw": 0.9},
        zorder=7,
    )

    handles = [
        Patch(facecolor="0.78", edgecolor="none", label="250 m support mesh"),
        Line2D([0], [0], color="#D55E00", linewidth=1.6, label="Roofline source curve (502 elements)"),
        Line2D(
            [0],
            [0],
            color="#0072B2",
            linewidth=1.4,
            marker="o",
            markerfacecolor="white",
            markeredgecolor="#0072B2",
            markersize=4.0,
            label="Fixed pedestrian route (22 standpoints)",
        ),
    ]
    ax.legend(handles=handles, loc="upper left", frameon=True, framealpha=0.96, edgecolor="0.6")
    ax.text(
        0.012,
        0.018,
        f"Route length {distance[-1]:.1f} m  |  Source support 267.2 m",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.1,
        bbox={"facecolor": "white", "edgecolor": "0.65", "linewidth": 0.45, "pad": 2.5},
        zorder=10,
    )
    _plot_body_panel(body_ax, body_triangles)

    ax.set_title("(d) Simulation configuration", loc="left", fontweight="bold", pad=4.0)
    ax.set_xlabel("East relative to site anchor (m)")
    ax.set_ylabel("North relative to site anchor (m)")
    ax.set_xlim(lower[0], upper[0])
    ax.set_ylim(lower[1], upper[1])
    ax.set_aspect("equal", adjustable="box")
    ax.tick_params(direction="out", length=3.0)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_color("0.2")
        spine.set_linewidth(0.55)

    fig.savefig(
        OUTPUT_PDF,
        bbox_inches="tight",
        pad_inches=0.02,
        metadata={
            "Title": "Prague city-exposure simulation configuration",
            "Creator": "configuration.py",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    fig.savefig(
        OUTPUT_PNG,
        dpi=300,
        bbox_inches="tight",
        pad_inches=0.02,
        metadata={"Title": "Prague city-exposure simulation configuration"},
    )
    plt.close(fig)


def _write_manifest(
    contract: dict[str, Any],
    authentication: dict[str, Any],
    positions: np.ndarray,
    distance: np.ndarray,
    source_summary: dict[str, Any],
) -> None:
    roles = {
        PHOTO_PATH: "registered source panorama, exact publication-pipeline panel",
        SUPPORT_PATH: "exact traced-support publication-pipeline panel",
        MATERIAL_PATH: "projection-aligned all-camera material-posterior display panel",
        MESH_PATH: "current 250 m Prague transport support mesh, with visual-only plan-view subsampling",
        BODY_PATH: "current campaign anatomical body surface",
        LOCATIONS_PATH: "current sealed fixed-route positions, body yaws, and route distances",
        SOURCE_CURVE_NPZ: "current sealed roofline segment endpoints and physical-length measure",
    }
    source_assets = []
    for path, role in roles.items():
        source_assets.append(
            {
                "path": _relative(path),
                "sha256": authentication["sha256"][_relative(path)],
                "role": role,
            }
        )

    payload = {
        "schema_version": "prague_configuration_figure_assets_v1",
        "figure_scope": (
            "early physical configuration: registered image evidence, transport support and "
            "material field, roofline source support, fixed pedestrian route, and body coupling"
        ),
        "site": "prague_staromestske",
        "source_assets": source_assets,
        "authenticated_contracts": {
            "curtain_manifest": {
                "path": _relative(CURTAIN_MANIFEST),
                "capture": authentication["curtain"]["capture"],
                "projection": authentication["curtain"]["projection"],
                "panel_dimensions": [1664, 832],
            },
            "campaign_identity": {
                "path": _relative(CAMPAIGN_IDENTITY),
                "sha256": EXPECTED_CAMPAIGN_IDENTITY,
                "route_contract": contract["configuration"]["route_contract"],
                "material_mode": contract["configuration"]["material_mode"],
                "transport_topology": contract["configuration"]["transport_topology"],
            },
            "source_curve": {
                "path": _relative(SOURCE_CURVE_JSON),
                "curve_source_hash_sha256": EXPECTED_SOURCE_CURVE,
                "selected_measure_rule": "physical_3d_edge_length",
            },
        },
        "shown_configuration": {
            "mesh_crop_radius_m": 250.0,
            "mesh_triangles": 664619,
            "route_standpoints": int(positions.shape[0]),
            "route_length_m": float(distance[-1]),
            "route_endpoints_are_registered_cameras": True,
            "body": {
                "description": "anatomical adult-male surface phantom",
                "surface_elements": 56024,
                "level": 2,
                "yaw_rule": "route tangent at each standpoint",
            },
            "roofline_segments": source_summary["segments"],
            "roofline_physical_3d_total_m": source_summary["physical_3d_total_m"],
        },
        "visual_transforms": {
            "panorama_panels": "exact 1664 x 832 source panels, uniformly resampled for layout only",
            "plan_view_mesh": (
                "deterministic display-only face stride after spatial clipping. Exact support remains "
                "visible in panel (b) and transport uses all 664619 faces"
            ),
            "roofline_and_route": "all coordinates shown without smoothing in local ENU metres",
            "body_inset": "orthographic x-z projection of the exact surface, every second triangle for compact PDF",
        },
        "excluded_assets": [
            {
                "pattern": "outputs/propagation_viz/figures/prague_staromestske_propagation_*.png",
                "reason": "older Blender walk, source, body, and ray renders do not represent the current sealed campaign",
            },
            {
                "kind": "propagation rays",
                "reason": "no rays are shown because available rendered rays are stale for this configuration",
            },
        ],
        "outputs": {
            OUTPUT_PDF.name: {"sha256": _sha256(OUTPUT_PDF), "bytes": OUTPUT_PDF.stat().st_size},
            OUTPUT_PNG.name: {"sha256": _sha256(OUTPUT_PNG), "bytes": OUTPUT_PNG.stat().st_size},
        },
    }
    ASSET_MANIFEST.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    contract, authentication = _authenticate_inputs()
    positions, distance, yaws, _kinds = _load_locations()
    source_starts, source_ends, source_summary = _load_source_curve()
    vertices, faces = _load_binary_triangle_ply()
    body_triangles = _load_binary_stl()
    _plot_configuration(
        positions,
        distance,
        yaws,
        source_starts,
        source_ends,
        vertices,
        faces,
        body_triangles,
    )
    _write_manifest(contract, authentication, positions, distance, source_summary)


if __name__ == "__main__":
    main()
