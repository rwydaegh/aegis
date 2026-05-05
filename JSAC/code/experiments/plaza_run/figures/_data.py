"""NPZ loader for plaza_run figures.

Exposes ``Run`` (a tidy view over one NPZ) and ``load_runs`` (returns the
three canonical runs the §VII figures consume).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"

CANONICAL_RUNS = {
    "specular_aware": "plaza_run_seed42_physhannon_poseaware_pathsdict.npz",
    "specular_ablate": "plaza_run_seed42_physhannon_poseablate_pathsdict.npz",
    "uma_aware": "plaza_run_seed42_physhannon_poseaware_pathsuma.npz",
}

PRECODER_DISPLAY = {
    "mrt": "MRT",
    "zf": "ZF",
    "wc_backoff": "WC back-off",
    "multibody_ecbf": "Multi-body ECBF",
    "oracle": "Oracle",
}

TIER_DISPLAY = {0: "Served (A)", 1: "Cooperating (B)", 2: "Bystander (C)"}


@dataclass
class Run:
    label: str
    p_abs: np.ndarray  # (T, B, P) W
    sumrate: np.ndarray  # (T, P) bps
    violation: np.ndarray  # (T, B, P) bool
    infeasible: np.ndarray  # (T, P) bool
    tier: np.ndarray  # (B,) uint8
    body_positions: np.ndarray  # (T, B, 3) m
    cadence_ms: np.ndarray  # (T, 4)
    body_budgets_w: np.ndarray  # (B,) W
    precoder_names: list[str]
    seed: int
    freq_hz: float
    tx_power_dbm: float
    n_bodies: int
    n_slots: int
    dt_s: float
    phy_mode: str
    pose_mode: str
    paths_mode: str

    @property
    def time_s(self) -> np.ndarray:
        return np.arange(self.n_slots) * self.dt_s

    def precoder_index(self, name: str) -> int:
        return self.precoder_names.index(name)


def load_run(npz_path: Path | str, label: str | None = None) -> Run:
    npz_path = Path(npz_path)
    with np.load(npz_path, allow_pickle=False) as f:
        return Run(
            label=label or npz_path.stem,
            p_abs=np.asarray(f["p_abs"]),
            sumrate=np.asarray(f["sumrate"]),
            violation=np.asarray(f["violation"]),
            infeasible=np.asarray(f["infeasible"]),
            tier=np.asarray(f["tier"]),
            body_positions=np.asarray(f["body_positions"]),
            cadence_ms=np.asarray(f["cadence_ms"]),
            body_budgets_w=np.asarray(f["body_budgets_w"]),
            precoder_names=[str(s) for s in f["precoder_names"].tolist()],
            seed=int(f["seed"]),
            freq_hz=float(f["freq_hz"]),
            tx_power_dbm=float(f["tx_power_dbm"]),
            n_bodies=int(f["n_bodies"]),
            n_slots=int(f["n_slots"]),
            dt_s=float(f["dt_s"]),
            phy_mode=str(f["phy_mode"]),
            pose_mode=str(f["pose_mode"]),
            paths_mode=str(f["paths_mode"]),
        )


def load_canonical(name: str) -> Run:
    return load_run(OUTPUTS_DIR / CANONICAL_RUNS[name], label=name)


def load_runs() -> dict[str, Run]:
    return {k: load_canonical(k) for k in CANONICAL_RUNS}
