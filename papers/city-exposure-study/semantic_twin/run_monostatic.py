"""The co-located return at the same standpoints the exposure runs use.

Two questions, one trace each, and the trace is the one ``run_exposure.py``
already runs. The gather of ``semantic_twin/transport/monostatic.py`` rides it
and reads off what a radar standing where the pedestrian stands would receive.

    python run_monostatic.py --sites all --locations 80 --rays 200000
    python run_monostatic.py --sites korenmarkt --evidence
    python run_monostatic.py --analyse

The first form answers whether the monostatic return predicts the exposure ratio
across the eleven squares. The second form answers what the closed loop buys in
image evidence, and needs a site with a fused walk binding. The third reduces
whatever is on disk to correlations and a figure. MONOSTATIC.md is the writeup.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import platform
import time
from typing import Any

import numpy as np

from semantic_twin.exposure.study import CONFIG, MODELS, REFERENCE_S0_W_M2, SITES, site_mesh, site_walk_semantics
from semantic_twin.propagation import MitsubaGeometry, SbrTracer, TraceConfig
from semantic_twin.transport.monostatic import MonostaticConfig, to_db, trace_monostatic
from semantic_twin.materials import classify_faces, load_table
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.ground import measure_ground_datum
from semantic_twin.walk.model import stratified_subset

ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs" / "monostatic"


def observed_mask(site: str, crop_m: int, face_count: int) -> tuple[np.ndarray | None, dict[str, Any]]:
    """Triangles a registered panorama collected a transient free ray on.

    The same mask ``materials.bind_walk_entities`` calls ``covered``, read
    straight off the fused walk npz. It is indexed by triangle against the mesh
    it was cast on, with no join key, so the face count is checked rather than
    assumed.
    """
    path = site_walk_semantics(site, crop_m)
    if path is None:
        return None, {"walk_semantics": None}
    data = np.load(path, allow_pickle=True)
    rays = data["clean_rays"]
    if rays.shape[1] != face_count:
        raise ValueError(f"{site}: walk semantics cover {rays.shape[1]} faces, the mesh has {face_count}")
    mask = rays.sum(axis=0) >= 1
    return mask, {
        "walk_semantics": str(path),
        "stations": int(rays.shape[0]),
        "observed_faces": int(mask.sum()),
        "observed_face_fraction": float(mask.mean()),
    }


def run_site(
    site: str,
    *,
    locations: int,
    rays: int,
    frequency_hz: float,
    max_bounces: int,
    crop_m: int,
    seed: int,
    variant: str,
    tag: str,
    walk_radius_m: float,
    walk_spacing_m: float,
    evidence: bool,
) -> pathlib.Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stem = f"{tag}_{site}_{frequency_hz / 1e9:g}ghz"
    rows_path = OUTPUT / f"{stem}_locations.jsonl"
    manifest_path = OUTPUT / f"{stem}_manifest.json"
    profile_path = OUTPUT / f"{stem}_profiles.npz"

    started = time.perf_counter()
    mesh = site_mesh(site, crop_m)
    geometry = MitsubaGeometry(mesh, variant=variant)
    datum = measure_ground_datum(geometry, radius_m=walk_radius_m).z_m
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(CONFIG, frequency_hz)

    mask: np.ndarray | None = None
    evidence_provenance: dict[str, Any] = {"requested": evidence}
    if evidence:
        mask, evidence_provenance = observed_mask(site, crop_m, geometry.face_count)
        evidence_provenance["requested"] = True
        if mask is None:
            raise ValueError(f"{site} has no fused walk binding at {crop_m} m, so there is no evidence mask")

    walk = build_walk(geometry, ground_datum_m=datum, radius_m=walk_radius_m, spacing_m=walk_spacing_m, seed=seed)
    picks = stratified_subset(walk, locations)
    config = TraceConfig(frequency_hz=frequency_hz, rays=rays, local_cells=512, max_bounces=max_bounces, seed=seed)
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
    monostatic = MonostaticConfig(max_order=max(4, max_bounces + 1), glint_max_range_m=float(crop_m))

    manifest = {
        "generator": "run_monostatic.py",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "site": site,
        "mesh": str(mesh),
        "mesh_triangles": int(geometry.face_count),
        "crop_radius_m": crop_m,
        "ground_datum_m": datum,
        "reference_s0_w_m2": REFERENCE_S0_W_M2,
        "trace_config": config.as_dict(),
        "monostatic_config": dict(monostatic.__dict__),
        "surface_binding": binding.as_dict(),
        "materials": "geometric class prior, identical across sites",
        "evidence": evidence_provenance,
        "walk": walk.provenance,
        "locations_traced": int(picks.size),
        "variant": variant,
        "python": platform.python_version(),
        "storage_policy": "paths are never written, only per location scalars and the range profile",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    profiles = np.zeros((picks.size, int(monostatic.max_two_way_range_m / monostatic.range_bin_m)))
    with rows_path.open("w") as handle:
        for row_index, index in enumerate(picks):
            point_xyz = walk.points[index]
            point, mono = trace_monostatic(
                tracer,
                point_xyz,
                MODELS,
                ground_z_m=float(walk.ground_z_m[index]),
                seed=seed + 1000 * index,
                config=monostatic,
                observed=mask,
            )
            row: dict[str, Any] = {
                "site": site,
                "index": int(index),
                "x": float(point_xyz[0]),
                "y": float(point_xyz[1]),
                "z": float(point_xyz[2]),
                "seconds": point.seconds,
            }
            row.update(point.scalars())
            row.update(mono.scalars())
            profiles[row_index] = mono.range_profile
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(
                f"[{site} {row_index + 1}/{picks.size}] mono={row['mono_gain_db']:.2f} dB "
                f"chi_iso={row['chi_isotropic']:.4f} glint={row['mono_glint_share']:.3f} "
                f"rse={row['mono_relative_standard_error']:.4f} ({mono.seconds:.1f} s)",
                flush=True,
            )
            np.savez_compressed(
                profile_path,
                range_profile=profiles[: row_index + 1],
                range_bin_m=monostatic.range_bin_m,
                index=picks[: row_index + 1],
            )
            if row_index == 0 and mono.coverage.get("available"):
                manifest["evidence_ledger_first_location"] = mono.coverage
                manifest_path.write_text(json.dumps(manifest, indent=2))

    manifest["wall_seconds"] = time.perf_counter() - started
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {rows_path}", flush=True)
    return rows_path


def run_stations(
    site: str,
    *,
    rays: int,
    frequency_hz: float,
    max_bounces: int,
    crop_m: int,
    seed: int,
    variant: str,
    tag: str,
) -> pathlib.Path:
    """The evidence experiment: stand the radar where the camera stood.

    The geometric guarantee is that both ends of a returning path are visible
    from the observation point. It becomes a guarantee about *image evidence*
    only when a camera stood at that point, so this run puts the observation
    point at each registered station rather than at a walk standpoint, which is
    the configuration the claim is actually about. Two masks are scored on the
    same geometry: the station's own rays, which is the strict reading, and the
    union over the walk, which is the mask the material binding really uses.
    """
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stem = f"{tag}_{site}_{frequency_hz / 1e9:g}ghz_stations"
    rows_path = OUTPUT / f"{stem}_locations.jsonl"
    manifest_path = OUTPUT / f"{stem}_manifest.json"

    semantics = site_walk_semantics(site, crop_m)
    if semantics is None:
        raise ValueError(f"{site} has no fused walk binding at {crop_m} m")
    document = json.loads(semantics.with_suffix(".json").read_text())
    data = np.load(semantics, allow_pickle=True)
    clean = data["clean_rays"]
    names = [str(name) for name in data["image_ids"]]
    stations = document["stations_admitted"]
    if len(stations) != clean.shape[0]:
        raise ValueError(
            f"{site}: {len(stations)} admitted stations against {clean.shape[0]} rows of cast rays, "
            "so the row order cannot be trusted"
        )

    mesh = site_mesh(site, crop_m)
    geometry = MitsubaGeometry(mesh, variant=variant)
    if clean.shape[1] != geometry.face_count:
        raise ValueError(f"{site}: walk semantics cover {clean.shape[1]} faces, the mesh has {geometry.face_count}")
    datum = measure_ground_datum(geometry, radius_m=90.0).z_m
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(CONFIG, frequency_hz)
    config = TraceConfig(frequency_hz=frequency_hz, rays=rays, local_cells=512, max_bounces=max_bounces, seed=seed)
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
    monostatic = MonostaticConfig(max_order=max(4, max_bounces + 1), glint_max_range_m=float(crop_m))
    fused = clean.sum(axis=0) >= 1

    manifest = {
        "generator": "run_monostatic.py --stations",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "site": site,
        "mesh": str(mesh),
        "mesh_triangles": int(geometry.face_count),
        "crop_radius_m": crop_m,
        "ground_datum_m": datum,
        "walk_semantics": str(semantics),
        "stations": names,
        "trace_config": config.as_dict(),
        "monostatic_config": dict(monostatic.__dict__),
        "fused_observed_face_fraction": float(fused.mean()),
        "own_observed_face_fraction": [float((row >= 1).mean()) for row in clean],
        "variant": variant,
        "python": platform.python_version(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))

    with rows_path.open("w") as handle:
        for row_index, station in enumerate(stations):
            point_xyz = np.asarray(station["position_enu_m"], dtype=np.float64)
            for mask_name, mask in (("own_station", clean[row_index] >= 1), ("fused_walk", fused)):
                point, mono = trace_monostatic(
                    tracer,
                    point_xyz,
                    MODELS,
                    ground_z_m=datum,
                    seed=seed + 977 * row_index,
                    config=monostatic,
                    observed=mask,
                )
                row: dict[str, Any] = {
                    "site": site,
                    "station": names[row_index],
                    "mask": mask_name,
                    "index": row_index,
                    "x": float(point_xyz[0]),
                    "y": float(point_xyz[1]),
                    "z": float(point_xyz[2]),
                    "camera_height_m": float(point_xyz[2] - datum),
                    "position_sigma_m": station.get("position_sigma_m"),
                    "residual_deg": station.get("residual_deg"),
                    "observed_face_fraction": float(mask.mean()),
                }
                row.update(point.scalars())
                row.update(mono.scalars())
                row["coverage"] = mono.coverage
                handle.write(json.dumps(row) + "\n")
                handle.flush()
                print(
                    f"[{names[row_index]} {mask_name}] closed loop chain "
                    f"{row['mono_evidence_chain_share']:.4f} against open path order 2 "
                    f"{row['adjoint_evidence_chain_share_order_2']:.4f}",
                    flush=True,
                )
    print(f"wrote {rows_path}", flush=True)
    return rows_path


def visible_faces(geometry: Any, origin: np.ndarray, probes: int = 2_000_000, chunk: int = 250_000) -> np.ndarray:
    """Triangles with a point directly visible from ``origin``, by first hit sampling.

    Denser than the trace that is scored against it, so a triangle the trace
    reaches on its first leg and this probe misses is unlikely rather than
    impossible. That asymmetry is the reason the number below is quoted as a
    lower bound on the theorem rather than as the theorem.
    """
    from semantic_twin.propagation import fibonacci_sphere

    directions = fibonacci_sphere(probes)
    seen = np.zeros(geometry.face_count, dtype=bool)
    for start in range(0, probes, chunk):
        batch = directions[start : start + chunk]
        hit, _, _, face = geometry.intersect(np.tile(origin, (batch.shape[0], 1)), batch)
        seen[face[hit]] = True
    return seen


def run_visibility(
    site: str,
    *,
    locations: int,
    rays: int,
    frequency_hz: float,
    max_bounces: int,
    crop_m: int,
    seed: int,
    variant: str,
    tag: str,
    walk_radius_m: float = 90.0,
    walk_spacing_m: float = 3.0,
    probes: int = 2_000_000,
) -> pathlib.Path:
    """The theorem on the real mesh, with visibility from the standpoint as the mask.

    Section 5.2 measures how far real image evidence falls short of geometric
    visibility. This measures the geometric statement on its own, on a
    photogrammetric city mesh rather than on the five plates of the unit test, by
    scoring the ledger against the set of triangles visible from the standpoint.
    """
    OUTPUT.mkdir(parents=True, exist_ok=True)
    stem = f"{tag}_{site}_{frequency_hz / 1e9:g}ghz_visibility"
    rows_path = OUTPUT / f"{stem}_locations.jsonl"

    mesh = site_mesh(site, crop_m)
    geometry = MitsubaGeometry(mesh, variant=variant)
    datum = measure_ground_datum(geometry, radius_m=walk_radius_m).z_m
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(CONFIG, frequency_hz)
    walk = build_walk(geometry, ground_datum_m=datum, radius_m=walk_radius_m, spacing_m=walk_spacing_m, seed=seed)
    picks = stratified_subset(walk, locations)
    config = TraceConfig(frequency_hz=frequency_hz, rays=rays, local_cells=512, max_bounces=max_bounces, seed=seed)
    tracer = SbrTracer(geometry, face_class, binding.permittivity, binding.rms_height_m, config)
    monostatic = MonostaticConfig(max_order=max(4, max_bounces + 1), glint_max_range_m=float(crop_m))

    with rows_path.open("w") as handle:
        for index in picks:
            point_xyz = walk.points[index]
            mask = visible_faces(geometry, point_xyz, probes=probes)
            _, mono = trace_monostatic(
                tracer,
                point_xyz,
                MODELS,
                ground_z_m=float(walk.ground_z_m[index]),
                seed=seed + 1000 * int(index),
                config=monostatic,
                observed=mask,
            )
            row = {
                "site": site,
                "index": int(index),
                "probes": probes,
                "visible_face_fraction": float(mask.mean()),
                "coverage": mono.coverage,
                **mono.scalars(),
            }
            handle.write(json.dumps(row) + "\n")
            handle.flush()
            print(
                f"[{site} {index}] closed loop order 1 {row['mono_evidence_chain_share_order_1']:.6f} "
                f"order 2 {row['mono_evidence_chain_share_order_2']:.6f} against open path order 2 "
                f"{row['adjoint_evidence_chain_share_order_2']:.4f}",
                flush=True,
            )
    print(f"wrote {rows_path}", flush=True)
    return rows_path


class _Plate:
    """One rectangle, brute forced, so the glint branch has a mesh to enumerate."""

    def __init__(self, side_m: float) -> None:
        self.vertices = np.array(
            [
                [-0.5 * side_m, -0.3 * side_m, 0.0],
                [0.7 * side_m, -0.3 * side_m, 0.0],
                [0.7 * side_m, 0.6 * side_m, 0.0],
                [-0.5 * side_m, 0.6 * side_m, 0.0],
            ]
        )
        self.faces = np.array([[0, 1, 2], [0, 2, 3]])

    def intersect(self, origins: np.ndarray, directions: np.ndarray):
        from semantic_twin.propagation.geometry import PlaneGeometry

        hit, distance, normal, face = PlaneGeometry(0.0).intersect(origins, directions)
        point = origins + np.where(hit, distance, 0.0)[:, None] * directions
        inside = (
            (point[:, 0] >= self.vertices[:, 0].min())
            & (point[:, 0] <= self.vertices[:, 0].max())
            & (point[:, 1] >= self.vertices[:, 1].min())
            & (point[:, 1] <= self.vertices[:, 1].max())
        )
        hit = hit & inside
        return hit, np.where(hit, distance, 1.0e30), normal, np.where(point[:, 0] > point[:, 1], 0, 1)


def validate(rays: int = 200_000) -> pathlib.Path:
    """The closed forms of MONOSTATIC_SBR.md section 11, with their residuals on file.

    Section 11.1 records that an earlier validation run left no artefact and that
    the number to quote had to come from somewhere else. This one writes the
    residuals down.
    """
    from semantic_twin.propagation import SphereGeometry
    from semantic_twin.transport.monostatic import MonostaticGather, specular_glints

    OUTPUT.mkdir(parents=True, exist_ok=True)
    wavelength = 299_792_458.0 / 15.0e9
    mirror = np.array([complex(1.0, -1.0e24)])
    lambertian = np.array([1.0e6])
    smooth = np.array([0.0])
    checks: dict[str, Any] = {}

    def cavity(radius: float, bounces: int) -> float:
        config = TraceConfig(
            frequency_hz=15.0e9,
            rays=rays,
            local_cells=64,
            max_bounces=bounces,
            roulette_start=99,
            ray_epsilon_m=1.0e-9,
            seed=3,
            batch=rays,
        )
        tracer = SbrTracer(SphereGeometry(radius), None, mirror, lambertian, config)
        gather = MonostaticGather(
            np.zeros(3),
            tracer.geometry,
            tracer.wavelength_m,
            MonostaticConfig(shadow_epsilon_m=1.0e-9),
        )
        tracer.trace(np.zeros(3), MODELS, gather=gather)
        return gather.finalise(rays)[0]

    for radius, bounces in ((10.0, 1), (8.0, 3)):
        target = bounces * wavelength**2 / (4.0 * np.pi**2 * radius**2)
        measured = cavity(radius, bounces)
        checks[f"lambertian_cavity_R{radius:g}_K{bounces}"] = {
            "target": target,
            "measured": measured,
            "relative_error": abs(measured / target - 1.0),
            "reference": "MONOSTATIC_SBR.md section 11.2, g_K = rho lam^2 / (4 pi^2 R^2) per order",
        }

    for height in (1.5, 3.0, 12.0):
        plate = _Plate(400.0)
        glint = specular_glints(
            np.array([0.0, 0.0, height]),
            vertices=plate.vertices,
            faces=plate.faces,
            face_class=None,
            permittivity=mirror,
            rms_height_m=smooth,
            wavelength_m=wavelength,
            geometry=plate,
            config=MonostaticConfig(shadow_epsilon_m=1.0e-9),
        )
        target = (wavelength / (8.0 * np.pi * height)) ** 2
        checks[f"image_source_h{height:g}m"] = {
            "target": target,
            "measured": glint.gain,
            "relative_error": abs(glint.gain / target - 1.0),
            "facets": glint.facets,
            "reference": "free space spreading over the unfolded round trip 2h, section 11.4",
        }

    range_m = 100.0
    triangle = _Plate(0.4)
    triangle.vertices = np.array([[-0.2, -0.2, 0.0], [0.2, -0.2, 0.0], [0.0, 0.2, 0.0], [0.0, 0.2, 0.0]])
    triangle.faces = np.array([[0, 1, 2]])
    area = 0.5 * float(
        np.linalg.norm(
            np.cross(triangle.vertices[1] - triangle.vertices[0], triangle.vertices[2] - triangle.vertices[0])
        )
    )
    glint = specular_glints(
        np.array([0.0, 0.0, range_m]),
        vertices=triangle.vertices,
        faces=triangle.faces,
        face_class=None,
        permittivity=mirror,
        rms_height_m=smooth,
        wavelength_m=wavelength,
        geometry=triangle,
        config=MonostaticConfig(shadow_epsilon_m=1.0e-9),
    )
    sigma = 4.0 * np.pi * area**2 / wavelength**2
    target = sigma * wavelength**2 / ((4.0 * np.pi) ** 3 * range_m**4)
    checks["physical_optics_plate"] = {
        "target": target,
        "measured": glint.gain,
        "relative_error": abs(glint.gain / target - 1.0),
        "plate_area_m2": area,
        "first_fresnel_area_m2": 0.5 * wavelength * range_m,
        "reference": "sigma = 4 pi A^2 / lam^2 at normal incidence, section 11.4",
    }

    summary = {
        "generator": "run_monostatic.py --validate",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rays": rays,
        "frequency_hz": 15.0e9,
        "note": (
            "The mirror is a permittivity with a 1e24 imaginary part rather than the package "
            "PEC stand in, whose 1e12 absorbs 2.8e-6 per bounce and would be read as an "
            "estimator error once several interaction orders are summed."
        ),
        "checks": checks,
    }
    path = OUTPUT / "monostatic_validation.json"
    path.write_text(json.dumps(summary, indent=2))
    for name, check in checks.items():
        print(f"{name}: {check['measured']:.6e} against {check['target']:.6e}, {check['relative_error']:.2e}")
    print(f"wrote {path}")
    return path


def load_rows(tag: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(OUTPUT.glob(f"{tag}_*_locations.jsonl")):
        with path.open() as handle:
            for line in handle:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 3:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _spearman(x: np.ndarray, y: np.ndarray) -> float:
    from scipy.stats import rankdata

    return _pearson(rankdata(x), rankdata(y))


def _partial(x: np.ndarray, y: np.ndarray, control: np.ndarray) -> float:
    """Correlation of ``x`` and ``y`` with the linear part of ``control`` taken out."""
    if x.size < 4:
        return float("nan")
    design = np.column_stack([np.ones_like(control), control])
    x_residual = x - design @ np.linalg.lstsq(design, x, rcond=None)[0]
    y_residual = y - design @ np.linalg.lstsq(design, y, rcond=None)[0]
    return _pearson(x_residual, y_residual)


def analyse(tag: str) -> pathlib.Path:
    """Correlate the co-located return against the exposure ratio, and report it.

    Everything is correlated in dB, which is the scale the exposure spread is
    quoted in and the scale a sounder measures on. Three targets, because they
    ask different questions: the total susceptibility, the part of it that is not
    the direct term, and the multipath gain, which is the ratio of the two. The
    monostatic return has no zero bounce term at all, so if it predicts anything
    it should predict the reflected part.
    """
    rows = load_rows(tag)
    if not rows:
        raise FileNotFoundError(f"no rows under {OUTPUT} for tag {tag!r}")
    sites = sorted({row["site"] for row in rows})
    models = [name for name in MODELS if f"chi_{name}" in rows[0]]

    def column(subset: list[dict[str, Any]], key: str) -> np.ndarray:
        return np.array([row[key] for row in subset], dtype=np.float64)

    def targets(subset: list[dict[str, Any]]) -> dict[str, np.ndarray]:
        out: dict[str, np.ndarray] = {}
        for name in models:
            total = column(subset, f"chi_{name}")
            direct = column(subset, f"chi_{name}_direct")
            out[f"chi_{name}"] = to_db(total)
            out[f"chi_{name}_reflected"] = to_db(np.maximum(total - direct, 0.0))
            out[f"multipath_gain_{name}"] = to_db(np.where(direct > 0.0, total / np.maximum(direct, 1e-300), 0.0))
        return out

    def block(subset: list[dict[str, Any]]) -> dict[str, Any]:
        sky = column(subset, "sky_fraction")
        out: dict[str, Any] = {"n": len(subset)}
        # Both the total and the incoherent part alone, because the enumerated
        # glint inherits the mesh's facet normals and a photogrammetric mesh has
        # noisy ones. If the two columns disagree, the conclusion rests on the
        # part of the estimator that does not depend on them.
        # ``mono_gain_order_2`` is here because the total is dominated by the
        # pavement under the observer, which knows nothing about the square. The
        # second order return is the part that has touched two surfaces, so it is
        # the part that could carry the buildings.
        for estimator in ("mono_gain", "mono_gain_diffuse", "mono_gain_order_2"):
            mono = to_db(column(subset, estimator))
            block_out: dict[str, Any] = {}
            for name, value in targets(subset).items():
                finite = np.isfinite(mono) & np.isfinite(value)
                block_out[name] = {
                    "pearson_db": _pearson(mono[finite], value[finite]),
                    "spearman": _spearman(mono[finite], value[finite]),
                    "partial_pearson_given_sky_fraction": _partial(mono[finite], value[finite], sky[finite]),
                    "partial_pearson_given_sky_fraction_db": _partial(mono[finite], value[finite], to_db(sky[finite])),
                }
            block_out["sky_fraction_against_mono_db"] = _pearson(mono, sky)
            out[estimator] = block_out
        for name in models:
            out[f"sky_fraction_against_chi_{name}_db"] = _pearson(sky, to_db(column(subset, f"chi_{name}")))
        out["glint_share"] = _quantiles(column(subset, "mono_glint_share"))
        out["glint_facets"] = _quantiles(column(subset, "mono_glint_facets"))
        out["relative_standard_error"] = _quantiles(column(subset, "mono_relative_standard_error"))
        return out

    summary: dict[str, Any] = {
        "generator": "run_monostatic.py --analyse",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tag": tag,
        "sites": sites,
        "locations": len(rows),
        "note": (
            "Correlations are between the co-located return in dB and the exposure ratio in dB. "
            "The pooled block mixes standpoints across sites, so it carries the between site spread. "
            "The within site blocks carry only the spread a pedestrian walks through."
        ),
        "pooled": block(rows),
        "per_site": {site: block([row for row in rows if row["site"] == site]) for site in sites},
        "site_medians": {
            site: {
                "mono_gain_db": float(np.median(to_db(column([r for r in rows if r["site"] == site], "mono_gain")))),
                **{
                    f"chi_{name}_db": float(
                        np.median(to_db(column([r for r in rows if r["site"] == site], f"chi_{name}")))
                    )
                    for name in models
                },
                "sky_fraction": float(np.median(column([r for r in rows if r["site"] == site], "sky_fraction"))),
            }
            for site in sites
        },
    }
    medians = summary["site_medians"]
    if len(sites) > 2:
        mono_medians = np.array([medians[s]["mono_gain_db"] for s in sites])
        summary["between_site"] = {
            "n": len(sites),
            **{
                f"chi_{name}": {
                    "pearson_db": _pearson(mono_medians, np.array([medians[s][f"chi_{name}_db"] for s in sites])),
                    "spearman": _spearman(mono_medians, np.array([medians[s][f"chi_{name}_db"] for s in sites])),
                }
                for name in models
            },
        }

    evidence = [row for row in rows if "mono_evidence_chain_share" in row]
    if evidence:
        summary["evidence"] = {
            "n": len(evidence),
            "sites": sorted({row["site"] for row in evidence}),
            "closed_loop_chain_observed": _quantiles(column(evidence, "mono_evidence_chain_share")),
            "closed_loop_last_surface_observed": _quantiles(column(evidence, "mono_evidence_last_share")),
            **{
                f"order_{order}": {
                    "closed_loop_chain_observed": _quantiles(
                        column(evidence, f"mono_evidence_chain_share_order_{order}")
                    ),
                    "open_path_chain_observed": _quantiles(
                        column(evidence, f"adjoint_evidence_chain_share_order_{order}")
                    ),
                }
                for order in (1, 2, 3)
                if f"mono_evidence_chain_share_order_{order}" in evidence[0]
            },
        }

    path = OUTPUT / f"{tag}_correlations.json"
    path.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary["pooled"], indent=2))
    print(f"wrote {path}")
    return path


def figure(tag: str) -> pathlib.Path:
    """Two panels: what the closed loop buys, and what the return predicts."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = load_rows(tag)
    stations = [
        json.loads(line)
        for path in sorted(OUTPUT.glob("*_stations_locations.jsonl"))
        for line in path.open()
        if line.strip()
    ]
    visibility = [
        json.loads(line)
        for path in sorted(OUTPUT.glob("*_visibility_locations.jsonl"))
        for line in path.open()
        if line.strip()
    ]

    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2))
    left, right = axes

    groups = [
        ("visible from\nthe standpoint", [r for r in visibility]),
        ("its own\ncamera", [r for r in stations if r.get("mask") == "own_station"]),
        ("any camera\non the walk", [r for r in stations if r.get("mask") == "fused_walk"]),
    ]
    width = 0.35
    for column, (label, subset) in enumerate(groups):
        if not subset:
            continue
        for offset, prefix, colour, name in (
            (-0.5, "mono_evidence_chain_share_order", "#1f77b4", "closed loop"),
            (0.5, "adjoint_evidence_chain_share_order", "#d62728", "open path"),
        ):
            values = [float(np.median([r[f"{prefix}_{order}"] for r in subset])) for order in (1, 2, 3)]
            for order_index, value in enumerate(values):
                left.bar(
                    column + offset * width + 0.12 * (order_index - 1),
                    value,
                    width=0.11,
                    color=colour,
                    alpha=0.45 + 0.27 * order_index,
                    edgecolor="none",
                    label=f"{name}, order {order_index + 1}" if column == 0 else None,
                )
    left.set_xticks(range(len(groups)))
    left.set_xticklabels([label for label, _ in groups])
    left.set_ylim(0.0, 1.05)
    left.set_ylabel("share of power on a fully observed chain")
    left.set_title("what closing the loop guarantees")
    left.legend(fontsize=7, loc="lower left", ncol=2)
    left.grid(axis="y", alpha=0.3)

    sites = sorted({row["site"] for row in rows})
    colours = plt.get_cmap("tab20")(np.linspace(0.0, 0.95, max(len(sites), 1)))
    for colour, site in zip(colours, sites, strict=True):
        subset = [row for row in rows if row["site"] == site]
        mono = to_db(np.array([row["mono_gain"] for row in subset]))
        chi = to_db(np.array([row["chi_isotropic"] for row in subset]))
        right.scatter(mono, chi, s=10, color=colour, alpha=0.75, label=site.replace("_", " "), edgecolors="none")
    if rows:
        mono = to_db(np.array([row["mono_gain"] for row in rows]))
        chi = to_db(np.array([row["chi_isotropic"] for row in rows]))
        right.set_title(f"pooled r = {_pearson(mono, chi):+.2f} over {len(rows)} standpoints")
    right.set_xlabel("co-located return, dB")
    right.set_ylabel("isotropic susceptibility, dB")
    right.legend(fontsize=6, loc="upper right", ncol=2)
    right.grid(alpha=0.3)

    fig.tight_layout()
    path = OUTPUT / f"{tag}_monostatic.png"
    fig.savefig(path, dpi=200)
    fig.savefig(path.with_suffix(".pdf"))
    plt.close(fig)
    print(f"wrote {path}")
    return path


def _quantiles(values: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"n": 0}
    return {
        "n": int(finite.size),
        "min": float(finite.min()),
        "median": float(np.median(finite)),
        "mean": float(finite.mean()),
        "max": float(finite.max()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sites", default="korenmarkt", help="comma separated, or 'all'")
    parser.add_argument("--locations", type=int, default=80)
    parser.add_argument("--rays", type=int, default=200_000)
    parser.add_argument("--max-bounces", type=int, default=3)
    parser.add_argument("--crop-m", type=int, default=250)
    parser.add_argument("--frequency-ghz", type=float, default=15.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--variant", default="llvm_ad_rgb")
    parser.add_argument("--walk-radius-m", type=float, default=90.0)
    parser.add_argument("--walk-spacing-m", type=float, default=3.0)
    parser.add_argument("--tag", default="mono250")
    parser.add_argument("--evidence", action="store_true", help="carry the panorama observed mask")
    parser.add_argument("--stations", action="store_true", help="stand at the registered cameras instead")
    parser.add_argument("--visibility", action="store_true", help="score the ledger against visibility alone")
    parser.add_argument("--analyse", action="store_true")
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)

    if args.validate:
        validate()
        return 0
    if args.analyse:
        analyse(args.tag)
        figure(args.tag)
        return 0

    sites = SITES if args.sites == "all" else tuple(name.strip() for name in args.sites.split(","))
    if args.visibility:
        for site in sites:
            run_visibility(
                site,
                locations=args.locations,
                rays=args.rays,
                frequency_hz=args.frequency_ghz * 1e9,
                max_bounces=args.max_bounces,
                crop_m=args.crop_m,
                seed=args.seed,
                variant=args.variant,
                tag=args.tag,
                walk_radius_m=args.walk_radius_m,
                walk_spacing_m=args.walk_spacing_m,
            )
        return 0
    if args.stations:
        for site in sites:
            run_stations(
                site,
                rays=args.rays,
                frequency_hz=args.frequency_ghz * 1e9,
                max_bounces=args.max_bounces,
                crop_m=args.crop_m,
                seed=args.seed,
                variant=args.variant,
                tag=args.tag,
            )
        return 0
    for site in sites:
        run_site(
            site,
            locations=args.locations,
            rays=args.rays,
            frequency_hz=args.frequency_ghz * 1e9,
            max_bounces=args.max_bounces,
            crop_m=args.crop_m,
            seed=args.seed,
            variant=args.variant,
            tag=args.tag,
            walk_radius_m=args.walk_radius_m,
            walk_spacing_m=args.walk_spacing_m,
            evidence=args.evidence,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
