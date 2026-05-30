"""
S1 hero scenario PoC — body-shadowed LOS at the window.

Single user seated at a desk; BS through a window 30 m away. The user's torso
partially shadows the LOS path. We sweep one DOF (torso yaw about the vertical
axis) and measure:
  - LOS visibility v(theta), then rate R(theta)
  - Absorbed dose P_abs(theta)
  - Pareto: (R(theta), P_abs(theta))

The hero number is R(theta*) - R(theta_baseline) in dB at C(theta*-theta0) <= 1
where C is the comfort cost (one unit ~ 5 deg torso rotation).

This is the load-bearing experiment for `rihb_theory_v2.tex` Lemma 4.2 and
Theorem 5.1 (`thm:los-pareto`). If the dB gain is < +6 dB, the spine is dead.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import matplotlib
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from aegis.geometry.mesh import BodyMesh
from aegis.tissue.fresnel import T0, n_complex


# ---------------------------------------------------------------------------
# Scenario parameters
# ---------------------------------------------------------------------------
@dataclass
class Scenario:
    """S1: body-shadowed LOS at the window."""

    # Frequency, bandwidth, power
    f_c: float = 28.0e9  # Hz
    bandwidth_hz: float = 100.0e6  # Hz
    p_tx_dbm: float = 43.0
    nf_dB: float = 6.0
    array_gain_dB: float = 18.0  # 64-element URA, beam at phone direction
    scene_loss_dB: float = 35.0  # window + 1 wall at FR2 + interior multipath (binding regime)
    # Geometry: BS through the window, user seated at desk
    bs_position: np.ndarray = None  # set in __post_init__
    body_center: np.ndarray = None
    phone_offset_local: np.ndarray = None  # in body local frame at theta=0
    # Pose sweep — wider, comfort budget chosen post hoc from C(theta)
    theta_min_deg: float = -45.0
    theta_max_deg: float = +45.0
    n_poses: int = 91
    # Comfort cost normalisation: C=1 at 5 deg torso rotation (RULA ~+1)
    comfort_unit_deg: float = 5.0
    # Reporting comfort budgets (C<=1 hero, C<=4 acceptable, C<=9 stretch)
    report_budgets: tuple = (1.0, 4.0, 9.0)  # equivalent to 5, 10, 15 deg
    # MCS27 cap from JSAC v5
    r_max_bps_per_hz: float = 7.4
    # Skin tissue at f_c (28 GHz Gabriel) — pre-computed
    skin_eps_r: float = 16.55
    skin_sigma: float = 25.83  # S/m

    def __post_init__(self) -> None:
        if self.bs_position is None:
            self.bs_position = np.array([0.0, 0.0, 8.0])
        if self.body_center is None:
            # Body's chest center at (30, 0, 1.0). Thelonious is upper-torso
            # only (extent 1.18 m vertical), so translating so chest ~1.0 m
            # gives head around z = 1.6 m.
            self.body_center = np.array([30.0, 0.0, 1.0])
        if self.phone_offset_local is None:
            # Phone held in front of user, arm extended ~55 cm forward at
            # chest height (typical phone-in-hand reach). Body faces +x
            # default; phone is at (+x_local, 0, +z_local). Rotating user
            # +theta about z swings phone in +y_world direction, allowing
            # the phone to come out of the body's shadow line.
            self.phone_offset_local = np.array([0.55, 0.0, 0.10])

    @property
    def lambda_m(self) -> float:
        return 299792458.0 / self.f_c

    @property
    def k0(self) -> float:
        return 2 * np.pi / self.lambda_m

    @property
    def p_tx_w(self) -> float:
        return 10 ** (self.p_tx_dbm / 10) * 1e-3

    @property
    def n_floor_w(self) -> float:
        # k T B with NF
        kT = 1.380649e-23 * 290.0
        return kT * self.bandwidth_hz * 10 ** (self.nf_dB / 10)

    @property
    def fresnel_zone_radius(self, distance: float = 30.0) -> float:
        # First Fresnel zone half-width at midpoint between BS and phone
        return float(np.sqrt(self.lambda_m * distance / 2))


# ---------------------------------------------------------------------------
# Mesh utilities: rotate around vertical axis at body center
# ---------------------------------------------------------------------------
def load_thelonious(scenario: Scenario, stl_path: str = "/home/user/aegis/data/thelonious.stl") -> tuple[BodyMesh, trimesh.Trimesh]:
    """Load via aegis BodyMesh (for Q_abs) and trimesh.Trimesh (for ray casting).

    The trimesh object is returned in mesh-local coordinates; transform per pose.
    """
    mesh = BodyMesh.load(stl_path)
    tm = trimesh.load(stl_path, process=True)
    # Trimesh STL loads in mm or m depending on the file; align with BodyMesh
    # by scale-detection: compare first vertex magnitude.
    if abs(tm.vertices.max() - mesh.bounding_box[1].max()) > 0.5:
        tm.apply_scale(0.001)  # mm -> m
    return mesh, tm


def world_centroids_normals(
    mesh: BodyMesh, scenario: Scenario, theta_rad: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return world-frame (centroids, normals, areas) after torso rotation.

    The body's local frame is aligned with mesh axes, then rotated by theta
    about z, then translated to scenario.body_center.
    """
    centroids_local = mesh.centroids - mesh.center
    normals_local = mesh.normals
    cos_t = np.cos(theta_rad)
    sin_t = np.sin(theta_rad)
    R = np.array([[cos_t, -sin_t, 0.0], [sin_t, cos_t, 0.0], [0.0, 0.0, 1.0]])
    cents_world = centroids_local @ R.T + scenario.body_center
    norms_world = normals_local @ R.T
    return cents_world, norms_world, mesh.areas


def world_phone_position(scenario: Scenario, theta_rad: float) -> np.ndarray:
    cos_t = np.cos(theta_rad)
    sin_t = np.sin(theta_rad)
    R = np.array([[cos_t, -sin_t, 0.0], [sin_t, cos_t, 0.0], [0.0, 0.0, 1.0]])
    return scenario.body_center + R @ scenario.phone_offset_local


# ---------------------------------------------------------------------------
# Visibility v(theta): LOS through body using ray-mesh intersection over a
# bundle of sub-rays sampling the first Fresnel zone.
# ---------------------------------------------------------------------------
def transform_trimesh(tm: trimesh.Trimesh, scenario: Scenario, theta_rad: float) -> trimesh.Trimesh:
    """Return a copy of the trimesh rotated by theta_rad about z and translated."""
    cos_t = np.cos(theta_rad)
    sin_t = np.sin(theta_rad)
    R = np.array([[cos_t, -sin_t, 0.0, 0.0],
                  [sin_t, cos_t, 0.0, 0.0],
                  [0.0, 0.0, 1.0, 0.0],
                  [0.0, 0.0, 0.0, 1.0]])
    # Mesh has its own center; first translate to origin, rotate, translate to body_center
    centering = np.eye(4)
    centering[:3, 3] = -np.mean(tm.bounds, axis=0)
    placement = np.eye(4)
    placement[:3, 3] = scenario.body_center
    T = placement @ R @ centering
    new_tm = tm.copy()
    new_tm.apply_transform(T)
    return new_tm


def los_visibility(
    tm_world: trimesh.Trimesh,
    bs_pos: np.ndarray,
    phone_pos: np.ndarray,
    fresnel_zone_radius: float,
    n_subrays: int = 49,
) -> float:
    """LOS visibility fraction via trimesh ray-mesh intersection on a bundle
    of n_subrays sampling the first Fresnel zone.
    """
    los_dir = phone_pos - bs_pos
    los_len = np.linalg.norm(los_dir)
    los_unit = los_dir / los_len
    if abs(los_unit[2]) < 0.9:
        perp_a = np.cross(los_unit, np.array([0.0, 0.0, 1.0]))
    else:
        perp_a = np.cross(los_unit, np.array([1.0, 0.0, 0.0]))
    perp_a /= np.linalg.norm(perp_a)
    perp_b = np.cross(los_unit, perp_a)

    n_side = int(np.ceil(np.sqrt(n_subrays)))
    offsets = np.linspace(-1.0, 1.0, n_side)
    grid_a, grid_b = np.meshgrid(offsets, offsets)
    grid_a = grid_a.flatten()
    grid_b = grid_b.flatten()
    in_disk = (grid_a**2 + grid_b**2) <= 1.0
    grid_a = grid_a[in_disk]
    grid_b = grid_b[in_disk]
    n_actual = len(grid_a)

    radius = fresnel_zone_radius * 0.5
    origins = bs_pos[None, :] + (
        grid_a[:, None] * radius * perp_a[None, :]
        + grid_b[:, None] * radius * perp_b[None, :]
    )
    targets = phone_pos[None, :] + (
        grid_a[:, None] * radius * perp_a[None, :]
        + grid_b[:, None] * radius * perp_b[None, :]
    )
    directions = targets - origins
    dir_norms = np.linalg.norm(directions, axis=1, keepdims=True)
    directions = directions / dir_norms

    # trimesh ray test (returns hit per-ray boolean via intersects_any)
    intersector = trimesh.ray.ray_triangle.RayMeshIntersector(tm_world)
    hits = intersector.intersects_any(origins, directions)
    # only count hits within the segment length (they should be, since target is past body)
    n_unblocked = int((~hits).sum())
    return n_unblocked / n_actual


# ---------------------------------------------------------------------------
# Absorbed dose: integrate incident power over front-facing area.
# Uses S_ab = S_inc * T0 * mu = (P_tx / 4 pi r^2) * T0 * mu
# at each triangle (LOS-only, no multipath in PoC).
# ---------------------------------------------------------------------------
def absorbed_dose_w(
    centroids: np.ndarray,
    normals: np.ndarray,
    areas: np.ndarray,
    bs_pos: np.ndarray,
    p_tx_w: float,
    t0_skin: float,
) -> float:
    """Total absorbed power (W) on the front-facing area for a LOS path."""
    # Direction from each triangle to BS (incident wave goes the opposite way)
    delta = bs_pos[None, :] - centroids  # (N, 3)
    r = np.linalg.norm(delta, axis=1)
    k_to_bs = delta / r[:, None]
    # Incident wave direction is -k_to_bs (BS toward triangle)
    k_inc = -k_to_bs
    mu = -(normals * k_inc).sum(axis=1)
    front = mu > 0
    if not np.any(front):
        return 0.0

    s_inc = p_tx_w / (4 * np.pi * r**2)  # W/m^2 at each triangle
    s_ab = s_inc * t0_skin * np.where(front, mu, 0.0)
    return float((s_ab * areas).sum())


# ---------------------------------------------------------------------------
# Rate model
# ---------------------------------------------------------------------------
def rate_bps(
    visibility_v: float,
    los_distance: float,
    scenario: Scenario,
) -> tuple[float, float, float]:
    """Achievable rate in bps from the LOS amplitude attenuation v(theta).

    Returns (capped_rate_bps, uncapped_rate_bps_per_hz, sinr_dB).
    """
    G_array_lin = 10 ** (scenario.array_gain_dB / 10)
    scene_loss_lin = 10 ** (-scenario.scene_loss_dB / 10)
    free_space_loss_lin = (4 * np.pi * los_distance / scenario.lambda_m) ** -2
    h_los_sq = visibility_v**2 * free_space_loss_lin * G_array_lin * scene_loss_lin
    rx_power_w = scenario.p_tx_w * h_los_sq
    sinr = rx_power_w / scenario.n_floor_w
    rate_uncapped_bps_per_hz = np.log2(1 + sinr)
    rate_bps_per_hz = min(rate_uncapped_bps_per_hz, scenario.r_max_bps_per_hz)
    return (
        float(rate_bps_per_hz * scenario.bandwidth_hz),
        float(rate_uncapped_bps_per_hz),
        float(10 * np.log10(max(sinr, 1e-12))),
    )


# ---------------------------------------------------------------------------
# Pose sweep driver
# ---------------------------------------------------------------------------
def run_sweep(scenario: Scenario, mesh: BodyMesh, tm: trimesh.Trimesh) -> dict:
    """Sweep torso yaw and return per-pose (visibility, dose, rate)."""
    n_tilde = n_complex(scenario.skin_eps_r, scenario.skin_sigma, scenario.f_c)
    t0_skin = T0(n_tilde)
    fresnel_radius = scenario.fresnel_zone_radius

    print(f"Skin: T0 = {t0_skin:.4f}, 1-T0 = {1 - t0_skin:.4f}")
    print(f"Fresnel zone radius @ 30 m: {fresnel_radius * 100:.1f} cm")

    thetas_deg = np.linspace(scenario.theta_min_deg, scenario.theta_max_deg, scenario.n_poses)
    visibility = np.zeros_like(thetas_deg)
    dose = np.zeros_like(thetas_deg)
    rate = np.zeros_like(thetas_deg)
    rate_uncapped_bphz = np.zeros_like(thetas_deg)
    sinr_dB = np.zeros_like(thetas_deg)
    los_lengths = np.zeros_like(thetas_deg)

    t0 = time.time()
    for i, theta_deg in enumerate(thetas_deg):
        theta_rad = np.deg2rad(theta_deg)
        cents, norms, areas = world_centroids_normals(mesh, scenario, theta_rad)
        phone_pos = world_phone_position(scenario, theta_rad)
        tm_world = transform_trimesh(tm, scenario, theta_rad)
        v = los_visibility(
            tm_world,
            scenario.bs_position,
            phone_pos,
            fresnel_radius,
            n_subrays=49,
        )
        d_los = float(np.linalg.norm(phone_pos - scenario.bs_position))
        dw = absorbed_dose_w(cents, norms, areas, scenario.bs_position, scenario.p_tx_w, 1 - t0_skin)
        # Dose is independent of v: the body absorbs whether the LOS continues
        # to the phone or not (the absorbing area is the body front, not the
        # phone position).
        r, r_unc, snr_db = rate_bps(v, d_los, scenario)
        visibility[i] = v
        dose[i] = dw
        rate[i] = r
        rate_uncapped_bphz[i] = r_unc
        sinr_dB[i] = snr_db
        los_lengths[i] = d_los

    elapsed = time.time() - t0
    print(f"Sweep done: {scenario.n_poses} poses in {elapsed:.1f} s ({elapsed / scenario.n_poses * 1000:.0f} ms/pose)")

    return {
        "thetas_deg": thetas_deg.tolist(),
        "visibility": visibility.tolist(),
        "dose_w": dose.tolist(),
        "rate_bps": rate.tolist(),
        "rate_uncapped_bphz": rate_uncapped_bphz.tolist(),
        "sinr_dB": sinr_dB.tolist(),
        "los_length_m": los_lengths.tolist(),
        "t0_skin": t0_skin,
        "p_tx_w": scenario.p_tx_w,
        "bandwidth_hz": scenario.bandwidth_hz,
        "elapsed_s": elapsed,
    }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------
def plot_results(results: dict, scenario: Scenario, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    thetas = np.array(results["thetas_deg"])
    visibility = np.array(results["visibility"])
    dose_w = np.array(results["dose_w"])
    rate_bps = np.array(results["rate_bps"])
    rate_uncapped_bphz = np.array(results["rate_uncapped_bphz"])
    sinr_dB = np.array(results["sinr_dB"])
    rate_gbps = rate_bps / 1e9

    # Baseline (theta=0)
    baseline_idx = int(np.argmin(np.abs(thetas)))
    # Comfort cost C(theta) = (theta / comfort_unit_deg)^2
    C = (thetas / scenario.comfort_unit_deg) ** 2

    # Hero numbers across budget tiers
    print()
    print(f"Baseline (theta=0): R = {rate_bps[baseline_idx] / 1e9:.3f} Gbps, "
          f"R_uncapped = {rate_uncapped_bphz[baseline_idx]:.2f} bps/Hz, "
          f"SINR = {sinr_dB[baseline_idx]:.1f} dB, "
          f"P_abs = {dose_w[baseline_idx] * 1000:.3f} mW")
    summary_per_budget = {}
    for budget in scenario.report_budgets:
        in_comfort = C <= budget
        if not np.any(in_comfort):
            continue
        rate_in = rate_bps[in_comfort]
        idx_local = int(np.argmax(rate_in))
        idx_global = int(np.where(in_comfort)[0][idx_local])
        rate_gain_db = 10 * np.log10(rate_bps[idx_global] / max(rate_bps[baseline_idx], 1.0))
        sinr_gain_db = sinr_dB[idx_global] - sinr_dB[baseline_idx]
        dose_change_db = 10 * np.log10(dose_w[idx_global] / max(dose_w[baseline_idx], 1e-15))
        equiv_deg = scenario.comfort_unit_deg * np.sqrt(budget)
        summary_per_budget[budget] = {
            "theta_opt_deg": float(thetas[idx_global]),
            "rate_gain_dB": float(rate_gain_db),
            "sinr_gain_dB": float(sinr_gain_db),
            "dose_change_dB": float(dose_change_db),
            "rate_gbps_opt": float(rate_bps[idx_global] / 1e9),
            "dose_mW_opt": float(dose_w[idx_global] * 1000),
        }
        print(f"At C<={budget:.0f} (~{equiv_deg:.0f} deg): theta_opt={thetas[idx_global]:+.1f} deg, "
              f"R={rate_bps[idx_global]/1e9:.3f} Gbps, "
              f"R gain={rate_gain_db:+.2f} dB, "
              f"SINR gain={sinr_gain_db:+.2f} dB, "
              f"dose change={dose_change_db:+.2f} dB")

    # Pick the headline at C<=4
    headline = summary_per_budget.get(4.0) or list(summary_per_budget.values())[0]
    rate_gain_db = headline["rate_gain_dB"]
    dose_change_db = headline["dose_change_dB"]

    # Figure 1: 4-panel diagnostic
    fig, axes = plt.subplots(2, 2, figsize=(11.0, 7.5))

    # Top-left: rate (capped + uncapped)
    ax = axes[0, 0]
    ax.plot(thetas, rate_uncapped_bphz, "C7--", lw=1, label="Shannon (uncapped)")
    ax.axhline(scenario.r_max_bps_per_hz, color="C3", lw=1, ls=":", label=f"MCS27 cap = {scenario.r_max_bps_per_hz:.1f} bps/Hz")
    ax.plot(thetas, rate_bps / scenario.bandwidth_hz, "C0-", lw=2, label="Achievable")
    ax.set_xlabel(r"Torso yaw $\theta$ (deg)")
    ax.set_ylabel("Rate (bps/Hz)")
    ax.axvline(0, color="k", lw=0.5, ls=":")
    for budget in scenario.report_budgets:
        d = scenario.comfort_unit_deg * np.sqrt(budget)
        ax.axvspan(-d, d, color="C2", alpha=0.05)
    ax.legend(loc="lower center")
    ax.set_title("Rate vs pose")

    # Top-right: SINR
    ax = axes[0, 1]
    ax.plot(thetas, sinr_dB, "C0-", lw=2)
    ax.axhline(np.log2(2 ** scenario.r_max_bps_per_hz - 1) * 10 / np.log2(np.e ** np.log(10)), color="C3", lw=1, ls=":")  # cap-equivalent SINR
    # Approximate: SINR threshold for cap = 10 log10(2^7.4 - 1) = 22.25 dB
    ax.axhline(22.25, color="C3", lw=1, ls=":", label="MCS27 SINR threshold")
    ax.set_xlabel(r"Torso yaw $\theta$ (deg)")
    ax.set_ylabel("SINR (dB)")
    ax.axvline(0, color="k", lw=0.5, ls=":")
    ax.legend()
    ax.set_title("SINR vs pose")

    # Bottom-left: dose
    ax = axes[1, 0]
    ax.plot(thetas, dose_w * 1e3, "C3-", lw=2)
    ax.set_xlabel(r"Torso yaw $\theta$ (deg)")
    ax.set_ylabel("Absorbed power (mW)")
    ax.axvline(0, color="k", lw=0.5, ls=":")
    ax.set_title(f"Dose vs pose (range +/- {50*(dose_w.max()-dose_w.min())/dose_w.mean():.1f}%)")

    # Bottom-right: visibility
    ax = axes[1, 1]
    ax.plot(thetas, visibility, "C2-", lw=2)
    ax.set_xlabel(r"Torso yaw $\theta$ (deg)")
    ax.set_ylabel(r"LOS visibility $v(\theta)$")
    ax.axvline(0, color="k", lw=0.5, ls=":")
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("LOS visibility")

    fig.suptitle(f"S1: BS at {scenario.bs_position}, body at {scenario.body_center}, scene loss {scenario.scene_loss_dB:.0f} dB")
    fig.tight_layout()
    p1 = out_dir / "rate_dose_vs_pose.png"
    fig.savefig(p1, dpi=150)
    plt.close(fig)

    # Figure 2: Pareto with comfort budget annotation
    fig, ax = plt.subplots(figsize=(7.5, 5.0))
    C_arr = (thetas / scenario.comfort_unit_deg) ** 2
    sc = ax.scatter(dose_w * 1e3, rate_gbps * 1000, c=C_arr, cmap="viridis", s=30, vmin=0, vmax=16)
    cb = fig.colorbar(sc, ax=ax)
    cb.set_label("Comfort cost C")
    ax.scatter([dose_w[baseline_idx] * 1e3], [rate_gbps[baseline_idx] * 1000],
               s=200, c="red", marker="x", label=f"baseline (theta=0)", zorder=10)
    for budget, marker, color in zip(scenario.report_budgets, ["o", "s", "*"], ["#ffaa00", "#cc6600", "#22aa22"]):
        in_comfort = C_arr <= budget
        if not np.any(in_comfort):
            continue
        idx_local = int(np.argmax(rate_bps[in_comfort]))
        idx = int(np.where(in_comfort)[0][idx_local])
        equiv_deg = scenario.comfort_unit_deg * np.sqrt(budget)
        ax.scatter([dose_w[idx] * 1e3], [rate_gbps[idx] * 1000], s=200, c=color, marker=marker,
                   edgecolors="black", linewidths=1.0,
                   label=f"opt at C<={budget:.0f} (~{equiv_deg:.0f} deg)", zorder=10)
    ax.axhline(scenario.r_max_bps_per_hz * scenario.bandwidth_hz / 1e6,
               color="C3", ls=":", lw=1, label=f"MCS27 cap = {scenario.r_max_bps_per_hz*scenario.bandwidth_hz/1e6:.0f} Mbps")
    ax.set_xlabel("Absorbed power (mW)")
    ax.set_ylabel("Achievable rate (Mbps)")
    ax.set_title("S1 Pareto: pose moves trade rate vs dose")
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    p2 = out_dir / "pareto.png"
    fig.savefig(p2, dpi=150)
    plt.close(fig)

    # Figure 3: visibility vs pose (diagnostic)
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    ax.plot(thetas, visibility, "C2-", lw=2)
    ax.set_xlabel(r"Torso yaw $\theta$ (deg)")
    ax.set_ylabel(r"LOS visibility $v(\theta)$")
    ax.axvline(0, color="k", lw=0.5, ls=":")
    ax.set_ylim(-0.05, 1.05)
    fig.tight_layout()
    p3 = out_dir / "visibility.png"
    fig.savefig(p3, dpi=150)
    plt.close(fig)

    return {
        "baseline_idx": baseline_idx,
        "summary_per_budget": summary_per_budget,
        "headline_rate_gain_db": float(rate_gain_db),
        "headline_dose_change_db": float(dose_change_db),
        "figures": [str(p1), str(p2), str(p3)],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(out_dir: Path = Path("/home/user/aegis/JSAC2/poc/s1_window/figures")) -> int:
    scenario = Scenario()
    print("Scenario:")
    print(f"  f_c = {scenario.f_c / 1e9:.1f} GHz, lambda = {scenario.lambda_m * 1000:.2f} mm")
    print(f"  P_tx = {scenario.p_tx_dbm:.1f} dBm = {scenario.p_tx_w * 1000:.1f} mW")
    print(f"  N_floor = {10 * np.log10(scenario.n_floor_w * 1e3):.1f} dBm")
    print(f"  BS @ {scenario.bs_position}, body @ {scenario.body_center}, phone offset {scenario.phone_offset_local}")

    mesh, tm = load_thelonious(scenario)
    print(f"  Mesh: {mesh.n_triangles} triangles, extent {mesh.bounding_box[1] - mesh.bounding_box[0]} m")

    results = run_sweep(scenario, mesh, tm)
    summary = plot_results(results, scenario, out_dir)
    results["summary"] = summary

    out_json = out_dir / "results.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print()
    print(f"Wrote {out_json}")
    for fig in summary["figures"]:
        print(f"Wrote {fig}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("/home/user/aegis/JSAC2/poc/s1_window/figures"))
    args = parser.parse_args()
    raise SystemExit(main(args.out))
