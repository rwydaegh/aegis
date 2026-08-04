"""The skyline of each square, and the direct illumination it implies.

Sites sit on facade tips, one per azimuth, so the direct flux at a standpoint is
a sum over azimuth and not an integral over a range band:

    chi_dir  proportional to  sum over phi of  cos^2(alpha) / d

with ``alpha`` the elevation of the highest surface in that azimuth and ``d``
its horizontal distance. Both come off the mesh. There is no height band and no
range band, because each azimuth carries exactly one source distance rather than
a distribution over one.

The derivation, in one line. Sites at linear density along the facade tip, an
azimuth slice ``dphi`` covers arc ``d dphi`` of that tip, each site is at slant
range ``d / cos(alpha)``, and flux falls as the inverse square of slant range.

This script measures the two fields the formula reads, per azimuth per
standpoint, at every site, and reports what they do to the direct term. It
traces nothing and consumes no illumination model.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np

from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.ground import measure_ground_datum, sky_visibility

ROOT = pathlib.Path(__file__).resolve().parent

#: Elevations searched for the silhouette, in degrees. The upper end is short of
#: the zenith on purpose: a standpoint under an arcade hits geometry straight up
#: and that is a ceiling rather than a skyline, and the sky test below drops it.
ELEVATION_MIN_DEG = 0.05
ELEVATION_MAX_DEG = 85.0


def skyline(
    geometry,
    origin: np.ndarray,
    *,
    azimuths: int,
    elevations: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Elevation and horizontal distance of the highest surface, per azimuth.

    Returns ``(alpha_rad, distance_m, found)``. A ray fan goes up each azimuth
    and the silhouette is the largest elevation that still hits something. Where
    nothing is hit at any elevation the azimuth is open to the horizon and
    ``found`` is False, which the caller has to decide about rather than have
    decided for it here.
    """
    azimuth = (np.arange(azimuths) + 0.5) * (2.0 * np.pi / azimuths)
    # Logarithmic in elevation. A facade tip 250 m away at 20 m height sits at
    # 4.6 degrees, so a grid uniform in elevation spends its cells above every
    # skyline this study contains.
    elevation = np.radians(np.logspace(np.log10(ELEVATION_MIN_DEG), np.log10(ELEVATION_MAX_DEG), elevations))
    az, el = np.meshgrid(azimuth, elevation, indexing="ij")
    unit = np.stack([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)], axis=-1)
    flat = unit.reshape(-1, 3)

    hit, distance, _, _ = geometry.intersect(np.broadcast_to(origin, flat.shape), flat)
    hit = hit.reshape(azimuths, elevations)
    distance = distance.reshape(azimuths, elevations)

    # The silhouette is the last elevation that hits, scanning upward. Reverse,
    # take the first hit, and convert the index back.
    reversed_hit = hit[:, ::-1]
    found = reversed_hit.any(axis=1)
    first = np.argmax(reversed_hit, axis=1)
    index = elevations - 1 - first

    rows = np.arange(azimuths)
    alpha = elevation[index]
    slant = distance[rows, index]
    horizontal = slant * np.cos(alpha)
    return alpha, horizontal, found


def direct_term(alpha: np.ndarray, horizontal: np.ndarray, found: np.ndarray) -> dict:
    """The direct sum, and the pieces of it worth reading separately.

    An azimuth with no facade tip contributes nothing here. That is a floor, not
    a neutral choice: a real horizon carries sites too. It is reported as a count
    so the reader can see how much of a square is answered this way.
    """
    weight = np.zeros_like(alpha)
    good = found & np.isfinite(horizontal) & (horizontal > 0.0)
    weight[good] = np.cos(alpha[good]) ** 2 / horizontal[good]
    total = float(weight.mean())  # mean over azimuth is the integral over 2 pi, up to the constant
    return {
        "direct_term": total,
        "open_azimuth_fraction": float(1.0 - good.mean()),
        "alpha_deg_median": float(np.degrees(np.median(alpha[good]))) if good.any() else float("nan"),
        "distance_m_median": float(np.median(horizontal[good])) if good.any() else float("nan"),
        "distance_m_p05": float(np.percentile(horizontal[good], 5)) if good.any() else float("nan"),
        "distance_m_p95": float(np.percentile(horizontal[good], 95)) if good.any() else float("nan"),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sites", nargs="*", default=None)
    ap.add_argument("--crop-m", type=int, default=250)
    ap.add_argument("--standpoints", type=int, default=24)
    ap.add_argument("--azimuths", type=int, default=720)
    ap.add_argument("--elevations", type=int, default=400)
    ap.add_argument("--walk-radius-m", type=float, default=90.0)
    ap.add_argument("--head-height-m", type=float, default=1.5)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--variant", default="llvm_ad_rgb")
    ap.add_argument("--tag", default="skyline")
    args = ap.parse_args()

    geometry_root = ROOT / "data" / "geometry"
    sites = args.sites or sorted(p.name for p in geometry_root.iterdir() if p.is_dir())

    out_dir = ROOT / "outputs" / "skyline"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for site in sites:
        mesh = geometry_root / site / f"inhouse_leaf_{args.crop_m}m_f64.ply"
        if not mesh.exists():
            mesh = geometry_root / site / f"inhouse_leaf_{args.crop_m}m.ply"
        if not mesh.exists():
            print(f"{site:24s} no {args.crop_m} m mesh, skipped")
            continue

        started = time.perf_counter()
        geometry = MitsubaGeometry(mesh, variant=args.variant)
        datum = measure_ground_datum(geometry, radius_m=args.walk_radius_m)
        walk = build_walk(
            geometry,
            ground_datum_m=datum.z_m,
            radius_m=args.walk_radius_m,
            head_height_m=args.head_height_m,
            seed=args.seed,
        )
        points = np.asarray(walk.points)
        if points.shape[0] > args.standpoints:
            index = np.linspace(0, points.shape[0] - 1, args.standpoints).round().astype(int)
            points = points[index]

        # The silhouette is checked against a quantity measured a different way.
        # Averaging (1 - sin alpha)/2 over azimuth is the sky solid angle the
        # skyline implies, and `sky_visibility` gets the same number by random
        # casting. They agree to 0.02 at Korenmarkt, which is what says the fan
        # is finding the silhouette rather than something below it.
        rng = np.random.default_rng(args.seed)
        sky_measured = sky_visibility(geometry, points, 4096, rng)

        per_standpoint = []
        alpha_all = []
        distance_all = []
        sky_implied = []
        for point in points:
            alpha, horizontal, found = skyline(geometry, point, azimuths=args.azimuths, elevations=args.elevations)
            per_standpoint.append(direct_term(alpha, horizontal, found))
            good = found & np.isfinite(horizontal) & (horizontal > 0.0)
            alpha_all.append(np.degrees(alpha[good]))
            distance_all.append(horizontal[good])
            sky_implied.append(float(np.mean((1.0 - np.sin(alpha)) / 2.0)))
        sky_error = np.abs(np.array(sky_implied) - sky_measured)

        terms = np.array([r["direct_term"] for r in per_standpoint])
        alpha_all = np.concatenate(alpha_all) if alpha_all else np.array([])
        distance_all = np.concatenate(distance_all) if distance_all else np.array([])
        row = {
            "site": site,
            "crop_radius_m": args.crop_m,
            "mesh": str(mesh.relative_to(ROOT)),
            "standpoints": int(points.shape[0]),
            "azimuths": args.azimuths,
            "elevations": args.elevations,
            "ground_datum_m": datum.z_m,
            "direct_term_median": float(np.median(terms)),
            "direct_term_p05": float(np.percentile(terms, 5)),
            "direct_term_p95": float(np.percentile(terms, 95)),
            "direct_term_spread_db": float(10.0 * np.log10(np.percentile(terms, 95) / np.percentile(terms, 5))),
            "alpha_deg_median": float(np.median(alpha_all)) if alpha_all.size else float("nan"),
            "alpha_deg_p95": float(np.percentile(alpha_all, 95)) if alpha_all.size else float("nan"),
            "distance_m_median": float(np.median(distance_all)) if distance_all.size else float("nan"),
            "distance_m_p95": float(np.percentile(distance_all, 95)) if distance_all.size else float("nan"),
            "open_azimuth_fraction_median": float(np.median([r["open_azimuth_fraction"] for r in per_standpoint])),
            "sky_check": {
                "implied_median": float(np.median(sky_implied)),
                "measured_median": float(np.median(sky_measured)),
                "abs_error_max": float(sky_error.max()),
            },
            "seconds": time.perf_counter() - started,
            "per_standpoint": per_standpoint,
        }
        rows.append(row)
        print(
            f"{site:24s} term {row['direct_term_median']:.5f} "
            f"spread {row['direct_term_spread_db']:+.2f} dB  "
            f"alpha {row['alpha_deg_median']:5.1f} deg  "
            f"d {row['distance_m_median']:6.1f} m  "
            f"open {row['open_azimuth_fraction_median']:.3f}  "
            f"skyerr {row['sky_check']['abs_error_max']:.3f}  "
            f"({row['seconds']:.0f} s)"
        )

    payload = {
        "question": "what the skyline is at each square, and what the mast free facade tip law makes of it",
        "law": "direct term proportional to mean over azimuth of cos^2(alpha) / d",
        "note": "no height band and no range band. Each azimuth carries one source distance.",
        "rows": rows,
    }
    path = out_dir / f"{args.tag}_{args.crop_m}m.json"
    path.write_text(json.dumps(payload, indent=1))
    print(f"\nwrote {path.relative_to(ROOT)}")

    if len(rows) > 1:
        terms = np.array([r["direct_term_median"] for r in rows])
        print(
            f"between site spread {10.0 * np.log10(terms.max() / terms.min()):.2f} dB, "
            f"median within site spread {np.median([r['direct_term_spread_db'] for r in rows]):.2f} dB"
        )


if __name__ == "__main__":
    main()
