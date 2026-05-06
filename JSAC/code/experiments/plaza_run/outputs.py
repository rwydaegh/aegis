"""NPZ + run.json writer for plaza_run outputs.

Filename pattern lets brief 09 glob-discover by pose / phy / paths config:

    plaza_run_seed{N}_phy{shannon|sionna}_pose{aware|ablate}_paths{dict|uma}.npz

The sibling ``run.json`` carries scenario settings, decisions captured, and
the cadence breakdown that populates paper ``tab:cadence``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class RunMetadata:
    seed: int
    n_bodies: int
    n_slots: int
    dt_s: float
    freq_hz: float
    tx_power_dbm: float
    phy_mode: str
    pose_mode: str
    paths_mode: str
    scene_hash: str
    decim: int
    bs_position: tuple[float, float, float]
    bs_broadside: tuple[float, float, float]
    n_users_max: int
    cadence_ms: dict = field(default_factory=dict)
    notes: str = ""
    label_suffix: str = ""
    reference_level_vpm: float = 14.57
    n_per_side: int = 8
    config_name: str = ""


def npz_filename(meta: RunMetadata) -> str:
    suffix = getattr(meta, "label_suffix", "")
    suffix_part = f"_{suffix}" if suffix else ""
    return (
        f"plaza_run_seed{meta.seed:d}_phy{meta.phy_mode}_pose{meta.pose_mode}_paths{meta.paths_mode}{suffix_part}.npz"
    )


def write_run(
    out_dir: str | Path,
    meta: RunMetadata,
    *,
    p_abs: np.ndarray,
    sumrate: np.ndarray,
    violation: np.ndarray,
    infeasible: np.ndarray,
    tier: np.ndarray,
    body_positions: np.ndarray,
    cadence_ms: np.ndarray,
    precoder_names: list[str],
    body_budgets_w: np.ndarray,
) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    npz_path = out_dir / npz_filename(meta)
    np.savez_compressed(
        npz_path,
        p_abs=p_abs.astype(np.float32),
        sumrate=sumrate.astype(np.float32),
        violation=violation.astype(bool),
        infeasible=infeasible.astype(bool),
        tier=tier.astype(np.uint8),
        body_positions=body_positions.astype(np.float32),
        cadence_ms=cadence_ms.astype(np.float32),
        precoder_names=np.array(precoder_names),
        body_budgets_w=body_budgets_w.astype(np.float32),
        seed=np.int32(meta.seed),
        freq_hz=np.float64(meta.freq_hz),
        tx_power_dbm=np.float64(meta.tx_power_dbm),
        n_bodies=np.int32(meta.n_bodies),
        n_slots=np.int32(meta.n_slots),
        dt_s=np.float64(meta.dt_s),
        scene_hash=np.array(meta.scene_hash),
        phy_mode=np.array(meta.phy_mode),
        pose_mode=np.array(meta.pose_mode),
        paths_mode=np.array(meta.paths_mode),
    )

    json_path = out_dir / (npz_path.stem + ".json")
    payload = asdict(meta)
    payload["bs_position"] = list(payload["bs_position"])
    payload["bs_broadside"] = list(payload["bs_broadside"])
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True))
    return npz_path


def cadence_summary(cadence_ms: np.ndarray, stage_names: list[str]) -> dict:
    """Median + p10/p90 per stage, in ms. Feeds paper ``tab:cadence``."""
    if cadence_ms.size == 0:
        return {}
    out: dict[str, dict[str, float]] = {}
    for i, name in enumerate(stage_names):
        col = cadence_ms[:, i]
        out[name] = {
            "p10_ms": float(np.percentile(col, 10)),
            "p50_ms": float(np.percentile(col, 50)),
            "p90_ms": float(np.percentile(col, 90)),
            "mean_ms": float(np.mean(col)),
        }
    return out
