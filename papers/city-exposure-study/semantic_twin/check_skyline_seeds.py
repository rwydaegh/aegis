"""Repeat the skyline fit from several seeds and report the spread, not one number.

``semantic_twin.align_skyline`` fits a single deterministic seed with a fixed
``dz`` bound. Its printed residual is therefore a sample from a stochastic global
optimiser on a shallow objective, not an accuracy estimate. This driver reuses the
same observation, the same candidate geometry, and the same objective, and varies
only the seed and the vertical search bound.

Run from ``semantic_twin``::

    ../../../.venv/bin/python check_skyline_seeds.py \
      --mesh data/geometry/milan_duomo/inhouse_leaf_200m.ply \
      --semantics data/panoramas/milan_duomo/semantics/panorama_semantics.npz \
      --semantics-json data/panoramas/milan_duomo/semantics/semantics.json \
      --pose data/panoramas/milan_duomo/pose_initial.json \
      --out data/panoramas/milan_duomo/alignment/skyline_seed_study.json
"""

from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
from scipy.optimize import differential_evolution

from semantic_twin.align_skyline import (
    candidate_vertices,
    mesh_skyline,
    observed_skyline,
    read_binary_ply_vertices,
)
from semantic_twin.pano_geometry import panorama_to_world_matrix, streetview_orientation_prior

DEFAULT_SEEDS = (0xAE615, 1, 2, 3, 5, 8, 13, 21)


def fit(
    vertices: np.ndarray,
    local_skyline: np.ndarray,
    position: np.ndarray,
    heading_deg: float,
    pitch_prior_deg: float,
    roll_prior_deg: float,
    *,
    n_bins: int,
    maxiter: int,
    minimum_distance_m: float,
    dz_bounds: tuple[float, float],
    seed: int,
) -> tuple[np.ndarray, float]:
    """Identical objective to ``align_skyline.fit_pose`` with an exposed seed."""

    def objective(params: np.ndarray) -> float:
        dx, dy, dz, yaw, pitch_delta, roll_delta = params
        camera = position + np.array([dx, dy, dz])
        model = mesh_skyline(vertices, camera, n_bins, minimum_distance_m)
        rotation = panorama_to_world_matrix(
            heading_deg + yaw,
            pitch_deg=pitch_prior_deg + pitch_delta,
            roll_deg=roll_prior_deg + roll_delta,
        )
        world = local_skyline @ rotation.T
        azimuth = np.arctan2(world[:, 0], world[:, 1])
        elevation = np.arcsin(np.clip(world[:, 2], -1.0, 1.0))
        index = ((azimuth / (2.0 * np.pi) + 0.5) * n_bins) % n_bins
        lo = np.floor(index).astype(int)
        hi = (lo + 1) % n_bins
        frac = index - lo
        predicted = model[lo] * (1.0 - frac) + model[hi] * frac
        residual = np.abs(predicted - elevation)
        cutoff = np.quantile(residual, 0.8)
        robust_error = np.mean(np.minimum(residual, cutoff))
        orientation_prior = 0.001 * ((pitch_delta / 3.0) ** 2 + (roll_delta / 3.0) ** 2)
        return float(robust_error + orientation_prior)

    result = differential_evolution(
        objective,
        bounds=[(-4.0, 4.0), (-4.0, 4.0), dz_bounds, (-20.0, 20.0), (-6.0, 6.0), (-6.0, 6.0)],
        seed=seed,
        popsize=7,
        maxiter=maxiter,
        polish=True,
        updating="immediate",
    )
    return result.x, float(result.fun)


def summarise(runs: list[dict[str, float]], dz_bounds: tuple[float, float]) -> dict[str, object]:
    names = ("dx_m", "dy_m", "dz_m", "yaw_deg", "pitch_delta_deg", "roll_delta_deg")
    spread = {}
    for name in names:
        values = np.array([run[name] for run in runs])
        spread[name] = {
            "mean": float(values.mean()),
            "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
            "min": float(values.min()),
            "max": float(values.max()),
        }
    residuals = np.array([run["residual_deg"] for run in runs])
    dz = np.array([run["dz_m"] for run in runs])
    return {
        "dz_bounds_m": list(dz_bounds),
        "runs": runs,
        "spread": spread,
        "residual_deg": {
            "mean": float(residuals.mean()),
            "std": float(residuals.std(ddof=1)) if len(residuals) > 1 else 0.0,
            "min": float(residuals.min()),
            "max": float(residuals.max()),
        },
        "seeds_at_lower_dz_bound": int(np.sum(np.abs(dz - dz_bounds[0]) < 0.1)),
        "seeds_at_upper_dz_bound": int(np.sum(np.abs(dz - dz_bounds[1]) < 0.1)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--semantics", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--bins", type=int, default=1024)
    parser.add_argument("--maxiter", type=int, default=35)
    parser.add_argument("--minimum-skyline-distance", type=float, default=8.0)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    parser.add_argument(
        "--dz-bounds",
        type=float,
        nargs=2,
        action="append",
        help="Vertical search bound in metres, repeatable (default: the shipped -1.5 3.0 plus -12 12)",
    )
    args = parser.parse_args()

    entity = np.load(args.semantics)["entity"]
    id2label = {int(k): v for k, v in json.loads(args.semantics_json.read_text())["entity_id2label"].items()}
    sky_id = next(i for i, label in id2label.items() if label.casefold() == "sky")
    structural_ids = {
        class_id for class_id, label in id2label.items() if label.casefold() in {"building", "wall", "bridge", "tunnel"}
    }
    pose = json.loads(args.pose.read_text())
    position = np.asarray(pose["position_enu_m"], dtype=float)
    heading = float(pose["heading_deg"])
    pitch_prior, roll_prior = streetview_orientation_prior(
        float(pose.get("tilt_deg", 90.0)), float(pose.get("roll_deg", 0.0))
    )
    vertices = read_binary_ply_vertices(args.mesh)
    candidates = candidate_vertices(vertices, position, args.bins, args.minimum_skyline_distance)
    observed = observed_skyline(entity, sky_id, args.bins, structural_ids)

    bound_sets = [tuple(pair) for pair in (args.dz_bounds or [[-1.5, 3.0], [-12.0, 12.0]])]
    study = []
    for dz_bounds in bound_sets:
        runs = []
        for seed in args.seeds:
            params, score = fit(
                candidates,
                observed,
                position,
                heading,
                pitch_prior,
                roll_prior,
                n_bins=args.bins,
                maxiter=args.maxiter,
                minimum_distance_m=args.minimum_skyline_distance,
                dz_bounds=dz_bounds,
                seed=seed,
            )
            runs.append(
                {
                    "seed": seed,
                    "dx_m": float(params[0]),
                    "dy_m": float(params[1]),
                    "dz_m": float(params[2]),
                    "yaw_deg": float(params[3]),
                    "pitch_delta_deg": float(params[4]),
                    "roll_delta_deg": float(params[5]),
                    "residual_deg": float(np.degrees(score)),
                }
            )
            print(
                f"[seed {seed:>7}] dz={params[2]:+.3f} m yaw={params[3]:+.3f} deg residual={np.degrees(score):.3f} deg",
                flush=True,
            )
        study.append(summarise(runs, dz_bounds))
        print(f"[bounds {dz_bounds}] residual mean={study[-1]['residual_deg']['mean']:.3f} deg", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(
            {
                "mesh": str(args.mesh),
                "pose": str(args.pose),
                "n_candidate_vertices": int(len(candidates)),
                "n_observed_structural_skyline_samples": int(len(observed)),
                "seeds": list(args.seeds),
                "studies": study,
            },
            indent=2,
        )
    )
    print(f"[seeds] -> {args.out}")


if __name__ == "__main__":
    main()
