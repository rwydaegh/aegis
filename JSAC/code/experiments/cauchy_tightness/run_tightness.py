"""Empirical tightness of the rank-1 Cauchy bound on the coherent operator Q.

Paper Theorem 2 (`paper_v2.tex` eq:cauchy-bound-op):

    x^H Q^{(u)} x  <=  T_0 * (A_ab^{(u)}/4) * D_max^{(u)} * |a_BS^{(u)}^H x|^2

This is the pose-agnostic safety net invoked for tier-C/D bystanders (the
bodies the BS does not have pose telemetry on). The paper never reports how
*tight* it is. If the bound overshoots actual x^H Q x by 6 dB on average,
every tier-C bystander costs the precoder ~6 dB of |a^H x|^2 capacity --
real and acknowledgeable. If it is tight to ~1 dB, the safety net is
essentially free.

This script measures the empirical ratio LHS/RHS in dB on Thelonious + Duke
+ Eartha + Ella, across plaza-specular and 3GPP UMa-LOS channel models,
and across four precoder ensembles:

    iso_random    : Gaussian unit precoders (the fully-uninformed baseline).
    mrt_random    : MRT toward a random user direction (`x ~ a_user*`).
    mrt_los       : MRT aligned with the body's LOS direction (`x ~ a*`,
                    the rank-1 saturating direction in the bound).
    ecbf          : ECBF outputs against a random user channel with the
                    body's Q as the absorption operator.
    zf_2user      : Two-user ZF (one user is the body LOS direction,
                    one is at a random direction).

Dimensional convention. The bound as written is dimensionally consistent
only if `a` carries the LOS path's E-field amplitude. We use

    a_los[m] = (psi_1m / r_body) * gain_LOS * exp(j k0 k_LOS . d_m)
    psi_1m = sqrt(2 Z_0 P_tx / (4 pi))
    RHS = T_0 * (A_ab/4) * D_max * |a_los^H x|^2 / (2 Z_0)

so |a_los^H x|^2 / (2 Z_0) is in W/m^2 (LOS-aligned power flux at body),
times A_ab/4 (m^2) gives Watts. This matches x^H Q x (Watts).

Outputs:
    tightness.{pdf,png}     CDF of LHS/RHS by channel x ensemble.
    ratios.npz              raw ratios per (body, position, channel, ensemble).
    summary.json            summary stats per ensemble x channel x body.
    README.md               numbers + commentary on the tier-C/D capacity tax.
"""

from __future__ import annotations

import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

# Make the in-repo 'aegis' package importable regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import matplotlib.pyplot as plt
import numpy as np

from aegis.channel.generator import generate_channel
from aegis.channel.presets import load_preset
from aegis.coherent.body_channel import compute_body_channel_factored
from aegis.coherent.ecbf import solve_ecbf
from aegis.coherent.exposure_operator import compute_exposure_operator
from aegis.constants import C_0, Z_0
from aegis.geometry.mesh import BodyMesh
from aegis.geometry.projected_area import compute_projected_area, fibonacci_sphere
from aegis.mimo.array import AntennaArray
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import TissueModel

# ---------------------------------------------------------------------------
# Scenario constants -- mirror rank_check so the two figures stay comparable
# ---------------------------------------------------------------------------
FREQ_HZ = 26.0e9
FREQ_GHZ = FREQ_HZ / 1e9
LAMBDA = C_0 / FREQ_HZ
N_H = 8
N_V = 8
D = LAMBDA / 2.0
BS_CENTER = np.array([0.0, 0.0, 8.0])
TILT_DEG = 10.0
BROADSIDE = np.array(
    [np.cos(np.deg2rad(TILT_DEG)), 0.0, -np.sin(np.deg2rad(TILT_DEG))]
)

FACADE_Y = 20.0
N_BODIES = 6  # positions per phantom
N_FIB = 256  # Fibonacci sphere directions for D_max / A_ab estimate
RANGE_MIN, RANGE_MAX = 20.0, 80.0
AZ_HALF_DEG = 60.0
RNG_SEED = 4242

REFL_GROUND = 0.55
REFL_FACADE = 0.35

TX_POWER_W = 10.0
TX_POWER_DBM = 10.0 * np.log10(TX_POWER_W * 1e3)

PRESET_NAME = "3GPP_38.901_UMa_LOS"
PRESET_DIR = Path("/home/user/aegis/data/channel_presets")
STOCHASTIC_SUBPATHS = 5  # match rank_check (12 clusters x 5 = 60 paths)

_ALL_PHANTOMS = [
    ("thelonious", "/home/user/aegis/data/thelonious.stl"),
    ("duke", "/home/user/aegis/data/duke.stl"),
    ("eartha", "/home/user/aegis/data/eartha.stl"),
    ("ella", "/home/user/aegis/data/ella.stl"),
]
# Default: 2 phantoms (Thelonious + Duke) -- runtime host is 8 GB RAM /
# 4 cores and shared with other sessions. Set CAUCHY_TIGHTNESS_FULL=1 on
# a beefier host (~16 GB+) to include eartha + ella for full demographic
# spread.
_FULL = os.environ.get("CAUCHY_TIGHTNESS_FULL", "0") == "1"
PHANTOMS = _ALL_PHANTOMS if _FULL else _ALL_PHANTOMS[:2]

CHANNEL_MODELS = ("specular", "stochastic")

# Precoder ensembles. Sample sizes balance statistical noise vs runtime.
ENSEMBLE_SIZES = {
    "iso_random": 200,
    "mrt_random": 60,
    "mrt_los": 1,
    "ecbf": 30,
    "zf_2user": 60,
}

# Tissue at 26 GHz (skin, the conservative outer-tissue model).
try:
    TISSUE = TissueModel.from_database("Skin", FREQ_HZ)
except Exception:  # noqa: BLE001
    TISSUE = TissueModel("Skin 26 GHz", eps_r=17.4, sigma=23.5, freq_hz=FREQ_HZ)
T0 = TISSUE.T0


# ---------------------------------------------------------------------------
# Body geometry analytics: A_ab/4 = mean(A_perp), D_max = max(A_perp)/<A_perp>
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class BodyAnalytics:
    name: str
    A_ab_over_4: float
    D_max: float
    total_area: float


def compute_body_analytics(body: BodyMesh) -> BodyAnalytics:
    """Compute (A_ab/4) and D_max for a body via Fibonacci-sphere sampling.

    Convention: A_ab = 4 * <A_perp>, so A_ab/4 = mean(A_perp). For convex
    bodies this equals total_area/4 (Cauchy 1841); for non-convex like
    Thelonious it is slightly smaller due to self-occlusion.

    D(k) = A_perp(k) / <A_perp>, so D_max = max(A_perp) / mean(A_perp).
    """
    k_hat = fibonacci_sphere(N_FIB)
    A_perp = compute_projected_area(body.normals, body.areas, k_hat)
    A_perp_mean = float(np.mean(A_perp))
    A_perp_max = float(np.max(A_perp))
    return BodyAnalytics(
        name=body.name,
        A_ab_over_4=A_perp_mean,
        D_max=A_perp_max / A_perp_mean if A_perp_mean > 0 else 0.0,
        total_area=float(body.total_area),
    )


# ---------------------------------------------------------------------------
# Path builders -- copied from rank_check for consistency
# ---------------------------------------------------------------------------
def _reflect_point(p: np.ndarray, plane_point: np.ndarray, plane_normal: np.ndarray) -> np.ndarray:
    d = np.dot(p - plane_point, plane_normal)
    return p - 2.0 * d * plane_normal


def _perpendicular_pol(k_hat: np.ndarray) -> np.ndarray:
    z = np.array([0.0, 0.0, 1.0])
    ref = z if abs(k_hat[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
    e = np.cross(k_hat, ref)
    return e / np.linalg.norm(e)


def build_specular_paths(
    bs_center: np.ndarray,
    body_target: np.ndarray,
    tx_power_w: float = TX_POWER_W,
) -> PropagationPaths:
    sources = [
        ("los", bs_center, 1.0),
        (
            "ground",
            _reflect_point(bs_center, np.zeros(3), np.array([0.0, 0.0, 1.0])),
            REFL_GROUND,
        ),
        (
            "facade_plus",
            _reflect_point(bs_center, np.array([0.0, +FACADE_Y, 0.0]), np.array([0.0, -1.0, 0.0])),
            REFL_FACADE,
        ),
        (
            "facade_minus",
            _reflect_point(bs_center, np.array([0.0, -FACADE_Y, 0.0]), np.array([0.0, +1.0, 0.0])),
            REFL_FACADE,
        ),
    ]
    k_hats, psis, delays, is_los = [], [], [], []
    psi_1m = np.sqrt(2.0 * Z_0 * tx_power_w / (4.0 * np.pi))
    for name, source, refl in sources:
        direction = body_target - source
        dist = float(np.linalg.norm(direction))
        k_hat = direction / dist
        amp = psi_1m * refl / dist
        e_pol = _perpendicular_pol(k_hat)
        psi = (amp * e_pol).astype(complex)
        k_hats.append(k_hat)
        psis.append(psi)
        delays.append(dist / C_0)
        is_los.append(name == "los")
    return PropagationPaths(
        k_hat=np.stack(k_hats),
        psi=np.stack(psis),
        element_index=np.zeros(len(sources), dtype=np.intp),
        delay=np.array(delays),
        is_los=np.array(is_los, dtype=bool),
    )


_PRESET_CACHE: dict | None = None


def _get_preset() -> dict:
    global _PRESET_CACHE
    if _PRESET_CACHE is None:
        _PRESET_CACHE = load_preset(PRESET_NAME, PRESET_DIR)
    return _PRESET_CACHE


def build_stochastic_paths(
    bs_center: np.ndarray,
    body_target: np.ndarray,
    seed: int,
) -> PropagationPaths:
    return generate_channel(
        params=_get_preset(),
        freq_ghz=FREQ_GHZ,
        antenna_pos=bs_center,
        body_center=body_target,
        power_dbm=TX_POWER_DBM,
        seed=seed,
        overrides={"NumSubPaths": STOCHASTIC_SUBPATHS},
    )


# ---------------------------------------------------------------------------
# LOS BS-side amplitude steering vector (the `a` in the bound)
# ---------------------------------------------------------------------------
def los_amplitude_vector(
    array: AntennaArray,
    body_centroid: np.ndarray,
    freq_hz: float,
    tx_power_w: float,
) -> np.ndarray:
    """Build a_los: per-element complex amplitude of the LOS path at body.

    a_los[m] = (psi_1m / r) * gain(k_LOS) * exp(j k0 k_LOS . d_m)

    Magnitude carries the LOS field strength (V/m) so |a_los^H x|^2 / (2Z_0)
    is in W/m^2 (LOS-aligned power flux at the body for unit precoder).
    """
    direction = body_centroid - array.reference_position
    r = float(np.linalg.norm(direction))
    k_LOS = direction / r
    psi_1m = np.sqrt(2.0 * Z_0 * tx_power_w / (4.0 * np.pi))
    a_phase = array.steering_vector(k_LOS, freq_hz)  # (M,) complex
    return (psi_1m / r) * a_phase


# ---------------------------------------------------------------------------
# Q assembly
# ---------------------------------------------------------------------------
def place_body(base_body: BodyMesh, offset_xy: np.ndarray) -> BodyMesh:
    v = base_body.vertices.reshape(-1, 3)
    z_min = float(v[:, 2].min())
    shift = np.array([offset_xy[0], offset_xy[1], -z_min])
    vertices = base_body.vertices + shift[None, None, :]
    centroids = base_body.centroids + shift[None, :]
    return BodyMesh(
        vertices=vertices,
        normals=base_body.normals.copy(),
        centroids=centroids,
        areas=base_body.areas.copy(),
        name=base_body.name,
    )


def sample_body_positions(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    r = np.sqrt(rng.uniform(RANGE_MIN**2, RANGE_MAX**2, size=n))
    az = rng.uniform(-np.deg2rad(AZ_HALF_DEG), np.deg2rad(AZ_HALF_DEG), size=n)
    return np.stack([r * np.cos(az), r * np.sin(az)], axis=1)


def compute_Q(body: BodyMesh, array: AntennaArray, center_paths: PropagationPaths) -> np.ndarray:
    array_paths = expand_paths_to_array(center_paths, array, FREQ_HZ)
    G_tilde = compute_body_channel_factored(
        normals=body.normals,
        centroids=body.centroids,
        center_k_hat=center_paths.k_hat,
        center_psi=center_paths.psi,
        element_psi=array_paths.psi,
        element_index=array_paths.element_index,
        n_tilde=TISSUE.n_complex,
        sigma=TISSUE.sigma,
        freq_hz=FREQ_HZ,
        n_elements=array.n_elements,
    )
    return compute_exposure_operator(G_tilde, body.areas)


# ---------------------------------------------------------------------------
# Precoder ensembles
# ---------------------------------------------------------------------------
def _normalise(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x)
    return x / n if n > 0 else x


def random_user_steering(array: AntennaArray, freq_hz: float, rng: np.random.Generator) -> np.ndarray:
    """A random unit direction in the front hemisphere of the array's broadside.

    Returns the steering vector (with element gain) for that direction.
    Models a user the BS would reasonably try to serve.
    """
    while True:
        v = rng.standard_normal(3)
        v /= np.linalg.norm(v)
        if v @ array.broadside > 0.2:  # at least 78 deg from boresight axis
            return array.steering_vector(v, freq_hz)


def sample_precoders(
    ensemble: str,
    Q: np.ndarray,
    a_los: np.ndarray,
    array: AntennaArray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Return (N, M_ant) complex precoders for the chosen ensemble.

    All precoders are unit-norm. The bound is homogeneous degree-2 in x,
    so |a^H x|^2 and x^H Q x both scale the same way -- normalising x to
    unit norm is a convention, not a constraint.
    """
    M = a_los.shape[0]
    N = ENSEMBLE_SIZES[ensemble]

    if ensemble == "iso_random":
        x = rng.standard_normal((N, M)) + 1j * rng.standard_normal((N, M))
    elif ensemble == "mrt_random":
        x = np.zeros((N, M), dtype=complex)
        for i in range(N):
            h = random_user_steering(array, FREQ_HZ, rng)
            x[i] = h.conj()  # MRT
    elif ensemble == "mrt_los":
        # The bound's RHS is |a^H x|^2, which by Cauchy-Schwarz is maximised
        # at x = a / ||a|| (not at x = a*/||a||, despite the more usual "MRT"
        # convention -- AEGIS treats `signal = h^T x` so MRT-to-h is x = h*).
        # Here the relevant optimisation is the rank-1 RHS, so x = a.
        x = a_los[None, :]
    elif ensemble == "ecbf":
        # Sweep ECBF with random user channels and varying P_abs_max budgets.
        x = np.zeros((N, M), dtype=complex)
        # Build a reference: peak xQx achievable at unit norm = lambda_max(Q).
        lam_max = float(np.linalg.eigvalsh(Q).max())
        for i in range(N):
            h = random_user_steering(array, FREQ_HZ, rng)
            # Pick budget anywhere from 5% to 80% of the rank-1 ceiling
            # (unit-norm precoder so xQx <= lam_max).
            budget_frac = rng.uniform(0.05, 0.8)
            P_abs_max = max(budget_frac * lam_max, 1e-30)
            try:
                x_star = solve_ecbf(h, Q, P_abs_max=P_abs_max, P=1.0)
            except Exception:  # noqa: BLE001
                x_star = h.conj()
            x[i] = np.asarray(x_star)
    elif ensemble == "zf_2user":
        # Two-user ZF among real users (the body is *not* in the user list -
        # it is a tier-C bystander, by definition unknown to the BS).
        # Precoder for served user 0 = ((H^H)(H H^H)^{-1})_col0.
        x = np.zeros((N, M), dtype=complex)
        for i in range(N):
            h0 = random_user_steering(array, FREQ_HZ, rng)
            h0 /= max(np.linalg.norm(h0), 1e-30)
            h1 = random_user_steering(array, FREQ_HZ, rng)
            h1 /= max(np.linalg.norm(h1), 1e-30)
            H = np.stack([h0, h1], axis=0)  # (2, M)
            try:
                G = H @ H.conj().T  # (2,2) Gram
                W = H.conj().T @ np.linalg.inv(G)  # (M, 2) ZF precoders
                x[i] = W[:, 0]
            except np.linalg.LinAlgError:
                x[i] = h0.conj()
    else:
        raise ValueError(f"unknown ensemble {ensemble!r}")

    # Normalise rows to unit norm
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    norms = np.where(norms > 0, norms, 1.0)
    return x / norms


# ---------------------------------------------------------------------------
# Bound evaluation
# ---------------------------------------------------------------------------
def evaluate_ratios(
    Q: np.ndarray,
    a_los: np.ndarray,
    body_anal: BodyAnalytics,
    array: AntennaArray,
    rng: np.random.Generator,
) -> dict[str, np.ndarray]:
    """For each ensemble, compute LHS/RHS in dB.

    LHS = x^H Q x  (Watts, real, >= 0)
    RHS = T_0 * (A_ab/4) * D_max * |a_los^H x|^2 / (2 Z_0)  (Watts)

    The bound holds iff LHS <= RHS, i.e., LHS/RHS <= 1, i.e., dB ratio <= 0.
    """
    out: dict[str, np.ndarray] = {}
    rhs_const = T0 * body_anal.A_ab_over_4 * body_anal.D_max / (2.0 * Z_0)
    for ensemble in ENSEMBLE_SIZES:
        X = sample_precoders(ensemble, Q, a_los, array, rng)  # (N, M)
        # LHS_i = x_i^H Q x_i
        Qx = X @ Q.T  # (N, M); note Q is Hermitian so Q.T = Q.conj()
        lhs = np.real(np.einsum("ni,ni->n", X.conj(), Qx))
        # |a^H x|^2
        inner = X @ a_los.conj()  # (N,)
        rhs = rhs_const * np.abs(inner) ** 2
        # Ratio in dB; floor RHS to avoid log(0) (e.g. for ZF in the LOS null).
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio_db = 10.0 * np.log10(np.maximum(lhs, 1e-300) / np.maximum(rhs, 1e-300))
        out[ensemble] = ratio_db
    return out


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
_WORKER_STATE: dict = {}


def _worker_init(phantoms: list[tuple[str, str]]):
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    array = AntennaArray.upa(
        n_h=N_H,
        n_v=N_V,
        d_h=D,
        d_v=D,
        center=BS_CENTER,
        broadside=BROADSIDE,
        element_pattern="patch",
    )
    bodies: dict[str, BodyMesh] = {}
    analytics: dict[str, BodyAnalytics] = {}
    for name, path in phantoms:
        b = BodyMesh.load(path)
        bodies[name] = b
        analytics[name] = compute_body_analytics(b)
    _WORKER_STATE["array"] = array
    _WORKER_STATE["bodies"] = bodies
    _WORKER_STATE["analytics"] = analytics


def _worker_task(job: tuple[str, str, int, tuple[float, float], int]) -> tuple:
    """Compute (body, position, channel) ratios for all ensembles."""
    body_name, channel, body_idx, xy, seed = job
    array: AntennaArray = _WORKER_STATE["array"]
    base_body: BodyMesh = _WORKER_STATE["bodies"][body_name]
    body_anal: BodyAnalytics = _WORKER_STATE["analytics"][body_name]

    body = place_body(base_body, np.asarray(xy))
    body_target = body.centroids.mean(axis=0)

    if channel == "specular":
        center_paths = build_specular_paths(BS_CENTER, body_target)
    elif channel == "stochastic":
        center_paths = build_stochastic_paths(BS_CENTER, body_target, seed=seed)
    else:
        raise ValueError(f"unknown channel {channel!r}")

    Q = np.asarray(compute_Q(body, array, center_paths))
    a_los = los_amplitude_vector(array, body_target, FREQ_HZ, TX_POWER_W)
    rng = np.random.default_rng(seed + 10_000)
    ratios = evaluate_ratios(Q, a_los, body_anal, array, rng)

    lam_max = float(np.linalg.eigvalsh(Q).max())
    a_norm_sq = float(np.vdot(a_los, a_los).real)
    return (body_name, channel, body_idx, lam_max, a_norm_sq, ratios, Q, a_los)


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
ENSEMBLE_LABELS = {
    "iso_random": "isotropic random (Gaussian)",
    "mrt_random": "MRT to random user direction",
    "mrt_los": "x = a (matched to body LOS direction)",
    "ecbf": "ECBF (random user, swept budget)",
    "zf_2user": "ZF among 2 random users (body unknown)",
}
ENSEMBLE_COLORS = {
    "iso_random": "C0",
    "mrt_random": "C1",
    "mrt_los": "C3",
    "ecbf": "C2",
    "zf_2user": "C4",
}


def plot_panel(ax, ratios: dict[str, np.ndarray], title: str) -> None:
    for ensemble, label in ENSEMBLE_LABELS.items():
        data = ratios.get(ensemble)
        if data is None or len(data) == 0:
            continue
        sorted_data = np.sort(data)
        cdf = np.linspace(0.0, 1.0, len(sorted_data), endpoint=False) + 1.0 / len(sorted_data)
        if ensemble == "mrt_los" and len(sorted_data) <= 5:
            # Render the rank-1-saturating reference as vertical lines, one per body.
            for v in sorted_data:
                ax.axvline(v, color=ENSEMBLE_COLORS[ensemble], linewidth=1.0,
                           alpha=0.6, linestyle="--")
            ax.plot([], [], color=ENSEMBLE_COLORS[ensemble], linewidth=1.0,
                    linestyle="--", label=label)
        else:
            ax.plot(sorted_data, cdf, label=label, color=ENSEMBLE_COLORS[ensemble], linewidth=1.6)
    ax.axvline(0.0, color="k", linewidth=0.9, linestyle=":", alpha=0.7)
    ax.set_xlabel(r"$10\log_{10}(x^H Q x \,/\, \mathrm{RHS})$  [dB]")
    ax.set_ylabel("empirical CDF")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=8)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    out_dir = Path(__file__).parent
    print(f"output dir: {out_dir}")
    print(f"freq: {FREQ_GHZ:.1f} GHz, lambda: {LAMBDA * 1e3:.2f} mm, d: {D * 1e3:.2f} mm")
    print(f"array: {N_H}x{N_V} UPA, {N_H * N_V} elements, {TILT_DEG:.0f} deg down-tilt")
    print(f"tissue: {TISSUE.name} (eps_r={TISSUE.eps_r:.2f}, sigma={TISSUE.sigma:.2f} S/m, T_0={T0:.4f})")

    # Sanity: print body analytics
    for name, path in PHANTOMS:
        b = BodyMesh.load(path)
        anal = compute_body_analytics(b)
        print(f"  {name:11s}  area={anal.total_area:6.3f} m^2,  "
              f"<A_perp>=A_ab/4={anal.A_ab_over_4:6.4f} m^2,  D_max={anal.D_max:.3f}")

    positions = sample_body_positions(N_BODIES, RNG_SEED)
    body_ranges = np.linalg.norm(positions, axis=1)
    print(f"  positions: {N_BODIES} per phantom, "
          f"range {body_ranges.min():.1f}..{body_ranges.max():.1f} m, "
          f"az +/- {AZ_HALF_DEG:.0f} deg")

    # Build job list
    jobs = []
    for body_name, _ in PHANTOMS:
        for channel in CHANNEL_MODELS:
            for body_idx, xy in enumerate(positions):
                seed = RNG_SEED + hash((body_name, channel, body_idx)) % 100_000
                jobs.append((body_name, channel, body_idx, tuple(xy), seed))
    print(f"\ntotal jobs: {len(jobs)}  ({len(PHANTOMS)} phantoms x {len(CHANNEL_MODELS)} channels x {N_BODIES} positions)")

    # Default to 1 worker: this experiment loads multiple phantoms per worker
    # and the stochastic-channel Q assembly peaks at ~1.5 GB. The host has
    # 8 GB RAM shared with several Claude sessions, so 1 worker keeps swap
    # cold. Override with CAUCHY_TIGHTNESS_WORKERS=2 on a beefier host.
    n_workers = int(os.environ.get("CAUCHY_TIGHTNESS_WORKERS", "1"))
    n_workers = min(len(jobs), max(1, n_workers))
    print(f"workers: {n_workers}\n")

    # Storage: ratios[(body, channel, ensemble)] = list[np.ndarray]
    ratios_all: dict[tuple[str, str, str], list[np.ndarray]] = {}
    lam_max_all: dict[tuple[str, str], list[float]] = {}
    a_norm_all: dict[str, list[float]] = {}
    # Stash Q + a_los per (body, channel, position) so finalise.py can
    # iterate on precoder logic without re-running the ~7 min Q sweep.
    Q_stash: dict[tuple[str, str, int], np.ndarray] = {}
    a_stash: dict[tuple[str, str, int], np.ndarray] = {}

    with ProcessPoolExecutor(
        max_workers=n_workers,
        initializer=_worker_init,
        initargs=(PHANTOMS,),
    ) as pool:
        for body_name, channel, body_idx, lam_max, a_norm_sq, ratios, Q, a_los in pool.map(
            _worker_task, jobs
        ):
            for ens, vals in ratios.items():
                ratios_all.setdefault((body_name, channel, ens), []).append(vals)
            lam_max_all.setdefault((body_name, channel), []).append(lam_max)
            a_norm_all.setdefault(body_name, []).append(a_norm_sq)
            Q_stash[(body_name, channel, body_idx)] = Q
            a_stash[(body_name, channel, body_idx)] = a_los
            print(f"  done: {body_name:11s} {channel:10s} pos={body_idx:2d}  "
                  f"lam_max(Q)={lam_max:.3e}  ||a||^2={a_norm_sq:.3e}",
                  flush=True)

    # Aggregate and save raw ratios
    ratios_flat: dict[str, dict[str, np.ndarray]] = {}  # ratios_flat[channel][ensemble] -> all dB values
    for channel in CHANNEL_MODELS:
        ratios_flat[channel] = {}
        for ensemble in ENSEMBLE_SIZES:
            stacks = []
            for body_name, _ in PHANTOMS:
                stacks.extend(ratios_all.get((body_name, channel, ensemble), []))
            if stacks:
                ratios_flat[channel][ensemble] = np.concatenate(stacks)
            else:
                ratios_flat[channel][ensemble] = np.array([])

    # NPZ dump
    npz_payload: dict[str, np.ndarray] = {
        "positions": positions,
        "freq_hz": np.array(FREQ_HZ),
        "T_0": np.array(T0),
        "tx_power_w": np.array(TX_POWER_W),
    }
    for channel, ens_dict in ratios_flat.items():
        for ensemble, vals in ens_dict.items():
            npz_payload[f"ratio_db__{channel}__{ensemble}"] = vals
    for (body_name, channel), vals in lam_max_all.items():
        npz_payload[f"lam_max__{body_name}__{channel}"] = np.array(vals)
    np.savez(out_dir / "ratios.npz", **npz_payload)
    print(f"\nwrote {out_dir / 'ratios.npz'}")

    # Stash Q + a_los so finalise.py can iterate on precoder logic without
    # re-running the Q sweep. Q is (M_ant, M_ant) complex per position --
    # tiny relative to the spectra (~64 KB per Q matrix).
    qa_payload: dict[str, np.ndarray] = {}
    for (body_name, channel, body_idx), Q in Q_stash.items():
        qa_payload[f"Q__{body_name}__{channel}__{body_idx:03d}"] = Q
    for (body_name, channel, body_idx), a in a_stash.items():
        qa_payload[f"a__{body_name}__{channel}__{body_idx:03d}"] = a
    qa_payload["positions"] = positions
    np.savez(out_dir / "q_and_a.npz", **qa_payload)
    print(f"wrote {out_dir / 'q_and_a.npz'}")

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    plot_panel(
        axes[0],
        ratios_flat["specular"],
        "(a) plaza specular (LOS + ground + 2 facades)",
    )
    plot_panel(
        axes[1],
        ratios_flat["stochastic"],
        f"(b) 3GPP UMa-LOS (12 clusters x {STOCHASTIC_SUBPATHS} subpaths)",
    )
    fig.suptitle(
        "Tightness of the rank-1 Cauchy operator bound (Theorem 2)\n"
        rf"$x^H Q x \leq T_0 (A_\mathrm{{ab}}/4) D_\mathrm{{max}} |a^H x|^2$, "
        rf"{len(PHANTOMS)} phantoms, {N_BODIES} positions each, 26 GHz, 8x8 UPA"
    )
    fig.tight_layout()
    fig.savefig(out_dir / "tightness.pdf")
    fig.savefig(out_dir / "tightness.png", dpi=180)
    plt.close(fig)
    print(f"wrote {out_dir / 'tightness.pdf'}")
    print(f"wrote {out_dir / 'tightness.png'}")

    # Numerical summary
    summary: dict = {"by_channel": {}, "by_body_channel": {}}
    for channel, ens_dict in ratios_flat.items():
        summary["by_channel"][channel] = {}
        for ensemble, vals in ens_dict.items():
            if vals.size == 0:
                continue
            summary["by_channel"][channel][ensemble] = {
                "n": int(vals.size),
                "mean_db": float(np.mean(vals)),
                "median_db": float(np.median(vals)),
                "p10_db": float(np.percentile(vals, 10)),
                "p90_db": float(np.percentile(vals, 90)),
                "min_db": float(np.min(vals)),
                "max_db": float(np.max(vals)),
                "fraction_violating": float(np.mean(vals > 0)),
            }
    # Also per-body
    for body_name, _ in PHANTOMS:
        summary["by_body_channel"][body_name] = {}
        for channel in CHANNEL_MODELS:
            summary["by_body_channel"][body_name][channel] = {}
            for ensemble in ENSEMBLE_SIZES:
                stacks = ratios_all.get((body_name, channel, ensemble), [])
                if not stacks:
                    continue
                vals = np.concatenate(stacks)
                summary["by_body_channel"][body_name][channel][ensemble] = {
                    "median_db": float(np.median(vals)),
                    "p90_db": float(np.percentile(vals, 90)),
                    "max_db": float(np.max(vals)),
                }

    summary["constants"] = {
        "freq_hz": FREQ_HZ,
        "T_0": T0,
        "tissue": TISSUE.name,
        "tissue_eps_r": TISSUE.eps_r,
        "tissue_sigma": TISSUE.sigma,
        "tx_power_w": TX_POWER_W,
        "n_h": N_H,
        "n_v": N_V,
    }
    summary["body_analytics"] = {
        name: {
            "A_ab_over_4_m2": _WORKER_STATE.get("analytics", {}).get(name, None).A_ab_over_4
            if _WORKER_STATE.get("analytics", {}).get(name, None) else None,
            "D_max": _WORKER_STATE.get("analytics", {}).get(name, None).D_max
            if _WORKER_STATE.get("analytics", {}).get(name, None) else None,
        }
        for name, _ in PHANTOMS
    }
    # _WORKER_STATE is empty in main proc; recompute:
    summary["body_analytics"] = {}
    for name, path in PHANTOMS:
        b = BodyMesh.load(path)
        anal = compute_body_analytics(b)
        summary["body_analytics"][name] = {
            "total_area_m2": anal.total_area,
            "A_ab_over_4_m2": anal.A_ab_over_4,
            "D_max": anal.D_max,
        }

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"wrote {out_dir / 'summary.json'}")

    # Console summary
    print("\n=== summary: median LHS/RHS in dB by channel x ensemble ===")
    for channel in CHANNEL_MODELS:
        print(f"  channel = {channel}")
        for ensemble in ENSEMBLE_SIZES:
            s = summary["by_channel"][channel].get(ensemble)
            if s is None:
                continue
            print(
                f"    {ensemble:10s}  n={s['n']:5d}  "
                f"med={s['median_db']:+6.2f}  p10={s['p10_db']:+6.2f}  "
                f"p90={s['p90_db']:+6.2f}  max={s['max_db']:+6.2f}  "
                f"frac>0={s['fraction_violating']:.2%}"
            )

    print("\n(LHS/RHS <= 0 dB means bound holds; > 0 dB means bound violated.)")


if __name__ == "__main__":
    main()
