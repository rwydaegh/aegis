"""An upper bound on the power a diffraction term could add, for this geometry.

The tracer of ``semantic_twin.transport.tracer`` is rectilinear. It has no
diffraction term, so every direction whose straight line to the sky is blocked
contributes nothing at zero bounces and can only be recovered by a reflected or
scattered path. This script bounds what a diffraction term would have added,
using the geometry that was actually traced rather than a generic argument.

Method, per standpoint:

1. Cast a dense direction grid, azimuth uniform and elevation logarithmic so the
   first few degrees above the horizon are resolved. Record hit or miss and the
   hit range. A miss is sky.
2. Recompute the zero bounce susceptibility ``sum over visible cells of
   Q(u) dOmega``. This has to reproduce ``chi_<model>_direct`` from the
   production run, and the agreement is printed as a check on everything else
   here.
3. For every blocked cell, take ``theta``, the great circle angle to the nearest
   visible cell, as the depth into the geometric shadow, and ``d``, a distance
   from the standpoint to the shadowing edge. Form the Fresnel-Kirchhoff
   parameter for a distant source and a receiver at range ``d`` behind a single
   absorbing half plane,

       v = theta * sqrt(2 d / lambda),

   and the knife edge loss ``J(v)`` of Recommendation ITU-R P.526, so that the
   diffracted power gain relative to free space is ``G = 10^(-J/10)``.
4. Report ``chi_diff = sum over blocked cells of Q(u) G(v) dOmega``, which is an
   upper bound on the zero bounce power a diffraction term could restore.

Two choices of ``d`` are reported. ``nominal`` uses the hit range of each
blocked ray. ``bound`` uses the smallest hit range anywhere in the blocked set,
which is the strict upper bound, because ``v`` grows as ``sqrt(d)`` and a
smaller ``v`` is a smaller loss.

Run with the AEGIS virtualenv, which carries Mitsuba:

    /home/user/aegis/.venv/bin/python bound_diffraction.py --site korenmarkt
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

import numpy as np
from scipy.spatial import cKDTree

from semantic_twin.illumination import MODELS
from semantic_twin.propagation.geometry import MitsubaGeometry

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIGHT_M_S = 299_792_458.0


@dataclass(frozen=True)
class DiffractionBoundConfig:
    site: str = "korenmarkt"
    locations: str | pathlib.Path | None = None
    mesh: str | pathlib.Path | None = None
    standpoints: int = 20
    azimuth: int = 720
    elevation: int = 600
    elevation_floor_deg: float = 0.05
    out: str | pathlib.Path | None = None


def knife_edge_loss_db(v: np.ndarray) -> np.ndarray:
    """Recommendation ITU-R P.526 single knife edge loss, in dB.

    ``J(v) = 6.9 + 20 log10( sqrt((v-0.1)^2 + 1) + v - 0.1 )``, stated there as
    valid for ``v > -0.78`` and taken as zero below it. Every cell fed to this
    function is geometrically shadowed, so ``v >= 0`` by construction.
    """
    shifted = v - 0.1
    loss = 6.9 + 20.0 * np.log10(np.sqrt(shifted**2 + 1.0) + shifted)
    return np.where(v > -0.78, loss, 0.0)


def direction_grid(n_azimuth: int, n_elevation: int, elevation_floor_deg: float):
    """Azimuth uniform, elevation logarithmic from the floor to the zenith.

    The illumination laws of section 4 put most of their measure in the first
    few degrees, so a grid uniform in elevation would spend its cells where
    there is no weight. Solid angle per cell is carried explicitly.
    """
    azimuth = (np.arange(n_azimuth) + 0.5) * (2.0 * np.pi / n_azimuth)
    edges = np.radians(np.logspace(np.log10(elevation_floor_deg), np.log10(90.0), n_elevation + 1))
    elevation = np.sqrt(edges[:-1] * edges[1:])
    # Exact solid angle of the band, times the azimuth share.
    band = (np.sin(edges[1:]) - np.sin(edges[:-1])) * (2.0 * np.pi / n_azimuth)
    az, el = np.meshgrid(azimuth, elevation, indexing="ij")
    unit = np.stack(
        [np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)],
        axis=-1,
    ).reshape(-1, 3)
    omega = np.broadcast_to(band[None, :], (n_azimuth, n_elevation)).reshape(-1).copy()
    return unit, omega, el.reshape(-1)


def bound_one(
    geometry,
    origin: np.ndarray,
    unit: np.ndarray,
    omega: np.ndarray,
    models: dict,
    wavelengths_m: dict[str, float],
    batch: int = 400_000,
) -> dict:
    origins = np.broadcast_to(origin, unit.shape)
    hit = np.zeros(unit.shape[0], dtype=bool)
    distance = np.zeros(unit.shape[0])
    for start in range(0, unit.shape[0], batch):
        stop = min(start + batch, unit.shape[0])
        h, t, _, _ = geometry.intersect(
            np.ascontiguousarray(origins[start:stop]), np.ascontiguousarray(unit[start:stop])
        )
        hit[start:stop] = h
        distance[start:stop] = np.where(h, t, np.inf)

    sky = ~hit
    out: dict = {"sky_cells": int(sky.sum()), "cells": int(sky.size)}
    if not sky.any():
        return out

    sky_unit = unit[sky]
    blocked_unit = unit[~sky]
    blocked_range = distance[~sky]

    tree_sky = cKDTree(sky_unit)
    chord, nearest_sky = tree_sky.query(blocked_unit, k=1)
    theta = 2.0 * np.arcsin(np.clip(chord / 2.0, 0.0, 1.0))

    # Range to the diffracting edge. The edge is where sky meets geometry, so
    # the hit range of the blocked cell closest to a given sky cell is the range
    # to the edge that shadows everything behind it. Each blocked cell inherits
    # the edge range of the sky cell it is nearest to.
    tree_blocked = cKDTree(blocked_unit)
    _, nearest_blocked = tree_blocked.query(sky_unit, k=1)
    edge_of_sky_cell = blocked_range[nearest_blocked]
    edge_range = edge_of_sky_cell[nearest_sky]

    edge_floor = float(np.min(blocked_range))
    out["min_hit_range_m"] = edge_floor
    out["median_edge_range_m"] = float(np.median(edge_range))
    out["median_shadow_depth_deg"] = float(np.degrees(np.median(theta)))

    variants = {
        "edge": edge_range,  # range to the sky boundary the cell hides behind
        "hit": blocked_range,  # range to whatever the ray itself struck
        "floor": edge_floor,  # the nearest surface anywhere, the strict bound
    }

    # P.526 states the angle form of nu for theta below about 0.2 rad. Cells
    # deeper than that are kept, because dropping them would understate the
    # bound, but their share is reported so the reader can see how much of the
    # answer sits outside the recommendation's stated validity.
    shallow = theta <= np.radians(12.0)

    for name, model in models.items():
        norm = model.normalisation()
        density = model.density(unit, norm)
        out[f"{name}_direct"] = float(np.sum(density[sky] * omega[sky]))
        out[f"{name}_blocked_measure"] = float(np.sum(density[~sky] * omega[~sky]))
        w = density[~sky] * omega[~sky]
        for band, lam in wavelengths_m.items():
            for label, dist in variants.items():
                gain = 10.0 ** (-knife_edge_loss_db(theta * np.sqrt(2.0 * dist / lam)) / 10.0)
                out[f"{name}_diff_{label}_{band}"] = float(np.sum(w * gain))
                if label == "edge":
                    out[f"{name}_diff_edge_shallow_{band}"] = float(np.sum((w * gain)[shallow]))
    return out


def run(config: DiffractionBoundConfig | None = None) -> pathlib.Path:
    settings = config or DiffractionBoundConfig()
    loc = pathlib.Path(
        settings.locations
        or ROOT / "outputs" / "exposure_korenmarkt" / f"city250_corrected_{settings.site}_15ghz_locations.jsonl"
    )
    records = []
    for line in loc.read_text().splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    records.sort(key=lambda r: r["sky_fraction"])
    if settings.standpoints > 0:
        records = records[: settings.standpoints]

    manifest = json.loads(loc.with_name(loc.name.replace("_locations.jsonl", "_manifest.json")).read_text())
    mesh_path = pathlib.Path(settings.mesh or manifest["mesh"])
    frequency = float(manifest["trace_config"]["frequency_hz"])
    wavelengths = {"15ghz": LIGHT_M_S / frequency, "2ghz": LIGHT_M_S / 2.0e9}

    geometry = MitsubaGeometry(mesh_path)
    unit, omega, _ = direction_grid(settings.azimuth, settings.elevation, settings.elevation_floor_deg)
    models = {name: MODELS[name] for name in ("isotropic", "rooftop", "street_small_cell")}

    rows = []
    for record in records:
        origin = np.array([record["x"], record["y"], record["z"]], dtype=np.float64)
        row = bound_one(geometry, origin, unit, omega, models, wavelengths)
        row["index"] = record["index"]
        row["sky_fraction"] = record["sky_fraction"]
        for name in models:
            row[f"{name}_direct_traced"] = record[f"chi_{name}_direct"]
            row[f"{name}_total_traced"] = record[f"chi_{name}"]
        rows.append(row)
        print(
            f"idx {record['index']:4d} sky {record['sky_fraction']:.4f} "
            f"rooftop direct {row['rooftop_direct']:.5f} vs traced {record['chi_rooftop_direct']:.5f} "
            f"diff_edge15 {row['rooftop_diff_edge_15ghz']:.6f}",
            flush=True,
        )

    output_path = pathlib.Path(
        settings.out or ROOT / "outputs" / "diffraction_bound" / f"{settings.site}_diffraction_bound.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "site": settings.site,
                "mesh": str(mesh_path),
                "frequency_hz": frequency,
                "grid": {
                    "azimuth": settings.azimuth,
                    "elevation": settings.elevation,
                    "elevation_floor_deg": settings.elevation_floor_deg,
                },
                "standpoints": rows,
            },
            indent=2,
        )
    )
    print(f"wrote {output_path}")
    return output_path
