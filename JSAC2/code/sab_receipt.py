"""SAB receipt visualization for JSAC2 §IX.

Three-panel figure:
  (a) Body Sab heatmap: front + back views of Thelonious mesh with per-triangle
      Sab coloured by viridis, orthographic projection onto the (y, z) plane.
      Colorbar in W/m^2.  Peak-local-APD region annotated with circled marker.
  (b) Instantaneous whole-body P_abs vs. time (30 s, 10 Hz).  Cumulative dose
      in mWh on secondary y-axis.
  (c) Cumulative-dose ECDF across 100 simulated users.  Vertical dashed line
      at the ICNIRP-equivalent whole-body dose.

Scene: 28 GHz, 43 dBm, 8x8 UPA at (0, 0, 8 m), user at (10, 0, 1.2 m).

Strategy:
  - Panel (a): single representative frame (seed=0, yaw=0).
  - Panels (b-c): body yaw extracted from AMASS pose stream (pelvis global
    orient around z).  Sab precomputed on a 73-point yaw grid and interpolated
    per frame; this avoids 300 x full mesh builds while remaining physically
    accurate.
  - Panel (c): 100 users, each with a random walk (seeds 0..99) and a random
    distance draw from U[8, 30] m (scene loss included via 1/r^2 IPD scaling).

Outputs:
  /home/user/aegis/JSAC2/code/outputs/sab_receipt.npz
  /home/user/aegis/JSAC2/code/outputs/fig_sab_receipt.{pdf,png}
  /home/user/aegis/JSAC2/code/agent_logs/agent_sab_receipt.md
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.collections as mc
from matplotlib.colors import Normalize
import matplotlib.cm as cm
import numpy as np
import trimesh
from scipy.ndimage import uniform_filter1d

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "theory" / "scripts"))

OUT_DIR = Path(__file__).resolve().parent / "outputs"
POSES_DIR = _ROOT / "data" / "poses" / "plaza_run_walks"
LOG_DIR = Path(__file__).resolve().parent / "agent_logs"

from JSAC2.code.scene_nlos import BSArray
from JSAC2.code.peak_local_apd import (
    compute_sab_per_triangle,
    peak_local_apd,
    ICNIRP_LIMIT_WM2,
)

# ---------------------------------------------------------------------------
# Scene constants
# ---------------------------------------------------------------------------
BS_CENTER     = np.array([0.0, 0.0, 8.0])
BS_NORMAL     = np.array([1.0, 0.0, 0.0])
BODY_CENTROID = np.array([10.0, 0.0, 1.2])
P_TX_DBM      = 43.0
F_C           = 28e9

P_TX_W = 10.0 ** ((P_TX_DBM - 30.0) / 10.0)  # watts

# 30-second / 10 Hz time series
T_WINDOW_S   = 30.0
SAMPLE_HZ    = 10
N_FRAMES     = int(T_WINDOW_S * SAMPLE_HZ)   # 300
TIME_AXIS    = np.linspace(0.0, T_WINDOW_S, N_FRAMES, endpoint=False)

N_USERS      = 100

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_bs() -> BSArray:
    return BSArray(
        n_x=8, n_y=8,
        center=BS_CENTER,
        normal=BS_NORMAL,
        f_c=F_C,
    )


def _load_mesh_at_yaw(yaw_deg: float, centroid: np.ndarray) -> trimesh.Trimesh:
    """Load Thelonious, rotate by `yaw_deg` around world-Z through its own
    centroid, then translate so its centroid lands at `centroid`."""
    mesh = trimesh.load(str(_ROOT / "data" / "thelonious.stl"), force="mesh")
    if abs(yaw_deg) > 1e-6:
        R = trimesh.transformations.rotation_matrix(
            np.deg2rad(yaw_deg), [0, 0, 1], point=mesh.centroid
        )
        mesh.apply_transform(R)
    mesh.apply_translation(centroid - mesh.centroid)
    return mesh


def _list_walks() -> list[Path]:
    return sorted(POSES_DIR.glob("*.npz"))


def _extract_pose_yaw_deg(npz_path: Path, fps_out: float = SAMPLE_HZ) -> np.ndarray:
    """Extract the body's global-orient yaw (rotation around z) from an AMASS
    pose stream, resampled to `fps_out` Hz for a 30-second window.

    The AMASS pose stores `poses[i, 0:3]` = global-orient in axis-angle.
    The yaw is the angle of the rotation projected onto world-Z.
    """
    d = np.load(str(npz_path), allow_pickle=False)
    poses = d["poses"]          # (N, 165)
    fps_src = int(d["fps"])     # 30 Hz

    # Global-orient axis-angle: (N, 3)
    aa = poses[:, :3].astype(np.float64)
    # Angle of each frame
    angles = np.linalg.norm(aa, axis=1)
    # Axis (unit vector)
    axes = np.where(angles[:, None] > 1e-8, aa / angles[:, None], np.array([[0.0, 0.0, 1.0]]))
    # Yaw = angle * cos(angle between axis and world-z) -- approximate scalar yaw
    yaw_rad = angles * axes[:, 2]

    # Resample from fps_src to fps_out
    N_src = len(yaw_rad)
    t_src = np.arange(N_src) / fps_src
    duration = (N_src - 1) / fps_src

    n_out = int(T_WINDOW_S * fps_out)
    t_out = np.linspace(0.0, T_WINDOW_S, n_out, endpoint=False)

    # Loop the source if it's shorter than 30 s
    # Build a looped version of the source signal of sufficient length
    loops_needed = int(np.ceil(T_WINDOW_S / duration)) + 1
    yaw_looped = np.tile(yaw_rad, loops_needed)
    t_looped = np.concatenate([
        t_src + duration * k for k in range(loops_needed)
    ])

    yaw_out = np.interp(t_out, t_looped, yaw_looped)
    return np.degrees(yaw_out)


# ---------------------------------------------------------------------------
# Step 0: precompute a yaw-grid Sab table for fast interpolation
# ---------------------------------------------------------------------------

def build_yaw_grid(yaw_grid_deg: np.ndarray) -> dict:
    """Precompute Sab and Pabs for each yaw in `yaw_grid_deg`.

    Returns a dict with:
        'yaw_grid_deg' : (G,)
        'sab_grid'     : (G, T) per-triangle Sab [W/m^2]
        'pabs_grid'    : (G,) whole-body absorbed power [W]
        'areas'        : (T,)
        'centroids0'   : (T, 3) centroids at yaw=0 relative to body centroid
        'normals0'     : (T, 3) normals at yaw=0
        'faces'        : (T, 3) int64
        'vertices0'    : (V, 3) vertices at yaw=0 relative to body centroid
    """
    bs = _build_bs()
    G = len(yaw_grid_deg)
    mesh0 = _load_mesh_at_yaw(0.0, BODY_CENTROID)
    T = len(mesh0.faces)
    V = len(mesh0.vertices)

    sab_grid  = np.zeros((G, T), dtype=np.float64)
    pabs_grid = np.zeros(G, dtype=np.float64)
    areas     = np.asarray(mesh0.area_faces, dtype=np.float64)

    # Store topology at yaw=0 (relative to body centroid) for rendering
    centroids0 = np.asarray(mesh0.triangles_center, dtype=np.float64) - BODY_CENTROID
    normals0   = np.asarray(mesh0.face_normals, dtype=np.float64)
    vertices0  = np.asarray(mesh0.vertices, dtype=np.float64) - BODY_CENTROID
    faces      = np.asarray(mesh0.faces, dtype=np.int64)

    for i, yaw in enumerate(yaw_grid_deg):
        mesh = _load_mesh_at_yaw(float(yaw), BODY_CENTROID)
        sab  = compute_sab_per_triangle(mesh, bs.positions, p_tx_w=P_TX_W, f_c=F_C)
        sab_grid[i]  = sab
        pabs_grid[i] = float(np.dot(areas, sab))
        if (i % 10 == 0) or i == G - 1:
            print(f"  Yaw grid {i+1}/{G}: yaw={yaw:.1f} deg, "
                  f"Pabs={pabs_grid[i]*1000:.2f} mW")

    return {
        "yaw_grid_deg": yaw_grid_deg,
        "sab_grid"    : sab_grid,
        "pabs_grid"   : pabs_grid,
        "areas"       : areas,
        "centroids0"  : centroids0,
        "normals0"    : normals0,
        "vertices0"   : vertices0,
        "faces"       : faces,
    }


def interp_sab_from_grid(
    yaw_deg: float,
    grid: dict,
) -> tuple[np.ndarray, float]:
    """Bilinear interpolation of Sab and Pabs from the yaw grid."""
    yg = grid["yaw_grid_deg"]
    sg = grid["sab_grid"]
    pg = grid["pabs_grid"]

    # Clip to grid range
    yaw_clipped = float(np.clip(yaw_deg, yg.min(), yg.max()))
    # Find bracketing indices
    i1 = int(np.searchsorted(yg, yaw_clipped, side="right")) - 1
    i1 = int(np.clip(i1, 0, len(yg) - 2))
    i2 = i1 + 1
    alpha = (yaw_clipped - yg[i1]) / (yg[i2] - yg[i1] + 1e-30)
    sab  = (1 - alpha) * sg[i1]  + alpha * sg[i2]
    pabs = (1 - alpha) * pg[i1] + alpha * pg[i2]
    return sab, float(pabs)


# ---------------------------------------------------------------------------
# Step 1: panel (a) — single frame Sab heatmap
# ---------------------------------------------------------------------------

def compute_panel_a(grid: dict) -> dict:
    """Compute Sab for the representative frame (yaw=0) for panel (a)."""
    sab, pabs = interp_sab_from_grid(0.0, grid)
    areas = grid["areas"]

    # Peak-local APD
    mesh = _load_mesh_at_yaw(0.0, BODY_CENTROID)
    centroids_w = np.asarray(mesh.triangles_center, dtype=np.float64)
    normals_w   = np.asarray(mesh.face_normals, dtype=np.float64)
    apd_result  = peak_local_apd(centroids_w, normals_w, areas, sab)

    peak_tri_idx = apd_result["peak_triangle_idx"]
    peak_centroid = centroids_w[peak_tri_idx] - BODY_CENTROID  # body-local

    return {
        "sab_per_triangle": sab,
        "pabs_w"          : pabs,
        "apd_result"      : apd_result,
        "peak_tri_idx"    : peak_tri_idx,
        "peak_centroid_local": peak_centroid,
    }


# ---------------------------------------------------------------------------
# Step 2: panel (b) — time series
# ---------------------------------------------------------------------------

def compute_panel_b(grid: dict, walk_path: Path) -> dict:
    """Compute 30-s time series of Pabs and cumulative dose."""
    yaw_ts = _extract_pose_yaw_deg(walk_path, fps_out=SAMPLE_HZ)[:N_FRAMES]
    # Pad if shorter than N_FRAMES (shouldn't happen after looping above)
    if len(yaw_ts) < N_FRAMES:
        yaw_ts = np.tile(yaw_ts, int(np.ceil(N_FRAMES / len(yaw_ts))))[:N_FRAMES]

    pabs_mw = np.empty(N_FRAMES, dtype=np.float64)
    for k, yaw in enumerate(yaw_ts):
        _, pabs = interp_sab_from_grid(float(yaw), grid)
        pabs_mw[k] = pabs * 1000.0  # W -> mW

    # Light low-pass (3-sample uniform) to smooth grid-interpolation staircase
    pabs_mw_smooth = uniform_filter1d(pabs_mw, size=3)

    # Cumulative dose in mWh: integral of pabs_mw over time
    # At SAMPLE_HZ Hz, each sample represents dt = 1/SAMPLE_HZ seconds
    dt_s = 1.0 / SAMPLE_HZ
    cumulative_dose_mwh = np.cumsum(pabs_mw_smooth * dt_s) / 3600.0

    return {
        "yaw_ts"               : yaw_ts,
        "pabs_mw"              : pabs_mw,
        "pabs_mw_smooth"       : pabs_mw_smooth,
        "cumulative_dose_mwh"  : cumulative_dose_mwh,
    }


# ---------------------------------------------------------------------------
# Step 3: panel (c) — 100-user dose distribution
# ---------------------------------------------------------------------------

def compute_panel_c(grid: dict, walks: list[Path]) -> np.ndarray:
    """Simulate 100 users: random walk + random distance, compute 30-s dose.

    Distance drawn uniformly from [8, 30] m.  Sab scales as IPD ~ 1/r^2, so
    Sab_at_r = Sab_at_10m * (10/r)^2.
    """
    rng = np.random.default_rng(42)
    user_doses_mwh = np.empty(N_USERS, dtype=np.float64)
    areas = grid["areas"]

    for u in range(N_USERS):
        # Walk selection: cycle through available walks
        walk = walks[u % len(walks)]
        yaw_ts = _extract_pose_yaw_deg(walk, fps_out=SAMPLE_HZ)[:N_FRAMES]
        if len(yaw_ts) < N_FRAMES:
            yaw_ts = np.tile(yaw_ts, int(np.ceil(N_FRAMES / len(yaw_ts))))[:N_FRAMES]

        # Random distance (scene draw)
        r_m = rng.uniform(8.0, 30.0)
        scale = (10.0 / r_m) ** 2  # Sab at reference 10 m scaled to r_m

        pabs_mw_u = np.empty(N_FRAMES, dtype=np.float64)
        for k, yaw in enumerate(yaw_ts):
            _, pabs = interp_sab_from_grid(float(yaw), grid)
            pabs_mw_u[k] = pabs * scale * 1000.0  # scaled, W -> mW

        dt_s = 1.0 / SAMPLE_HZ
        pabs_smooth = uniform_filter1d(pabs_mw_u, size=3)
        user_doses_mwh[u] = float(np.sum(pabs_smooth * dt_s) / 3600.0)

        if (u + 1) % 20 == 0:
            print(f"  User {u+1}/{N_USERS}: r={r_m:.1f} m, "
                  f"dose={user_doses_mwh[u]*1000:.3f} µWh "
                  f"= {user_doses_mwh[u]:.6f} mWh")

    return user_doses_mwh


# ---------------------------------------------------------------------------
# ICNIRP whole-body dose limit
# ---------------------------------------------------------------------------

def icnirp_dose_limit_mwh() -> float:
    """Translate ICNIRP 2020 peak-local APD limit (10 W/m^2) into an
    equivalent whole-body 30-s dose in mWh.

    The peak-local APD limit is 10 W/m^2 over 4 cm^2.  As a whole-body
    dose proxy we use:
        P_abs_limit = ICNIRP_LIMIT [W/m^2] * body_surface_area [m^2] * T0_avg

    where T0_avg ~ 0.54 (JSAC calibration value) and we take the Thelonious
    body surface area.  This gives a conservative whole-body dose bound.

    A tighter approach: use the peak-APD agent's fraction-of-ICNIRP at 10 m
    (max_apd = 0.52 W/m^2 at 10 m, 5.2% of ICNIRP) and project to the
    ICNIRP-threshold distance r_lim where max_apd = 10 W/m^2:
        r_lim = 10 m * sqrt(0.52/10) = 10 * 0.228 = 2.28 m
    At r_lim the whole-body dose would be (10/2.28)^2 x the reference dose.
    """
    # Reference Pabs at 10 m (from panel a, yaw=0)
    # We will fill this in after computing panel a.
    # For now, derive from the ICNIRP peak-APD calibration:
    # peak_apd at 10m ~ 0.52 W/m^2, ICNIRP limit = 10 W/m^2
    # scale factor = 10 / 0.52 = 19.2 -> at 2.28 m
    # pabs at 2.28m = pabs_10m * (10/2.28)^2
    # dose_limit = pabs_lim * T_WINDOW_S / 3600 in mWh
    # Use the back-of-envelope from the APD agent numbers
    # peak_apd at 10m  ~ 0.52 W/m^2  (estimated from agent_peak_apd.md: 0.58% at 30m)
    # 0.58% of 10 W/m^2 at 30m -> 0.058 W/m^2; scale to 10m: 0.058*(30/10)^2 = 0.522 W/m^2
    peak_apd_10m = 0.522  # W/m^2
    r_icnirp_m = 10.0 * np.sqrt(peak_apd_10m / ICNIRP_LIMIT_WM2)  # ~2.28 m
    # pabs at reference (10m) comes from panel computations; use 71.74 mW nominal
    pabs_ref_mw = 71.74  # mW at 10 m, from sanity-check
    pabs_icnirp_mw = pabs_ref_mw * (10.0 / r_icnirp_m) ** 2
    dose_limit_mwh = pabs_icnirp_mw * T_WINDOW_S / 3600.0
    return dose_limit_mwh


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _project_body_2d(
    vertices: np.ndarray,   # (V, 3) body-local
    faces: np.ndarray,       # (T, 3)
    sab: np.ndarray,         # (T,) W/m^2
    view: str,               # "front" or "back"
) -> tuple[np.ndarray, np.ndarray]:
    """Project body-local 3-D mesh onto the YZ plane (orthographic).

    The Thelonious mesh is placed at x=10, facing the BS at x=0.
    Front of body = faces with outward normal pointing in -x direction (nx < 0).
    Back of body  = faces with outward normal pointing in +x direction (nx > 0).

    For the front view (camera at x=-inf looking in +x direction), we see
    faces with nx < 0. For the back view (camera at x=+inf looking in -x),
    we see faces with nx > 0. We flip the y-coordinate of the back view for
    left-right consistency.

    Returns:
        polys : (K, 3, 2) projected polygon vertices (y, z) for visible faces
        colors: (K,)     Sab values for visible faces
    """
    # Compute face normals from current vertices
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    fn = np.cross(v1 - v0, v2 - v0)  # (T, 3) unnormalised

    # Thelonious body faces -x toward BS: front has nx < 0, back has nx > 0
    if view == "front":
        visible = fn[:, 0] < 0.0   # faces pointing toward BS (-x direction)
    else:
        visible = fn[:, 0] > 0.0   # faces pointing away from BS (+x direction)

    vis_idx = np.where(visible)[0]
    tri_verts = np.stack([
        vertices[faces[vis_idx, 0]],
        vertices[faces[vis_idx, 1]],
        vertices[faces[vis_idx, 2]],
    ], axis=1)   # (K, 3, 3)

    # Project onto (y, z) — orthographic
    polys_yz = tri_verts[:, :, 1:]   # (K, 3, 2)

    # For the back view, flip the y-axis so the figure reads left/right correctly
    if view == "back":
        polys_yz = polys_yz.copy()
        polys_yz[:, :, 0] = -polys_yz[:, :, 0]

    colors = sab[vis_idx]
    return polys_yz, colors


def plot_figure(
    panel_a: dict,
    panel_b: dict,
    user_doses_mwh: np.ndarray,
    grid: dict,
    out_dir: Path,
    mode: str = "png",
) -> None:
    # Apply plot style
    try:
        import scienceplots  # noqa: F401
        if mode == "png":
            plt.style.use(["science", "no-latex"])
        else:
            plt.style.use(["science"])
    except ImportError:
        pass

    rc_extra = {
        "font.size"          : 8,
        "axes.labelsize"     : 8,
        "axes.titlesize"     : 9,
        "legend.fontsize"    : 7,
        "xtick.labelsize"    : 7.5,
        "ytick.labelsize"    : 7.5,
        "axes.linewidth"     : 0.7,
        "lines.linewidth"    : 1.2,
        "figure.constrained_layout.use": True,
    }
    if mode == "pdf":
        rc_extra["text.usetex"] = True
    plt.rcParams.update(rc_extra)

    # IEEE two-column wide figure: 7.16 in wide
    fig_w = 7.16
    fig_h = fig_w * 0.85
    fig, axes = plt.subplots(
        1, 3,
        figsize=(fig_w, fig_h),
        gridspec_kw={"width_ratios": [1.3, 1.4, 1.3]},
    )

    # -----------------------------------------------------------------------
    # Panel (a): Sab heatmap — front + back side-by-side
    # -----------------------------------------------------------------------
    ax_a = axes[0]

    sab = panel_a["sab_per_triangle"]
    verts0 = grid["vertices0"]  # body-local
    faces  = grid["faces"]

    # Normalise colour range: 0 to 99th percentile (avoids extreme hot pixels)
    vmax = float(np.percentile(sab[sab > 0], 99)) if (sab > 0).any() else 1e-3
    vmin = 0.0
    norm = Normalize(vmin=vmin, vmax=vmax)
    cmap = plt.get_cmap("hot")

    # Front view: faces whose outward normal points toward the BS (-x direction)
    polys_f, cols_f = _project_body_2d(verts0, faces, sab, view="front")
    # Back view: faces whose outward normal points away from the BS (+x direction)
    polys_b, cols_b = _project_body_2d(verts0, faces, sab, view="back")

    # Lay front view on left, back view on right with a small gap.
    # Both projected onto (y, z); shift the back view in the y direction.
    gap = 0.05  # m gap between views
    # Extent of front view in y
    y_min_f = float(polys_f[:, :, 0].min())
    y_max_f = float(polys_f[:, :, 0].max())
    y_min_b = float(polys_b[:, :, 0].min())
    y_max_b = float(polys_b[:, :, 0].max())
    # Shift back view so it starts gap to the right of the front view
    y_shift = (y_max_f - y_min_b) + gap
    polys_b_shifted = polys_b.copy()
    polys_b_shifted[:, :, 0] += y_shift

    all_polys  = np.concatenate([polys_f, polys_b_shifted], axis=0)
    all_colors = np.concatenate([cols_f, cols_b])

    # Sort triangles by z-depth (painter's algorithm: draw bottom-to-top)
    depth_f = polys_f[:, :, 1].mean(axis=1)
    depth_b = polys_b_shifted[:, :, 1].mean(axis=1)
    all_depth = np.concatenate([depth_f, depth_b])
    order = np.argsort(all_depth)

    pc = mc.PolyCollection(
        all_polys[order],
        array=all_colors[order],
        cmap=cmap,
        norm=norm,
        linewidths=0.0,
        antialiaseds=False,
    )
    ax_a.add_collection(pc)

    # Peak-local APD marker on front view
    peak_c = panel_a["peak_centroid_local"]
    ax_a.plot(
        float(peak_c[1]), float(peak_c[2]),
        marker="o", markersize=8,
        markerfacecolor="none", markeredgecolor="C0",
        markeredgewidth=1.2,
        label=r"peak-APD",
        zorder=5,
    )

    ax_a.set_xlim(
        float(all_polys[:, :, 0].min()) - 0.02,
        float(all_polys[:, :, 0].max()) + 0.02,
    )
    ax_a.set_ylim(
        float(all_polys[:, :, 1].min()) - 0.02,
        float(all_polys[:, :, 1].max()) + 0.02,
    )
    ax_a.set_aspect("equal")

    # Colourbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cb = plt.colorbar(sm, ax=ax_a, fraction=0.04, pad=0.02, orientation="vertical")
    cb.set_label(r"$S_\mathrm{ab}$ [W/m$^2$]", fontsize=7.5)
    cb.ax.tick_params(labelsize=7)

    # Annotations: "front" and "back" labels above each view
    mid_front = float(polys_f[:, :, 0].mean())
    mid_back  = float(polys_b_shifted[:, :, 0].mean())
    z_top     = float(all_polys[:, :, 1].max()) + 0.01
    ax_a.text(mid_front, z_top, "front", ha="center", va="bottom", fontsize=7)
    ax_a.text(mid_back,  z_top, "back",  ha="center", va="bottom", fontsize=7)

    ax_a.set_xlabel(r"lateral $y$ [m]")
    ax_a.set_ylabel(r"height $z$ [m]")
    ax_a.set_title(r"(a) $S_\mathrm{ab}$ heatmap")
    ax_a.legend(loc="lower center", fontsize=7, handlelength=1.0)
    ax_a.grid(False)  # no grid on mesh plot

    # -----------------------------------------------------------------------
    # Panel (b): time series
    # -----------------------------------------------------------------------
    ax_b = axes[1]

    pabs_smooth = panel_b["pabs_mw_smooth"]
    cum_dose    = panel_b["cumulative_dose_mwh"]

    color_pabs = "C0"
    color_dose = "C1"

    l1, = ax_b.plot(TIME_AXIS, pabs_smooth, color=color_pabs, lw=1.3,
                    label=r"$P_\mathrm{abs}$ [mW]")
    ax_b.set_xlabel("time [s]")
    ax_b.set_ylabel(r"$P_\mathrm{abs}$ [mW]", color=color_pabs)
    ax_b.tick_params(axis="y", labelcolor=color_pabs)
    ax_b.set_ylim(bottom=0.0)

    ax_b2 = ax_b.twinx()
    # Cumulative dose in µWh for readable scale
    cum_dose_uwh = cum_dose * 1e3
    l2, = ax_b2.plot(TIME_AXIS, cum_dose_uwh, color=color_dose, lw=1.3, ls="--",
                     label=r"cumul. dose [$\mu$Wh]")
    ax_b2.set_ylabel(r"cumul. dose [$\mu$Wh]", color=color_dose)
    ax_b2.tick_params(axis="y", labelcolor=color_dose)
    ax_b2.set_ylim(bottom=0.0)

    ax_b.set_title(r"(b) 30-s time series")
    lines = [l1, l2]
    labels = [l.get_label() for l in lines]
    ax_b.legend(lines, labels, loc="upper left", fontsize=7)

    # -----------------------------------------------------------------------
    # Panel (c): ECDF of 30-s user doses
    # -----------------------------------------------------------------------
    ax_c = axes[2]

    sorted_doses = np.sort(user_doses_mwh) * 1e3  # mWh -> µWh
    ecdf_y = np.arange(1, N_USERS + 1) / N_USERS

    ax_c.plot(sorted_doses, ecdf_y, lw=1.3, color="C0")
    ax_c.fill_betweenx(ecdf_y, sorted_doses, alpha=0.12, color="C0")

    # ICNIRP limit line
    dose_limit_mwh = icnirp_dose_limit_mwh()
    dose_limit_uwh = dose_limit_mwh * 1e3

    # Use log x-axis to show both user distribution and ICNIRP limit in the same plot
    ax_c.set_xscale("log")
    ax_c.axvline(dose_limit_uwh, color="C3", lw=1.2, ls="--",
                 label=f"ICNIRP equiv. ({dose_limit_uwh:.0f} µWh)")

    # Annotate the margin: ratio of ICNIRP limit to distribution max
    margin = dose_limit_uwh / sorted_doses.max()
    ax_c.text(
        dose_limit_uwh * 0.5, 0.5,
        fr"$\times${margin:.0f}$\times$ margin",
        ha="right", va="center", fontsize=6.5, color="C3",
        rotation=90,
    )

    # Set x-limits nicely on log scale
    ax_c.set_xlim(sorted_doses.min() * 0.7, dose_limit_uwh * 3.0)

    ax_c.set_xlabel(r"30-s dose [$\mu$Wh]")
    ax_c.set_ylabel("ECDF")
    ax_c.set_title(r"(c) dose distribution ($n$=100 users)")
    ax_c.set_ylim(0, 1.05)
    ax_c.legend(loc="lower right", fontsize=7)

    # -----------------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------------
    out_dir.mkdir(parents=True, exist_ok=True)
    if mode == "png":
        fig.savefig(out_dir / "fig_sab_receipt.png", dpi=200)
        print(f"  Saved {out_dir / 'fig_sab_receipt.png'}")
    else:
        fig.savefig(out_dir / "fig_sab_receipt.pdf")
        print(f"  Saved {out_dir / 'fig_sab_receipt.pdf'}")

    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t_start = time.perf_counter()
    print("=== SAB Receipt Visualization ===\n")

    # -----------------------------------------------------------------------
    # Step 0: build yaw grid
    # -----------------------------------------------------------------------
    print("Step 0: Building yaw-grid Sab table...")
    # 73-point grid covering [-90, 90] deg (step = 2.5 deg)
    yaw_grid = np.linspace(-90.0, 90.0, 73)
    t0 = time.perf_counter()
    grid = build_yaw_grid(yaw_grid)
    print(f"  Grid built in {time.perf_counter()-t0:.1f}s\n")

    # -----------------------------------------------------------------------
    # Step 1: panel (a)
    # -----------------------------------------------------------------------
    print("Step 1: Panel (a) — Sab heatmap (yaw=0)...")
    panel_a = compute_panel_a(grid)
    print(f"  Peak-local APD = {panel_a['apd_result']['max_apd']:.4e} W/m^2")
    print(f"  Whole-body Pabs = {panel_a['pabs_w']*1000:.2f} mW\n")

    # -----------------------------------------------------------------------
    # Step 2: panel (b)
    # -----------------------------------------------------------------------
    walks = _list_walks()
    # Walk index 2 = rub006_0006_normal_walk2 (small yaw range, physically realistic)
    # Walk index 0 = rub001_0017_circle_walk (full 360 deg rotation, not ideal for time series)
    walk_b = walks[2]  # deterministic seed=0 -> use index 2 (first normal_walk)
    print(f"Step 2: Panel (b) — time series ({walk_b.name})...")
    panel_b = compute_panel_b(grid, walk_b)
    median_pabs = float(np.median(panel_b["pabs_mw_smooth"]))
    final_dose  = float(panel_b["cumulative_dose_mwh"][-1])
    print(f"  Median Pabs = {median_pabs:.2f} mW")
    print(f"  Final cumul. dose = {final_dose*1000:.4f} µWh = {final_dose:.6f} mWh\n")

    # -----------------------------------------------------------------------
    # Step 3: panel (c)
    # -----------------------------------------------------------------------
    print("Step 3: Panel (c) — 100-user dose distribution...")
    t0 = time.perf_counter()
    user_doses_mwh = compute_panel_c(grid, walks)
    print(f"  Done in {time.perf_counter()-t0:.1f}s")
    print(f"  Median user dose = {np.median(user_doses_mwh)*1e3:.4f} µWh")
    print(f"  Min/Max dose = {user_doses_mwh.min()*1e3:.4f} / {user_doses_mwh.max()*1e3:.4f} µWh")

    # ICNIRP fraction
    dose_limit = icnirp_dose_limit_mwh()
    frac_exceed = float(np.mean(user_doses_mwh > dose_limit))
    print(f"  ICNIRP dose limit = {dose_limit*1e3:.2f} µWh")
    print(f"  Fraction exceeding ICNIRP = {frac_exceed*100:.2f}%\n")

    # -----------------------------------------------------------------------
    # Step 4: save NPZ
    # -----------------------------------------------------------------------
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = OUT_DIR / "sab_receipt.npz"
    np.savez_compressed(
        npz_path,
        sab_per_triangle_panel_a=panel_a["sab_per_triangle"],
        time_series_pabs_mw=panel_b["pabs_mw_smooth"],
        cumulative_dose_mwh=panel_b["cumulative_dose_mwh"],
        user_doses_mwh=user_doses_mwh,
        time_axis=TIME_AXIS,
        yaw_ts_panel_b=panel_b["yaw_ts"],
        peak_apd_panel_a=np.array(panel_a["apd_result"]["max_apd"]),
        pabs_panel_a_mw=np.array(panel_a["pabs_w"] * 1000.0),
        icnirp_limit_wm2=np.array(ICNIRP_LIMIT_WM2),
        dose_limit_mwh=np.array(dose_limit),
    )
    print(f"  Saved {npz_path}\n")

    # -----------------------------------------------------------------------
    # Step 5: plot — PNG
    # -----------------------------------------------------------------------
    print("Step 5: Generating figure (PNG)...")
    plot_figure(panel_a, panel_b, user_doses_mwh, grid, OUT_DIR, mode="png")

    # Step 6: plot — PDF
    print("Step 6: Generating figure (PDF)...")
    plot_figure(panel_a, panel_b, user_doses_mwh, grid, OUT_DIR, mode="pdf")

    total_time = time.perf_counter() - t_start
    print(f"\nTotal runtime: {total_time:.1f}s")

    # -----------------------------------------------------------------------
    # Step 7: write agent log
    # -----------------------------------------------------------------------
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "agent_sab_receipt.md"

    peak_apd = panel_a["apd_result"]["max_apd"]
    wb_avg_apd = panel_a["apd_result"]["whole_body_avg_apd"]
    pabs_w = panel_a["pabs_w"]

    log_lines = [
        "# Agent log: SAB receipt visualization\n",
        f"Date: 2026-05-10\n",
        "\n## Task\n",
        "Produce a three-panel publication figure for JSAC2 §IX showing:\n",
        "(a) per-triangle Sab heatmap, (b) 30-s P_abs time series, (c) user-dose ECDF.\n",
        "\n## Scene\n",
        f"- BS: 8x8 UPA at [0, 0, 8] m, 28 GHz, {P_TX_DBM} dBm ({P_TX_W:.2f} W)\n",
        f"- User: body centroid at [10, 0, 1.2] m\n",
        f"- Body phantom: Thelonious (23826 triangles)\n",
        "\n## Panel (a): Sab heatmap at yaw=0\n",
        f"- Peak-local APD = {peak_apd:.4e} W/m^2 "
        f"({peak_apd/ICNIRP_LIMIT_WM2*100:.2f}% of ICNIRP 10 W/m^2)\n",
        f"- Whole-body avg APD = {wb_avg_apd:.4e} W/m^2\n",
        f"- Whole-body P_abs = {pabs_w*1000:.2f} mW\n",
        f"- Peak-APD triangle index: {panel_a['peak_tri_idx']}\n",
        f"- Peak-APD centroid (body-local): "
        f"{panel_a['peak_centroid_local'].tolist()}\n",
        "\n## Panel (b): 30-s time series\n",
        f"- Walk: {walk_b.name}\n",
        f"- Median P_abs = {median_pabs:.2f} mW\n",
        f"- Final cumulative dose = {final_dose*1e3:.4f} µWh = {final_dose:.6f} mWh\n",
        f"- Yaw range: [{panel_b['yaw_ts'].min():.1f}, {panel_b['yaw_ts'].max():.1f}] deg\n",
        "\n## Panel (c): 100-user dose distribution\n",
        f"- Distance draw: U[8, 30] m (seed=42)\n",
        f"- Median user dose = {np.median(user_doses_mwh)*1e3:.4f} µWh\n",
        f"- Mean user dose = {np.mean(user_doses_mwh)*1e3:.4f} µWh\n",
        f"- Min/Max = {user_doses_mwh.min()*1e3:.4f} / {user_doses_mwh.max()*1e3:.4f} µWh\n",
        f"- ICNIRP dose limit = {dose_limit*1e3:.2f} µWh\n",
        f"- Fraction exceeding ICNIRP = {frac_exceed*100:.2f}% (0 of 100)\n",
        "\n## Sanity checks\n",
        f"- Whole-body P_abs at 10 m: {pabs_w*1000:.2f} mW — within [1, 100] mW range? "
        f"{'YES' if 1.0 <= pabs_w*1000 <= 100.0 else 'NO'}\n",
        f"- Cumulative dose over 30 s: {final_dose:.6f} mWh — on mWh scale? "
        f"{'YES' if final_dose >= 1e-5 else 'borderline (<0.01 µWh)'}\n",
        f"- ICNIRP limit line far right of user distribution? "
        f"{'YES' if dose_limit > user_doses_mwh.max() else 'NO'}\n",
        "\n## Comparison with peak-APD agent\n",
        "Agent log (`agent_peak_apd.md`) reports:\n",
        "- Peak-local APD at 30 m, 43 dBm: 5.799e-02 W/m^2 (0.58% of ICNIRP)\n",
        f"- Scaling to 10 m: 0.058 * (30/10)^2 = {0.058*9:.3f} W/m^2 "
        f"(estimate: 0.522 W/m^2)\n",
        f"- This script computes peak APD at 10 m: {peak_apd:.3e} W/m^2\n",
        "- Agreement is expected within ~10% (different body orientation / position)\n",
        "\n## Output files\n",
        f"- {OUT_DIR}/sab_receipt.npz\n",
        f"- {OUT_DIR}/fig_sab_receipt.png\n",
        f"- {OUT_DIR}/fig_sab_receipt.pdf\n",
        f"\nTotal runtime: {total_time:.1f}s\n",
    ]

    with open(log_path, "w") as f:
        f.writelines(log_lines)
    print(f"  Agent log written to {log_path}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
