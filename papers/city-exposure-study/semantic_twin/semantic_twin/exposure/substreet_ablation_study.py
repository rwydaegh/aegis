"""Exposure ablation for reconstructed geometry below street level."""

from __future__ import annotations

import json
import pathlib
import time
from dataclasses import dataclass, field

import numpy as np

from semantic_twin import paths
from semantic_twin.exposure.study import MODELS, ground_datum, site_mesh
from semantic_twin.materials import classify_faces, load_table
from semantic_twin.propagation import MitsubaGeometry
from semantic_twin.transport import DEFAULT_MAX_BOUNCES, SbrTracer, TraceConfig
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.model import stratified_subset

FREQUENCY_HZ = 15.0e9


@dataclass(frozen=True)
class SubstreetAblationConfig:
    site: str = "newyork_timessquare"
    crop_m: int = 250
    locations: int = 40
    walk_radius_m: float = 60.0
    rays: int = 120_000
    floor_below_datum_m: float = 8.0
    seed: int = 0
    out: pathlib.Path | None = None
    root: pathlib.Path = field(default_factory=paths.root)

    @property
    def output_dir(self) -> pathlib.Path:
        return self.out or self.root / "outputs" / "substreet_ablation"


def write_culled(geometry: MitsubaGeometry, floor_z: float, path: pathlib.Path) -> tuple[pathlib.Path, int, int]:
    corners = geometry.vertices[geometry.faces]
    keep = corners[:, :, 2].max(axis=1) >= floor_z
    faces = geometry.faces[keep]
    used, remapped = np.unique(faces, return_inverse=True)
    vertices = geometry.vertices[used]
    faces = remapped.reshape(faces.shape)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(b"ply\nformat binary_little_endian 1.0\n")
        handle.write(f"element vertex {vertices.shape[0]}\n".encode())
        handle.write(b"property float x\nproperty float y\nproperty float z\n")
        handle.write(f"element face {faces.shape[0]}\n".encode())
        handle.write(b"property list uchar int vertex_indices\nend_header\n")
        handle.write(np.ascontiguousarray(vertices, dtype="<f4").tobytes())
        block = np.empty(faces.shape[0], dtype=[("n", "u1"), ("v", "<i4", 3)])
        block["n"] = 3
        block["v"] = faces
        handle.write(block.tobytes())
    return path, int(geometry.faces.shape[0]), int(faces.shape[0])


def trace_all(
    geometry: MitsubaGeometry,
    datum: float,
    points: np.ndarray,
    datums: np.ndarray,
    config: TraceConfig,
    config_dir: pathlib.Path,
) -> dict[str, np.ndarray]:
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(config_dir, FREQUENCY_HZ)
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
    rows = []
    for index, (point, ground) in enumerate(zip(points, datums, strict=True)):
        result = tracer.trace(point, MODELS, ground_z_m=float(ground), seed=config.seed + index)
        rows.append(result.scalars())
    return {key: np.array([row[key] for row in rows]) for key in rows[0]}


def run_substreet_ablation(config: SubstreetAblationConfig) -> pathlib.Path:
    started = time.perf_counter()
    config.output_dir.mkdir(parents=True, exist_ok=True)
    mesh = site_mesh(config.site, config.crop_m, root_dir=config.root)
    geometry = MitsubaGeometry(mesh)
    datum = ground_datum(geometry, radius_m=config.walk_radius_m)
    floor_z = datum - config.floor_below_datum_m

    culled_path, before, after = write_culled(
        geometry,
        floor_z,
        config.output_dir / f"{config.site}_culled.ply",
    )
    print(f"{config.site}: datum {datum:.2f} m, floor {floor_z:.2f} m, {before} faces -> {after}", flush=True)

    walk = build_walk(
        geometry,
        ground_datum_m=datum,
        radius_m=config.walk_radius_m,
        spacing_m=3.0,
        seed=config.seed,
    )
    picks = stratified_subset(walk, config.locations)
    points, datums = walk.points[picks], walk.ground_z_m[picks]
    print(f"walk: {len(walk)} candidates, tracing {picks.size} against both meshes", flush=True)

    trace_config = TraceConfig(
        frequency_hz=FREQUENCY_HZ,
        rays=config.rays,
        local_cells=512,
        max_bounces=DEFAULT_MAX_BOUNCES,
        seed=config.seed,
    )
    as_built = trace_all(geometry, datum, points, datums, trace_config, config.root / "config")
    culled = trace_all(MitsubaGeometry(culled_path), datum, points, datums, trace_config, config.root / "config")

    report: dict[str, object] = {
        "site": config.site,
        "crop_radius_m": config.crop_m,
        "ground_datum_m": datum,
        "cull_floor_z_m": floor_z,
        "faces_before": before,
        "faces_after": after,
        "faces_removed_fraction": (before - after) / before,
        "locations": int(picks.size),
        "rays": config.rays,
        "seconds": None,
    }
    print(f"\n{'quantity':28s} {'as built':>12s} {'culled':>12s} {'shift dB':>10s}")
    for key in ("chi_isotropic", "chi_rooftop", "chi_street_small_cell", "sky_fraction"):
        a, b = as_built[key], culled[key]
        median_a, median_b = float(np.median(a)), float(np.median(b))
        shift = 10.0 * np.log10(median_b / median_a) if median_a > 0.0 and median_b > 0.0 else float("nan")
        per_location_shift = np.abs(10.0 * np.log10(np.maximum(b, 1e-12) / np.maximum(a, 1e-12)))
        report[key] = {
            "median_as_built": median_a,
            "median_culled": median_b,
            "median_shift_db": shift,
            "worst_location_shift_db": float(np.max(per_location_shift)),
            "locations_moving_over_0p5_db": int(np.count_nonzero(per_location_shift > 0.5)),
        }
        print(f"{key:28s} {median_a:12.5f} {median_b:12.5f} {shift:10.3f}")
    report["seconds"] = time.perf_counter() - started
    path = config.output_dir / f"{config.site}_substreet.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(f"\n[done] {path}")
    return path
