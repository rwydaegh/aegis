"""Deterministic plaza scenario assembly.

Given a seed, builds:
  - the BS antenna array (8x8 patch UPA at 26 GHz, hand-placed on plaza-south
    facade since Brussels parquet has no mmWave sites)
  - 50 SMPL-X body spawns + walk trajectories within the plaza
  - tier assignment 25/15/10 (A served / B cooperating / C bystander),
    static across the run
  - per-body AMASS walk-cycle pose stream pick

Design notes:
  - Brussels parquet (`data/basestations/merged/brussels.parquet`) tops out
    at Band3600MHz — no 26 GHz sites. The panel is hand-placed in plaza
    coordinates (origin at BS phase center, x=east, y=north, z=up).
  - Walk trajectories are bounded random walks at ~1 m/s; bodies bounce
    off a virtual ``[-r_max, r_max]`` x ``[5, r_max]`` plaza box so they
    stay in the BS forward sector.
  - AMASS root translation is ignored — only the joint angles are used,
    looped frame-by-frame. Real plaza root translations come from the
    bounded random walk here.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aegis.constants import C_0
from aegis.geometry.parametric import ParametricBody
from aegis.geometry.pose_stream import PoseStream
from aegis.mimo.array import AntennaArray

# Scene constants — paper §VII.A.
FREQ_HZ = 26.0e9
TX_POWER_DBM = 30.0
TX_POWER_W = 10 ** ((TX_POWER_DBM - 30.0) / 10.0)
N_PER_SIDE = 8

# BS placement in local plaza frame (origin = plaza center, +y = north into plaza).
BS_X_M = 0.0
BS_Y_M = -40.0  # south facade
BS_Z_M = 12.0
BS_DOWNTILT_DEG = 5.0
# Broadside points north (into plaza) with slight downtilt.
BS_BROADSIDE = np.array(
    [
        0.0,
        np.cos(np.deg2rad(BS_DOWNTILT_DEG)),
        -np.sin(np.deg2rad(BS_DOWNTILT_DEG)),
    ]
)
BS_POSITION = np.array([BS_X_M, BS_Y_M, BS_Z_M], dtype=np.float64)

# Body spawn / walk box (in BS-forward sector).
RANGE_MIN_M = 5.0
RANGE_MAX_M = 55.0  # paper says 5-60; clamp to 55 to keep bodies inside plaza
WALK_SPEED_M_PER_S = 1.0
WALK_HEADING_NOISE_RAD_PER_S = 0.5
PLAZA_HALF_WIDTH_M = 35.0  # east-west extent

# Tier assignment counts (paper §VII.A).
TIER_COUNTS = {"A": 25, "B": 15, "C": 10}


@dataclass(frozen=True)
class BSPanel:
    array: AntennaArray
    position: np.ndarray
    broadside: np.ndarray
    freq_hz: float
    tx_power_w: float


@dataclass(frozen=True)
class Body:
    index: int
    tier: str  # "A", "B", "C"
    pose_path: Path  # AMASS .npz used for joint angles
    spawn_xy: np.ndarray  # (2,) initial position in plaza frame
    initial_heading_rad: float


def build_bs_panel(freq_hz: float = FREQ_HZ, tx_power_dbm: float = TX_POWER_DBM) -> BSPanel:
    lam = C_0 / freq_hz
    array = AntennaArray.upa(
        n_h=N_PER_SIDE,
        n_v=N_PER_SIDE,
        d_h=lam / 2.0,
        d_v=lam / 2.0,
        center=BS_POSITION,
        broadside=BS_BROADSIDE,
        element_pattern="patch",
    )
    return BSPanel(
        array=array,
        position=BS_POSITION,
        broadside=BS_BROADSIDE,
        freq_hz=freq_hz,
        tx_power_w=10 ** ((tx_power_dbm - 30.0) / 10.0),
    )


def discover_walks(
    pose_root: Path = Path("data/poses/plaza_run_walks"),
) -> list[Path]:
    """Find every PoseStream-format walk sequence in the ingested corpus.

    The corpus is produced by ``scripts/ingest_amass.py`` from the raw AMASS
    archive at ``data/poses/amass_smplx_g/BMLrub/``. PoseStream.load expects
    the converted format (poses, trans, betas, gender, fps, source); the raw
    AMASS files have ``mocap_frame_rate`` instead of ``fps``.
    """
    if not pose_root.exists():
        raise FileNotFoundError(
            f"Walk corpus not found at {pose_root}. Run:\n"
            "  python scripts/ingest_amass.py --input data/poses/amass_smplx_g/BMLrub "
            "--output data/poses/plaza_run_walks --filter walk --max-sequences 60"
        )
    walks = sorted(pose_root.rglob("*.npz"))
    if len(walks) < 50:
        raise RuntimeError(f"Only {len(walks)} walk sequences in {pose_root}; need >= 50")
    return walks


def assign_bodies(
    n_bodies: int,
    rng: random.Random,
    pose_paths: list[Path],
) -> list[Body]:
    """Deterministic body assembly: tiers 25/15/10, AMASS pick, spawn, heading."""
    if n_bodies != sum(TIER_COUNTS.values()):
        raise ValueError(f"n_bodies={n_bodies} doesn't match tier counts {TIER_COUNTS}")
    tiers: list[str] = []
    for t, count in TIER_COUNTS.items():
        tiers.extend([t] * count)
    rng.shuffle(tiers)

    available = list(pose_paths)
    rng.shuffle(available)
    picks = available[:n_bodies]

    out: list[Body] = []
    for i, (tier, pose_path) in enumerate(zip(tiers, picks, strict=True)):
        # Sample spawn in BS-forward sector with annulus range constraint.
        for _ in range(50):
            x = rng.uniform(-PLAZA_HALF_WIDTH_M, PLAZA_HALF_WIDTH_M)
            # forward-y from BS: BS at (0, -40), so plaza ranges from y=-35 to y=+35
            y_local = rng.uniform(-30.0, 30.0)
            r_from_bs = float(np.linalg.norm([x - BS_X_M, y_local - BS_Y_M]))
            if RANGE_MIN_M <= r_from_bs <= RANGE_MAX_M:
                spawn = np.array([x, y_local], dtype=np.float64)
                break
        else:
            # Fallback: place on the broadside ray at mid-range.
            r = (RANGE_MIN_M + RANGE_MAX_M) / 2.0
            spawn = np.array([0.0, BS_Y_M + r], dtype=np.float64)
        heading = rng.uniform(-np.pi, np.pi)
        out.append(
            Body(
                index=i,
                tier=tier,
                pose_path=pose_path,
                spawn_xy=spawn,
                initial_heading_rad=heading,
            )
        )
    return out


def generate_walk_trajectory(
    body: Body,
    n_slots: int,
    dt_s: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Bounded random walk in the plaza for ``n_slots`` frames.

    Returns ``(n_slots, 3)`` positions (z=0). Heading drifts via a low-rate
    OU-style process; the body bounces off the plaza box.
    """
    pos = np.zeros((n_slots, 3), dtype=np.float64)
    xy = body.spawn_xy.copy()
    heading = body.initial_heading_rad
    for t in range(n_slots):
        # Heading random walk.
        heading += rng.normal() * WALK_HEADING_NOISE_RAD_PER_S * np.sqrt(dt_s)
        step = WALK_SPEED_M_PER_S * dt_s
        nx = xy[0] + step * np.cos(heading)
        ny = xy[1] + step * np.sin(heading)
        # Bounce off plaza box and BS-forward range constraint.
        if abs(nx) > PLAZA_HALF_WIDTH_M:
            heading = np.pi - heading
            nx = np.clip(nx, -PLAZA_HALF_WIDTH_M, PLAZA_HALF_WIDTH_M)
        r_from_bs = float(np.hypot(nx - BS_X_M, ny - BS_Y_M))
        if r_from_bs < RANGE_MIN_M or r_from_bs > RANGE_MAX_M or ny < -30.0 or ny > 30.0:
            # Reverse and damp.
            heading += np.pi
            nx, ny = xy[0], xy[1]
        xy = np.array([nx, ny])
        pos[t] = [xy[0], xy[1], 0.0]
    return pos


# Brussels Grand Place entry / exit nodes in plaza-local frame (origin = plaza
# centre, +y north, +x east). Approximate; calibrated against the OSM mesh.
ENTRY_NODES_M: dict[str, tuple[float, float]] = {
    "N_rue_au_beurre": (-12.0, 32.0),
    "NE_rue_colline": (28.0, 30.0),
    "E_rue_chapeliers": (33.0, -8.0),
    "SE_rue_charles_buls": (24.0, -27.0),
    "S_rue_etuve": (-6.0, -30.0),
    "SW_rue_violette": (-25.0, -25.0),
    "W_rue_chair_pain": (-32.0, 6.0),
}


def _flux_pair(rng: random.Random) -> tuple[str, str]:
    """Pick a distinct (entry, exit) node pair uniformly."""
    keys = list(ENTRY_NODES_M.keys())
    a = rng.choice(keys)
    b = rng.choice([k for k in keys if k != a])
    return a, b


def generate_flux_trajectory(
    body: Body,
    n_slots: int,
    dt_s: float,
    rng: np.random.Generator,
    py_rng: random.Random,
) -> np.ndarray:
    """Origin-destination flux walk: enter via one street node, traverse the
    plaza toward a random interior dwell point, then exit via a different
    street node. When the body reaches the exit it re-enters via a new
    (entry, exit) pair so the trace fills the full ``n_slots``.

    Heading at each step is the bearing toward the current waypoint plus
    Gaussian heading noise (matching the bounded-random-walk style).
    """
    pos = np.zeros((n_slots, 3), dtype=np.float64)

    waypoints: list[np.ndarray] = []

    def _refill_waypoints():
        a, b = _flux_pair(py_rng)
        # Spawn from entry; dwell at a random interior point near plaza centre;
        # exit via b.
        entry = np.array(ENTRY_NODES_M[a])
        exit_ = np.array(ENTRY_NODES_M[b])
        # Two dwell points biased toward plaza centre, randomised.
        dwells = []
        for _ in range(2):
            dx = py_rng.uniform(-15.0, 15.0)
            dy = py_rng.uniform(-15.0, 15.0)
            dwells.append(np.array([dx, dy]))
        waypoints.extend([entry, dwells[0], dwells[1], exit_])

    # Body enters at its first entry node (override spawn).
    _refill_waypoints()
    xy = waypoints.pop(0).copy()

    step = WALK_SPEED_M_PER_S * dt_s
    arrive_eps = 1.5  # waypoint reached when within 1.5 m

    for t in range(n_slots):
        if not waypoints:
            _refill_waypoints()
        target = waypoints[0]
        d = target - xy
        dist = float(np.linalg.norm(d))
        if dist < arrive_eps:
            waypoints.pop(0)
            pos[t] = [xy[0], xy[1], 0.0]
            continue
        bearing = float(np.arctan2(d[1], d[0]))
        # Heading noise around the bearing.
        bearing += rng.normal() * WALK_HEADING_NOISE_RAD_PER_S * np.sqrt(dt_s)
        nx = xy[0] + step * np.cos(bearing)
        ny = xy[1] + step * np.sin(bearing)
        # Soft constraint: stay clear of the BS pole.
        r_from_bs = float(np.hypot(nx - BS_X_M, ny - BS_Y_M))
        if r_from_bs < RANGE_MIN_M:
            # nudge tangentially
            nx, ny = xy[0], xy[1]
            waypoints.pop(0)  # abandon this dwell
        xy = np.array([nx, ny])
        pos[t] = [xy[0], xy[1], 0.0]
    return pos


def load_pose_streams(bodies: list[Body]) -> list[PoseStream]:
    return [PoseStream.load(b.pose_path) for b in bodies]


def smplx_body() -> ParametricBody:
    """Load the canonical neutral SMPL-X body once. ~5 s; cache by caller."""
    return ParametricBody.load("smplx", gender="neutral")


def served_user_indices(bodies: list[Body]) -> np.ndarray:
    """Indices of tier-A served users into the 50-body array."""
    return np.array([b.index for b in bodies if b.tier == "A"], dtype=np.int64)


def cooperating_indices(bodies: list[Body]) -> np.ndarray:
    return np.array([b.index for b in bodies if b.tier == "B"], dtype=np.int64)


def bystander_indices(bodies: list[Body]) -> np.ndarray:
    return np.array([b.index for b in bodies if b.tier == "C"], dtype=np.int64)
