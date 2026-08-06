"""Compare corrected and fixed-height illumination laws on identical rays."""

from __future__ import annotations

import json
import pathlib
import time
from dataclasses import dataclass, field

import numpy as np

from semantic_twin import paths
from semantic_twin.exposure.study import GROUND_DATUM_M, ground_datum, site_mesh
from semantic_twin.illumination import VARIANTS
from semantic_twin.materials import classify_faces, load_table
from semantic_twin.propagation import MitsubaGeometry
from semantic_twin.transport import DEFAULT_MAX_BOUNCES, SbrTracer, TraceConfig
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.model import stratified_subset

PAIRS = {"rooftop": "rooftop_fixed_height", "street_small_cell": "street_small_cell_fixed_height"}


@dataclass(frozen=True)
class LawComparisonConfig:
    site: str = "korenmarkt"
    crops: tuple[int, ...] = (130, 250)
    anchor_crop_m: int = 130
    locations: int = 40
    walk_radius_m: float = 60.0
    rays: int = 150_000
    frequency_hz: float = 15.0e9
    seed: int = 0
    out: pathlib.Path | None = None
    root: pathlib.Path = field(default_factory=paths.root)

    @property
    def output_dir(self) -> pathlib.Path:
        return self.out or self.root / "outputs" / "law_comparison"


def trace_site(config: LawComparisonConfig, crop_m: int) -> dict[str, np.ndarray]:
    mesh = site_mesh(config.site, crop_m, root_dir=config.root)
    geometry = MitsubaGeometry(mesh)
    datum = GROUND_DATUM_M if config.site == "korenmarkt" else ground_datum(geometry)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(config.root / "config", config.frequency_hz)
    trace_config = TraceConfig(
        frequency_hz=config.frequency_hz,
        rays=config.rays,
        local_cells=512,
        max_bounces=DEFAULT_MAX_BOUNCES,
        seed=config.seed,
    )
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, trace_config)

    anchor = MitsubaGeometry(site_mesh(config.site, config.anchor_crop_m, root_dir=config.root))
    anchor_datum = GROUND_DATUM_M if config.site == "korenmarkt" else ground_datum(anchor)
    walk = build_walk(
        anchor,
        ground_datum_m=anchor_datum,
        radius_m=config.walk_radius_m,
        spacing_m=3.0,
        seed=config.seed,
    )
    picks = stratified_subset(walk, config.locations)
    points, datums = walk.points[picks], walk.ground_z_m[picks]

    rows = []
    for index, (point, ground) in enumerate(zip(points, datums, strict=True)):
        result = tracer.trace(point, VARIANTS, ground_z_m=float(ground), seed=config.seed + index)
        rows.append(result.scalars())
    keys = {key for row in rows for key in row}
    return {key: np.array([row.get(key, np.nan) for row in rows]) for key in sorted(keys)}


def run_law_comparison(config: LawComparisonConfig) -> pathlib.Path:
    started = time.perf_counter()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    by_crop = {}
    for crop in config.crops:
        print(f"[trace] {config.site} at {crop} m", flush=True)
        by_crop[crop] = trace_site(config, crop)

    report: dict[str, object] = {
        "site": config.site,
        "crops_m": config.crops,
        "anchor_crop_m": config.anchor_crop_m,
        "locations": config.locations,
        "rays": config.rays,
        "note": (
            "Old and new law come from the same rays at each crop, so the level "
            "difference between them carries no Monte Carlo noise. The crop difference within one law does."
        ),
    }

    print(f"\n{'model':32s} " + " ".join(f"{crop:>12d} m" for crop in config.crops))
    for new, old in PAIRS.items():
        for name in (old, new):
            medians = [float(np.median(by_crop[crop][f"chi_{name}"])) for crop in config.crops]
            print(f"{name:32s} " + " ".join(f"{median:14.5f}" for median in medians))
            report[name] = {
                "median_by_crop": dict(zip([str(crop) for crop in config.crops], medians, strict=True)),
                "crop_correction_db": (
                    10.0 * np.log10(medians[-1] / medians[0]) if medians[0] > 0.0 and medians[-1] > 0.0 else None
                ),
            }
        shift = [
            10.0 * np.log10(np.median(by_crop[crop][f"chi_{new}"]) / np.median(by_crop[crop][f"chi_{old}"]))
            for crop in config.crops
        ]
        report[f"{new}_law_shift_db"] = dict(zip([str(crop) for crop in config.crops], shift, strict=True))
        print(f"{'  new against old, dB':32s} " + " ".join(f"{value:14.3f}" for value in shift))
        print(
            f"{'  crop correction, dB':32s} "
            f"old {report[old]['crop_correction_db']:+.3f}   new {report[new]['crop_correction_db']:+.3f}\n"
        )

    isotropic = [float(np.median(by_crop[crop]["chi_isotropic"])) for crop in config.crops]
    report["isotropic"] = {"median_by_crop": dict(zip([str(crop) for crop in config.crops], isotropic, strict=True))}
    print(f"{'isotropic, unchanged by the law':32s} " + " ".join(f"{median:14.5f}" for median in isotropic))

    report["seconds"] = time.perf_counter() - started
    path = config.output_dir / f"{config.site}_law_comparison.json"
    path.write_text(json.dumps(report, indent=2, default=float) + "\n")
    print(f"\n[done] {path}")
    return path
