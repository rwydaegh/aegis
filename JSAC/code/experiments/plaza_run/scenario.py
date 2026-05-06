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


def build_bs_panel(
    freq_hz: float = FREQ_HZ,
    tx_power_dbm: float = TX_POWER_DBM,
    n_per_side: int = N_PER_SIDE,
) -> BSPanel:
    lam = C_0 / freq_hz
    array = AntennaArray.upa(
        n_h=n_per_side,
        n_v=n_per_side,
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
    "NE_rue_colline": (12.0, 22.0),
    "E_rue_chapeliers": (33.0, -8.0),
    "SE_rue_charles_buls": (24.0, -27.0),
    "S_rue_etuve": (-6.0, -30.0),
    "SW_rue_violette": (-15.0, -15.0),
    "W_rue_chair_pain": (-32.0, 6.0),
}


def _flux_pair(rng: random.Random) -> tuple[str, str]:
    """Pick a distinct (entry, exit) node pair uniformly."""
    keys = list(ENTRY_NODES_M.keys())
    a = rng.choice(keys)
    b = rng.choice([k for k in keys if k != a])
    return a, b


PLAZA_OFFSCREEN_DIST_M = 200.0  # park far past the camera frustum
REST_SLOTS_RANGE = (60, 300)  # 2 .. 10 s parked off-screen between visits
DWELL_HALF_M = 14.0  # interior dwell points sampled from [-DWELL,+DWELL]^2
ENTRY_APPROACH_M = 35.0  # distance walked along the street outside the plaza
HEADING_NOISE_RAD_PER_S = 0.35


def _interior_dwell(py_rng: random.Random, anchor: np.ndarray) -> np.ndarray:
    """Sample an interior dwell biased toward the line BS→anchor.

    Pure uniform sampling tends to clip outside the plaza polygon; bias
    toward the segment between BS and the body's anchor (entry / exit) so
    dwell points land in the open courtyard.
    """
    bs_xy = np.array([BS_X_M, BS_Y_M])
    mid = 0.5 * (bs_xy + anchor)
    jx = py_rng.uniform(-DWELL_HALF_M, DWELL_HALF_M)
    jy = py_rng.uniform(-DWELL_HALF_M, DWELL_HALF_M)
    p = mid + np.array([jx, jy])
    p[0] = float(np.clip(p[0], -PLAZA_HALF_WIDTH_M + 4, PLAZA_HALF_WIDTH_M - 4))
    p[1] = float(np.clip(p[1], -25.0, 25.0))
    return p


def generate_flux_trajectory(
    body: Body,
    n_slots: int,
    dt_s: float,
    rng: np.random.Generator,
    py_rng: random.Random,
) -> np.ndarray:
    """Steady-state OD walks with continuous re-entry.

    Each body cycles through:

      1. Park off-screen (PLAZA_OFFSCREEN_DIST_M, unique per-body angle so
         bodies don't stack at one point) for `rest` slots.
      2. Walk entry → 1-2 interior dwells → exit, picking a fresh random
         (entry, exit) pair from ``ENTRY_NODES_M``.
      3. Repeat. The schedule extends from a per-body random phase
         offset (in roughly [-n_slots, +n_slots/4]) past the end of the
         run, so at t=0 some bodies are already mid-walk (steady state).

    Speed: WALK_SPEED_M_PER_S along path-arc; small heading noise via
    np.random within each segment. Output ``(n_slots, 3)`` positions.
    """
    pos = np.zeros((n_slots, 3), dtype=np.float64)
    walk_step_m = WALK_SPEED_M_PER_S * dt_s

    # Unique parking angle per body so they fan out around the plaza when
    # off-screen instead of stacking at one cardinal point.
    park_angle = py_rng.uniform(-np.pi, np.pi)
    park_xy = np.array(
        [
            PLAZA_OFFSCREEN_DIST_M * np.cos(park_angle),
            PLAZA_OFFSCREEN_DIST_M * np.sin(park_angle),
        ]
    )

    # Random phase offset: when does this body's first event start, in
    # slots relative to t=0? Negative means the body is already mid-walk
    # / mid-park at t=0 (steady-state population).
    phase_offset = py_rng.randint(-n_slots, n_slots // 4)

    # Build the schedule from cursor=phase_offset until past n_slots.
    # Each event = ('park', slot_a, slot_b) or ('walk', slot_a, slot_b, path).
    schedule: list[tuple] = []
    cursor = phase_offset
    is_walking = py_rng.random() < 0.55  # ~55 % start mid-walk
    bs_xy = np.array([BS_X_M, BS_Y_M])
    while cursor < n_slots:
        if is_walking:
            a, b = _flux_pair(py_rng)
            entry = np.array(ENTRY_NODES_M[a])
            exit_ = np.array(ENTRY_NODES_M[b])
            # Pre-entry / post-exit: extend the path along the BS→node
            # outward direction so the body walks in/out of the plaza
            # through the street, fading off-screen smoothly instead of
            # teleporting at the entry/exit node.
            entry_out = entry - bs_xy
            entry_out = entry_out / max(float(np.linalg.norm(entry_out)), 1e-6)
            pre_entry = entry + entry_out * ENTRY_APPROACH_M
            exit_out = exit_ - bs_xy
            exit_out = exit_out / max(float(np.linalg.norm(exit_out)), 1e-6)
            post_exit = exit_ + exit_out * ENTRY_APPROACH_M
            n_dwells = py_rng.choice([1, 2])
            dwells = [_interior_dwell(py_rng, entry if k == 0 else exit_) for k in range(n_dwells)]
            path = [pre_entry, entry, *dwells, exit_, post_exit]
            seg_lengths = [float(np.linalg.norm(path[i + 1] - path[i])) for i in range(len(path) - 1)]
            total_dist_m = sum(seg_lengths)
            walk_slots = max(8, int(total_dist_m / walk_step_m))
            schedule.append(("walk", cursor, cursor + walk_slots, path, seg_lengths, total_dist_m))
            cursor += walk_slots
        else:
            rest = py_rng.randint(*REST_SLOTS_RANGE)
            schedule.append(("park", cursor, cursor + rest))
            cursor += rest
        is_walking = not is_walking

    # Rasterise the schedule into pos[t] for t in [0, n_slots).
    ev_idx = 0
    for t in range(n_slots):
        # Advance through schedule until the active event covers t.
        while ev_idx < len(schedule) and schedule[ev_idx][2] <= t:
            ev_idx += 1
        if ev_idx >= len(schedule):
            pos[t] = [park_xy[0], park_xy[1], 0.0]
            continue
        ev = schedule[ev_idx]
        if t < ev[1] or ev[0] == "park":
            pos[t] = [park_xy[0], park_xy[1], 0.0]
            continue
        # Walk event: linear-interp along path with arc-length parameter.
        _, slot_a, slot_b, path, seg_lengths, total = ev
        elapsed = t - slot_a
        duration = max(1, slot_b - slot_a)
        target_dist = (elapsed / duration) * total
        travelled = 0.0
        xy = np.array(path[0], dtype=np.float64).copy()
        for i, sl in enumerate(seg_lengths):
            if travelled + sl >= target_dist:
                frac = (target_dist - travelled) / sl if sl > 1e-9 else 0.0
                xy = path[i] + frac * (path[i + 1] - path[i])
                break
            travelled += sl
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
