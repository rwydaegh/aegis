"""Big near-field phone exposure sweep.

For each phantom, frequency band, placement, source-to-body distance and device
orientation, computes the full set of ICNIRP 2020 metrics (whole-body SAR,
psSAR10g, peak/4 cm^2/1 cm^2 APD) at 1 W radiated power. The orientation
ensemble is a set of uniformly random device rotations, giving the variability
envelope used for the uncertainty estimates; the boresight-at-body "nominal"
pose is included and flagged.

Everything is normalised per watt of radiated power: SAR is W/kg per W_rad
and APD is W/m^2 per W_rad. These are not the GOLIAT near-field deliverable
values. GOLIAT uses CNR's band-specific input powers calibrated on a flat
phantom. An explicit input-to-radiated conversion or empirical calibration
must precede that comparison.

Output: ``out/sweep_<tag>.parquet`` (long form, one row per configuration).

Usage::

    python -m studies.nearfield_phone.run_sweep --phantoms duke --full
    python -m studies.nearfield_phone.run_sweep            # all phantoms, default grid
"""

from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from aegis.nearfield.metrics import MetricsEvaluator
from aegis.nearfield.phone import compute_sab_batch
from aegis.nearfield.scenarios import _rotation_aligning_z_to, standard_placements
from studies.nearfield_phone import config as C

METRIC_KEYS = [
    "sar_wb",
    "pssar_10g",
    "peak_apd",
    "apd_4cm2",
    "apd_1cm2",
    "peak_surface_sar",
    "p_abs_w",
]


def sweep_phantom(
    name: str,
    distances_m: np.ndarray,
    n_orient: int,
    seed: int,
    bands: dict,
    mass_kg: float,
) -> pd.DataFrame:
    """Run the full grid for one phantom and return a long-form DataFrame."""
    mesh = C.load_mesh(name)
    centroids = np.asarray(mesh.centroids)
    normals = np.asarray(mesh.normals)
    evaluator = MetricsEvaluator(centroids, mesh.areas, C.RHO_SKIN)
    placements = standard_placements(mesh)

    # Orientation ensemble: the nominal boresight-at-body pose plus uniformly
    # random device rotations (Shoemake). The same random set is reused across
    # bands/placements/distances so configurations are comparable.
    rand_rots = C.random_rotations(n_orient, seed=seed)

    rows = []
    for mhz, bt in bands.items():
        for pname in C.PLACEMENTS:
            pl = placements[pname]
            base_rot = _rotation_aligning_z_to(pl.look_dir)
            # Full orientation set: index 0 is the nominal pose.
            rots = np.concatenate([base_rot[None], rand_rots @ base_rot], axis=0)
            n_rot = rots.shape[0]
            for d in distances_m:
                pos = pl.position(float(d))
                positions = np.broadcast_to(pos, (n_rot, 3))
                sab = np.asarray(
                    compute_sab_batch(
                        centroids,
                        normals,
                        positions,
                        rots,
                        bt.pattern,
                        bt.t0,
                        bt.n_tilde,
                        radiated_power_w=1.0,
                        fresnel=True,
                    )
                )
                m = evaluator.evaluate_batch(sab, bt.n_tilde, bt.freq_hz, mass_kg)
                for j in range(n_rot):
                    row = {
                        "phantom": name,
                        "freq_mhz": mhz,
                        "placement": pname,
                        "distance_mm": float(d) * 1e3,
                        "orient_id": j,
                        "is_nominal": j == 0,
                        "efficiency_reliable": mhz not in C.UNRELIABLE_EFFICIENCY_MHZ,
                    }
                    for k in METRIC_KEYS:
                        row[k] = float(m[k][j])
                    rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phantoms", nargs="*", default=["duke", "ella", "eartha", "thelonious"])
    ap.add_argument("--n-dist", type=int, default=24)
    ap.add_argument("--dmin-mm", type=float, default=5.0)
    ap.add_argument("--dmax-mm", type=float, default=400.0)
    ap.add_argument("--n-orient", type=int, default=64)
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--full", action="store_true", help="dense grid (n-dist=28, n-orient=96)")
    ap.add_argument("--tag", default="main")
    args = ap.parse_args()

    if args.full:
        args.n_dist, args.n_orient = 28, 96

    distances = np.geomspace(args.dmin_mm * 1e-3, args.dmax_mm * 1e-3, args.n_dist)
    patterns = C.load_patterns()
    bands = C.band_tissues(patterns)
    masses = C.phantom_masses()

    print(f"bands: {sorted(bands)}")
    print(f"distances (mm): {np.round(distances * 1e3, 1)}")
    print(f"orientations: {args.n_orient} random + 1 nominal")

    frames = []
    for name in args.phantoms:
        t0 = time.time()
        df = sweep_phantom(name, distances, args.n_orient, args.seed, bands, masses[name])
        frames.append(df)
        print(f"  {name}: {len(df):,} rows in {time.time() - t0:.1f}s")

    out = pd.concat(frames, ignore_index=True)
    path = C.OUT_DIR / f"sweep_{args.tag}.parquet"
    out.to_parquet(path)
    print(f"wrote {len(out):,} rows -> {path}")


if __name__ == "__main__":
    main()
