"""Crop-radius convergence study for exposure susceptibility."""

from __future__ import annotations

import json
import pathlib
import re
import time
from dataclasses import dataclass, field

import numpy as np

from semantic_twin import paths
from semantic_twin.illumination import ISOTROPIC, ROOFTOP, STREET_SMALL_CELL
from semantic_twin.materials import classify_faces, load_table
from semantic_twin.propagation.geometry import MitsubaGeometry
from semantic_twin.transport.tracer import DEFAULT_MAX_BOUNCES, SbrTracer, TraceConfig
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.ground import ground_datum
from semantic_twin.walk.model import stratified_subset


@dataclass(frozen=True)
class CropConvergenceConfig:
    site: str = "korenmarkt"
    out: pathlib.Path | None = None
    locations: int = 24
    rays: int = 200_000
    max_bounces: int = DEFAULT_MAX_BOUNCES
    observer_radius_m: float = 40.0
    frequency_hz: float = 15.0e9
    seed: int = 11
    root: pathlib.Path = field(default_factory=paths.root)

    @property
    def output_dir(self) -> pathlib.Path:
        return self.out or self.root / "outputs" / "crop_convergence"


def radius_of(path: pathlib.Path) -> float:
    match = re.search(r"_(\d+)m", path.name)
    return float(match.group(1)) if match else float("nan")


def candidate_meshes(site: str, root: pathlib.Path | None = None) -> list[pathlib.Path]:
    directory = (root or paths.root()) / "data" / "geometry" / site
    best: dict[float, pathlib.Path] = {}
    for path in sorted(directory.glob("inhouse_leaf_*.ply")):
        radius = radius_of(path)
        if np.isnan(radius):
            continue
        if radius not in best or path.name.endswith("_f64.ply"):
            best[radius] = path
    return [best[radius] for radius in sorted(best)]


def run_crop_convergence(config: CropConvergenceConfig) -> pathlib.Path:
    meshes = candidate_meshes(config.site, config.root)
    if len(meshes) < 3:
        raise SystemExit(f"need at least three radii to see a trend, found {len(meshes)}")
    print(f"[sweep] {config.site}: radii {[radius_of(path) for path in meshes]}", flush=True)

    smallest = MitsubaGeometry(meshes[0])
    ground = ground_datum(smallest, radius_m=config.observer_radius_m)
    walk = build_walk(
        smallest,
        ground_datum_m=ground,
        radius_m=config.observer_radius_m,
        spacing_m=3.0,
        seed=config.seed,
    )
    picks = stratified_subset(walk, config.locations)
    points = walk.points[picks]
    datums = walk.ground_z_m[picks]
    print(
        f"[sweep] {len(walk)} candidates, {len(points)} observers inside {config.observer_radius_m:.0f} m",
        flush=True,
    )

    models = {"isotropic": ISOTROPIC, "rooftop": ROOFTOP, "street_small_cell": STREET_SMALL_CELL}
    binding = load_table(config.root / "config", config.frequency_hz)
    rows = []
    for path in meshes:
        started = time.perf_counter()
        geometry = MitsubaGeometry(path)
        face_class = classify_faces(geometry.vertices, geometry.faces, ground)
        trace_config = TraceConfig(
            frequency_hz=config.frequency_hz,
            rays=config.rays,
            max_bounces=config.max_bounces,
            seed=config.seed,
        )
        tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, trace_config)
        chi = {name: [] for name in models}
        sky = []
        for point, datum in zip(points, datums, strict=True):
            result = tracer.trace(point, models, ground_z_m=float(datum))
            for name in models:
                chi[name].append(result.susceptibility[name])
            sky.append(result.sky_fraction)
        row = {
            "mesh": path.name,
            "crop_radius_m": radius_of(path),
            "triangles": int(len(geometry.faces)),
            "observers": len(points),
            "sky_fraction_mean": float(np.mean(sky)),
            "seconds": time.perf_counter() - started,
        }
        for name in models:
            values = np.asarray(chi[name])
            row[f"chi_{name}_mean"] = float(values.mean())
            row[f"chi_{name}_median"] = float(np.median(values))
        rows.append(row)
        print(
            f"[sweep] r={row['crop_radius_m']:5.0f} m  sky {row['sky_fraction_mean']:.4f}  "
            f"chi_iso {row['chi_isotropic_mean']:.4f}  chi_roof {row['chi_rooftop_mean']:.4f}  "
            f"chi_street {row['chi_street_small_cell_mean']:.5f}  {row['seconds']:.0f} s",
            flush=True,
        )

    for previous, current in zip(rows, rows[1:], strict=False):
        for key in (
            "chi_isotropic_mean",
            "chi_rooftop_mean",
            "chi_street_small_cell_mean",
            "sky_fraction_mean",
        ):
            before, after = previous[key], current[key]
            current[f"delta_db_{key}"] = float(10.0 * np.log10(after / before)) if before > 0 else float("nan")

    config.output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "site": config.site,
        "observer_radius_m": config.observer_radius_m,
        "rays": config.rays,
        "max_bounces": config.max_bounces,
        "frequency_hz": config.frequency_hz,
        "note": (
            "Observers are held fixed inside the smallest crop so every radius is scored on the same "
            "standpoints and only the surrounding scene changes. Deltas are against the next smaller radius."
        ),
        "rows": rows,
    }
    path = config.output_dir / f"{config.site}_crop_convergence.json"
    path.write_text(json.dumps(payload, indent=1) + "\n")
    print(f"[sweep] wrote {path}", flush=True)
    return path
