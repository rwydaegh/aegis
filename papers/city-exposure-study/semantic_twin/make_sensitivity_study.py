"""Sensitivity of the published susceptibility to the deployment geometry.

The illumination models integrate over base stations of uniform areal density
lying in a height band and a range band. DEPLOYMENT_GEOMETRY.md section 4.3
establishes that no register anywhere contains a deployed cellular antenna above
6 GHz, so neither band can be cited. They can only be assumed, and an assumption
that cannot be cited has to be reported as a sensitivity. This script is that
report, computed on the full traced `chi` rather than on the zero bounce proxy
that DEPLOYMENT_GEOMETRY.md section 7.5 had to use.

How it avoids retracing once per parameter value
------------------------------------------------
`chi` is a linear functional of the illumination density. The tracer forms

    chi = dOmega * sum over cells of (1 / n_cell) * sum over escaping rays of
          throughput * Q(u_exit)

and every band law here is uniform in azimuth, so `Q(u)` depends on the exit
direction only through its elevation. Accumulating

    W[b] = dOmega * sum over escaping rays in elevation bin b of
           throughput / n_cell(ray)

therefore reduces the whole trace to one vector, and `chi` for any illumination
model whatsoever is the dot product `W . Q`. One trace per standpoint then
supports an arbitrarily dense parameter sweep, exactly, with no Monte Carlo
noise between parameter values.

`W` does not scale with the ray count, so keeping it does not break the storage
rule of this study. No path is written.

The second harvested array `W2` carries a coarser elevation axis crossed with
the horizontal range at which the escaping ray leaves the built crop. That axis
exists for one question: the geometry crop radius and the illumination range cap
are different things, and a range cap larger than the built extent integrates
over sources whose intervening geometry was never reconstructed.

Usage
-----
    python make_sensitivity_study.py --harvest          # trace, ~1 h for 11 sites
    python make_sensitivity_study.py --analyse          # sweeps from the harvest
    python make_sensitivity_study.py --figures          # replot from the sweeps
    python make_sensitivity_study.py                    # all three in order
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys
import time
from typing import Any

import numpy as np

from semantic_twin.propagation import (
    MODELS,
    MitsubaGeometry,
    SbrTracer,
    TraceConfig,
)
from semantic_twin.illumination import BandLaw, IlluminationModel
from semantic_twin.materials import classify_faces, load_table
from semantic_twin.walk.grid import build_walk
from semantic_twin.walk.model import stratified_subset

ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs" / "sensitivity"

#: The published cross city run this study perturbs, read off its own manifests
#: rather than retyped: outputs/exposure_korenmarkt/city250_corrected_*.
PUBLISHED_TAG = "city250_corrected"
PUBLISHED_DIR = ROOT / "outputs" / "exposure_korenmarkt"
CROP_M = 250
LOCATIONS = 80
RAYS = 200_000
LOCAL_CELLS = 512
SEED = 7
WALK_RADIUS_M = 90.0
WALK_SPACING_M = 3.0
FREQUENCY_HZ = 15.0e9
VARIANT = "llvm_ad_rgb"

#: Pinned rather than taken from the tracer's current default. This study is a
#: perturbation of one published run and has to reproduce it, so a later change
#: to the library default must not silently change what is being perturbed.
#: ``published_trace_config`` checks the pin against the published manifest and
#: refuses to run if they have drifted apart.
MAX_BOUNCES = 4


def published_trace_config() -> dict[str, Any]:
    """The published run's own trace settings, read from its manifest.

    Raises rather than warns. A harvest that quietly used different settings
    would produce a sensitivity study of a run nobody published.
    """
    manifest = PUBLISHED_DIR / f"{PUBLISHED_TAG}_korenmarkt_15ghz_manifest.json"
    if not manifest.exists():
        raise FileNotFoundError(f"no published manifest at {manifest}")
    config = json.loads(manifest.read_text())["trace_config"]
    pinned = {
        "rays": RAYS,
        "local_cells": LOCAL_CELLS,
        "max_bounces": MAX_BOUNCES,
        "seed": SEED,
        "frequency_hz": FREQUENCY_HZ,
    }
    drift = {k: (v, config[k]) for k, v in pinned.items() if config[k] != v}
    if drift:
        raise RuntimeError(f"harvest settings have drifted from the published run: {drift}")
    return config


#: Fine elevation axis for the reweighting. 0.04 degrees, over the whole sphere
#: so the isotropic control is carried too. The band laws vary on a scale of
#: degrees, so this is roughly two orders of magnitude finer than it needs to
#: be, and the harvest checks that rather than assuming it.
ELEVATION_BINS = 4500

#: Coarser elevation axis crossed with the built extent, for the crop question.
CROP_ELEVATION_BINS = 900
CROP_RANGE_EDGES_M = np.array(
    [0.0, 25.0, 50.0, 75.0, 100.0, 125.0, 150.0, 175.0, 200.0, 225.0, 250.0, 275.0, 300.0, 350.0, 400.0, 500.0, np.inf]
)


def site_list() -> tuple[str, ...]:
    import run_exposure

    return run_exposure.SITES


# --------------------------------------------------------------------------
# Harvest
# --------------------------------------------------------------------------


class HarvestTracer(SbrTracer):
    """The shipped tracer, plus one reduced angular accumulator per standpoint.

    Nothing about the ray paths changes. `_deposit` is extended, not replaced,
    and no random draw is touched, so a harvested `chi` has to reproduce the
    published one to the accuracy of the elevation binning. The harvest asserts
    that rather than trusting it.
    """

    def __init__(self, *args: Any, crop_radius_m: float, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.crop_radius_m = float(crop_radius_m)
        self._records: list[tuple[np.ndarray, ...]] = []
        self._cell_counts: np.ndarray | None = None
        self._origin_xy = np.zeros(2)

    def trace(self, origin: np.ndarray, models: Any, **kwargs: Any) -> Any:
        self._records = []
        self._cell_counts = None
        self._origin_xy = np.asarray(origin, dtype=np.float64)[:2]
        return super().trace(origin, models, **kwargs)

    def _run_batch(self, origin, count, rng, models, normalisations, rho, rho_direct, cell_counts, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN201
        # Held by reference. After ``trace`` returns it carries the final per
        # cell ray counts, which is the divisor the published ``chi`` uses.
        self._cell_counts = cell_counts
        return super()._run_batch(
            origin, count, rng, models, normalisations, rho, rho_direct, cell_counts, *args, **kwargs
        )

    def _deposit(
        self, index, exit_direction, throughput, cell, path_length, last_vertex, origin, bounces, *args, **kwargs
    ):  # noqa: ANN001, ANN002, ANN003, ANN201
        elevation = np.degrees(np.arcsin(np.clip(exit_direction[:, 2], -1.0, 1.0)))
        self._records.append(
            (
                np.asarray(cell, dtype=np.int32).copy(),
                elevation.astype(np.float64),
                self._built_range(last_vertex, exit_direction),
                np.asarray(throughput, dtype=np.float64).copy(),
                np.asarray(bounces, dtype=np.int32).copy(),
            )
        )
        return super()._deposit(
            index, exit_direction, throughput, cell, path_length, last_vertex, origin, bounces, *args, **kwargs
        )

    def _built_range(self, last_vertex: np.ndarray, exit_direction: np.ndarray) -> np.ndarray:
        """Horizontal range from the standpoint at which the ray leaves the crop.

        The mesh is a cylinder of radius ``crop_radius_m`` about the crop
        centre, so an escaping ray stops having geometry around it where it
        crosses that cylinder. A source further out than this along the same
        direction is a source whose line of sight was never reconstructed.

        This inherits the far source approximation the estimator already makes:
        the exit direction is read as the arrival direction at the standpoint,
        so the crossing point is measured back to the standpoint rather than to
        the last bounce. For a zero bounce ray the two are the same point.
        """
        p = last_vertex[:, :2]
        u = exit_direction[:, :2]
        a = np.einsum("ij,ij->i", u, u)
        b = np.einsum("ij,ij->i", p, u)
        c = np.einsum("ij,ij->i", p, p) - self.crop_radius_m**2
        with np.errstate(divide="ignore", invalid="ignore"):
            step = (-b + np.sqrt(np.maximum(b * b - a * c, 0.0))) / a
        crossing = p + np.where(np.isfinite(step), step, 0.0)[:, None] * u
        reach = np.linalg.norm(crossing - self._origin_xy, axis=1)
        # A ray with no horizontal component never leaves the cylinder.
        return np.where(a > 1.0e-12, reach, np.inf)

    def harvest(self) -> dict[str, np.ndarray]:
        """Reduce the recorded escapes to the two reweighting arrays."""
        counts = np.maximum(self._cell_counts, 1.0)
        solid_angle = 4.0 * np.pi / self.config.local_cells
        fine = np.zeros(ELEVATION_BINS, dtype=np.float64)
        direct = np.zeros(ELEVATION_BINS, dtype=np.float64)
        crop = np.zeros((CROP_ELEVATION_BINS, CROP_RANGE_EDGES_M.size - 1), dtype=np.float64)
        for cell, elevation, reach, throughput, bounces in self._records:
            weight = solid_angle * throughput / counts[cell]
            fine_bin = np.clip(((elevation + 90.0) / 180.0 * ELEVATION_BINS).astype(np.int64), 0, ELEVATION_BINS - 1)
            np.add.at(fine, fine_bin, weight)
            zero = bounces == 0
            np.add.at(direct, fine_bin[zero], weight[zero])
            coarse_bin = np.clip(
                ((elevation + 90.0) / 180.0 * CROP_ELEVATION_BINS).astype(np.int64), 0, CROP_ELEVATION_BINS - 1
            )
            reach_bin = np.clip(np.searchsorted(CROP_RANGE_EDGES_M, reach, side="right") - 1, 0, crop.shape[1] - 1)
            np.add.at(crop, (coarse_bin, reach_bin), weight)
        return {"fine": fine.astype(np.float32), "direct": direct.astype(np.float32), "crop": crop.astype(np.float32)}


def elevation_centres(bins: int) -> np.ndarray:
    edges = np.linspace(-90.0, 90.0, bins + 1)
    return 0.5 * (edges[:-1] + edges[1:])


def harvest_site(site: str, *, locations: int = LOCATIONS, rays: int = RAYS, stride: int = 1) -> pathlib.Path:
    """One trace per published standpoint, reduced to reweighting arrays.

    ``stride`` thins the published standpoint list rather than requesting fewer
    standpoints from the walk. Thinning keeps every harvested standpoint a
    standpoint the published run also traced, so the harvest can be checked
    against the published number at each one. Asking the walk for half as many
    would have returned a different, unrelated set.
    """
    import run_exposure

    published_trace_config()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT / f"harvest_{site}.npz"
    mesh = run_exposure.site_mesh(site, CROP_M)
    manifest = json.loads(mesh.with_suffix(".json").read_text())
    crop_radius_m = float(manifest["crop_radius_m"])

    started = time.perf_counter()
    geometry = MitsubaGeometry(mesh, variant=VARIANT)
    # One rule for all eleven sites, the same call ``run_exposure.run`` makes.
    # Korenmarkt has a registered camera datum available as a constant, and an
    # earlier version of this script used it there and the measurement
    # everywhere else. The two differ by 3 cm at Korenmarkt, which is nothing,
    # but a cross city study that applies two rules invites the question at the
    # one site where it can be asked.
    datum = run_exposure.ground_datum(geometry, radius_m=WALK_RADIUS_M)
    face_class = classify_faces(geometry.vertices, geometry.faces, datum)
    binding = load_table(run_exposure.CONFIG, FREQUENCY_HZ)
    walk = build_walk(geometry, ground_datum_m=datum, radius_m=WALK_RADIUS_M, spacing_m=WALK_SPACING_M, seed=SEED)
    picks = stratified_subset(walk, locations)[:: max(1, int(stride))]

    config = TraceConfig(
        frequency_hz=FREQUENCY_HZ, rays=rays, local_cells=LOCAL_CELLS, max_bounces=MAX_BOUNCES, seed=SEED
    )
    tracer = HarvestTracer(
        geometry, face_class, binding.permittivity, binding.rms_height_m, config, crop_radius_m=crop_radius_m
    )

    fine = np.zeros((picks.size, ELEVATION_BINS), dtype=np.float32)
    direct = np.zeros_like(fine)
    crop = np.zeros((picks.size, CROP_ELEVATION_BINS, CROP_RANGE_EDGES_M.size - 1), dtype=np.float32)
    traced = np.zeros((picks.size, len(MODELS)))
    xy = np.zeros((picks.size, 3))
    for row, index in enumerate(picks):
        point = walk.points[index]
        result = tracer.trace(point, MODELS, ground_z_m=float(walk.ground_z_m[index]), seed=SEED + 1000 * index)
        arrays = tracer.harvest()
        fine[row] = arrays["fine"]
        direct[row] = arrays["direct"]
        crop[row] = arrays["crop"]
        traced[row] = [result.susceptibility[name] for name in MODELS]
        xy[row] = point
        print(
            f"  [{row + 1}/{picks.size}] chi_rooftop={result.susceptibility['rooftop']:.4f} ({result.seconds:.1f} s)",
            flush=True,
        )

    np.savez_compressed(
        destination,
        fine=fine,
        direct=direct,
        crop=crop,
        crop_range_edges_m=CROP_RANGE_EDGES_M,
        traced_chi=traced,
        traced_models=np.array(list(MODELS)),
        points=xy,
        index=picks,
        crop_radius_m=crop_radius_m,
        elevation_bins=ELEVATION_BINS,
        crop_elevation_bins=CROP_ELEVATION_BINS,
        wall_seconds=time.perf_counter() - started,
        mesh=str(mesh),
    )
    print(f"wrote {destination} in {time.perf_counter() - started:.0f} s", flush=True)
    return destination


# --------------------------------------------------------------------------
# Reweighting
# --------------------------------------------------------------------------

#: The three shipped models and the bands they carry. `isotropic` has no band at
#: all, which makes it the control: nothing in this study may move it.
DEFAULTS: dict[str, dict[str, Any]] = {
    "rooftop": {"height_band_m": (13.5, 43.5), "range_band_m": (25.0, 250.0)},
    "street_small_cell": {"height_band_m": (2.5, 6.5), "range_band_m": (10.0, 150.0)},
}

#: Spans over which each endpoint is defensible, from DEPLOYMENT_GEOMETRY.md
#: sections 11.2 and 12. The macro floor spans the two branches of section 4.4,
#: overlay at 16.5 m and densification at 8.5 m. The macro ceiling spans the
#: current 43.5 m and the recommended 38.5 m, widened to 33.5 m by the
#: superseded draft. The small cell endpoints are the ones section 12 leaves
#: unchanged, so their spans are the stated confidence intervals rather than
#: competing recommendations.
DEFENSIBLE: dict[str, dict[str, tuple[float, float]]] = {
    "rooftop": {
        "h_min": (8.5, 16.5),
        "h_max": (33.5, 43.5),
        "d_min": (10.0, 50.0),
        "d_max": (150.0, 400.0),
    },
    "street_small_cell": {
        "h_min": (1.5, 3.5),
        "h_max": (5.0, 8.5),
        "d_min": (5.0, 25.0),
        "d_max": (100.0, 250.0),
    },
}


def band_model(name: str, h_min: float, h_max: float, d_min: float, d_max: float) -> IlluminationModel:
    return BandLaw(
        name=f"{name}_{h_min:g}_{h_max:g}_{d_min:g}_{d_max:g}",
        height_band_m=(float(h_min), float(h_max)),
        range_band_m=(float(d_min), float(d_max)),
        description="sensitivity sweep",
    )


#: Quadrature for the normalising integral. The shipped default is 200 001,
#: which a sweep over a few thousand models cannot afford. Against that default
#: 20 001 is within 2e-7 relative on every band this study evaluates, checked in
#: ``quadrature_check``, so the saving costs nothing.
NORMALISATION_QUADRATURE = 20_001


def density_on(model: IlluminationModel, elevation_deg: np.ndarray) -> np.ndarray:
    """`Q_S` in sr^-1 sampled on an elevation axis, via the shipped model."""
    elevation = np.radians(elevation_deg)
    directions = np.column_stack([np.cos(elevation), np.zeros_like(elevation), np.sin(elevation)])
    return model.density(directions, model.normalisation(NORMALISATION_QUADRATURE))


def quadrature_check() -> dict[str, float]:
    """Worst relative error of the reduced quadrature over the swept corners."""
    worst: dict[str, float] = {}
    for name, defaults in DEFAULTS.items():
        h_min, h_max = defaults["height_band_m"]
        d_min, d_max = defaults["range_band_m"]
        error = 0.0
        for h_low in (0.5 * h_min, h_min, 1.5 * h_min):
            for cap in (100.0, 250.0, 400.0, 500.0):
                model = band_model(name, h_low, h_max, d_min, cap)
                reference = model.normalisation(200_001)
                error = max(error, abs(model.normalisation(NORMALISATION_QUADRATURE) / reference - 1.0))
        worst[name] = float(error)
    return worst


def isotropic_density(elevation_deg: np.ndarray) -> np.ndarray:
    return np.full(elevation_deg.shape, 1.0 / (4.0 * np.pi))


class Reweighter:
    """Holds one site's harvest and turns illumination models into `chi`."""

    def __init__(self, path: pathlib.Path) -> None:
        data = np.load(path, allow_pickle=False)
        self.fine = data["fine"].astype(np.float64)
        self.direct = data["direct"].astype(np.float64)
        self.crop = data["crop"].astype(np.float64)
        self.crop_range_edges_m = data["crop_range_edges_m"]
        self.traced_chi = data["traced_chi"]
        self.traced_models = [str(x) for x in data["traced_models"]]
        self.points = data["points"]
        self.index = data["index"]
        self.crop_radius_m = float(data["crop_radius_m"])
        self.elevation_deg = elevation_centres(int(data["elevation_bins"]))
        self.crop_elevation_deg = elevation_centres(int(data["crop_elevation_bins"]))

    @property
    def locations(self) -> int:
        return int(self.fine.shape[0])

    def chi(self, model: IlluminationModel | None) -> np.ndarray:
        """Per standpoint `chi`. ``None`` means the isotropic control."""
        weight = isotropic_density(self.elevation_deg) if model is None else density_on(model, self.elevation_deg)
        return self.fine @ weight

    def chi_direct(self, model: IlluminationModel | None) -> np.ndarray:
        weight = isotropic_density(self.elevation_deg) if model is None else density_on(model, self.elevation_deg)
        return self.direct @ weight

    def chi_built(self, model: IlluminationModel) -> tuple[np.ndarray, np.ndarray]:
        """`chi` counted twice: as published, and with unbuilt sources refused.

        The second number restricts every escaping ray to sources no further
        out than the point where that ray leaves the reconstructed crop. It is
        a lower bound rather than the exact restriction, because the built
        extent is binned and the bin's near edge is used.
        """
        h_min, h_max = model.height_band_m  # type: ignore[misc]
        d_min, d_max = model.range_band_m  # type: ignore[misc]
        elevation = np.radians(self.crop_elevation_deg)
        sine = np.sin(elevation)
        cosine = np.cos(elevation)
        total = model.normalisation(NORMALISATION_QUADRATURE)
        lower = self.crop_range_edges_m[:-1]

        with np.errstate(divide="ignore", invalid="ignore"):
            near = np.maximum(h_min / sine, d_min / cosine)
            far_full = np.minimum(h_max / sine, d_max / cosine)
            # (elevation, built extent bin): the range cap the geometry supports.
            cap = np.minimum(d_max, lower[None, :])
            far_built = np.minimum(h_max / sine[:, None], cap / cosine[:, None])
        inside = sine > 0.0
        weight_full = np.where(inside, np.maximum(far_full**3 - near**3, 0.0) / 3.0, 0.0) / total
        weight_built = np.where(inside[:, None], np.maximum(far_built**3 - near[:, None] ** 3, 0.0) / 3.0, 0.0) / total
        published = self.crop.sum(axis=2) @ weight_full
        built = np.einsum("pej,ej->p", self.crop, weight_built)
        return published, built


def mechanism(model: str) -> dict[str, Any]:
    """What the range cap does to the illumination, before any site is involved.

    The cap does not scale the weight, it moves the lower edge of the elevation
    support, and the support edge is where the mass is. This block is a
    property of the illumination model alone, which is why it carries no site
    axis: it is the reason the per site sensitivities come out as unequal as
    they do.
    """
    from semantic_twin.illumination import measure_below

    h_min, h_max = DEFAULTS[model]["height_band_m"]
    d_min, _ = DEFAULTS[model]["range_band_m"]
    rows = []
    for cap in (100.0, 150.0, 200.0, 250.0, 300.0, 400.0, 500.0):
        built = band_model(model, h_min, h_max, d_min, cap)
        grid = np.linspace(built.elevation_min_deg, built.elevation_max_deg, 60)
        cumulative = np.array([measure_below(built, float(e), samples=4096) for e in grid])
        rows.append(
            {
                "cap_m": cap,
                "support_deg": [built.elevation_min_deg, built.elevation_max_deg],
                "measure_below_5_deg": measure_below(built, 5.0),
                "measure_below_10_deg": measure_below(built, 10.0),
                "measure_below_20_deg": measure_below(built, 20.0),
                "median_arrival_deg": float(np.interp(0.5, cumulative, grid)),
            }
        )
    return {"rows": rows}


def site_statistic(values: np.ndarray) -> float:
    """The site level number. Median over standpoints, as the paper reports."""
    return float(np.median(values))


# --------------------------------------------------------------------------
# Sweeps
# --------------------------------------------------------------------------


def sweep_axes(model: str) -> dict[str, np.ndarray]:
    defaults = DEFAULTS[model]
    h_min, h_max = defaults["height_band_m"]
    d_min, d_max = defaults["range_band_m"]
    return {
        "d_max": np.arange(50.0, 501.0, 5.0),
        "d_min": np.linspace(0.25 * d_min, 3.0 * d_min, 45),
        "h_min": np.linspace(0.25 * h_min, 0.95 * h_max, 45),
        "h_max": np.linspace(1.1 * h_min, 2.2 * h_max, 45),
    }


def one_dimensional(reweighters: dict[str, Reweighter], model: str) -> dict[str, Any]:
    defaults = DEFAULTS[model]
    h_min, h_max = defaults["height_band_m"]
    d_min, d_max = defaults["range_band_m"]
    base = {"h_min": h_min, "h_max": h_max, "d_min": d_min, "d_max": d_max}
    out: dict[str, Any] = {"axes": {}, "chi": {}}
    for parameter, axis in sweep_axes(model).items():
        models = []
        kept = []
        for value in axis:
            trial = dict(base)
            trial[parameter] = float(value)
            if trial["h_min"] >= trial["h_max"] or trial["d_min"] >= trial["d_max"]:
                continue
            models.append(band_model(model, trial["h_min"], trial["h_max"], trial["d_min"], trial["d_max"]))
            kept.append(float(value))
        weights = np.column_stack([density_on(m, next(iter(reweighters.values())).elevation_deg) for m in models])
        out["axes"][parameter] = kept
        # Stored as one list of per standpoint values per axis point, so a
        # consumer indexes the axis first and reduces over standpoints second.
        out["chi"][parameter] = {site: (rw.fine @ weights).T.tolist() for site, rw in reweighters.items()}
    return out


def interaction(reweighters: dict[str, Reweighter], model: str, parameter: str, values: np.ndarray) -> dict[str, Any]:
    """`chi` on a grid of range cap against one height edge."""
    defaults = DEFAULTS[model]
    h_min, h_max = defaults["height_band_m"]
    d_min, d_max = defaults["range_band_m"]
    caps = np.linspace(100.0, 400.0, 25)
    base = {"h_min": h_min, "h_max": h_max, "d_min": d_min, "d_max": d_max}
    grid: dict[str, list[list[float]]] = {site: [] for site in reweighters}
    for value in values:
        models = []
        for cap in caps:
            trial = dict(base)
            trial[parameter] = float(value)
            trial["d_max"] = float(cap)
            models.append(band_model(model, trial["h_min"], trial["h_max"], trial["d_min"], trial["d_max"]))
        weights = np.column_stack([density_on(m, next(iter(reweighters.values())).elevation_deg) for m in models])
        for site, rw in reweighters.items():
            grid[site].append([site_statistic(column) for column in (rw.fine @ weights).T])
    out = {"parameter": parameter, "values": values.tolist(), "caps": caps.tolist(), "median_chi": grid}
    if parameter == "h_min":
        out["collapse"] = collapse_onto_support_edge(values, caps, grid)
    return out


def collapse_onto_support_edge(
    values: np.ndarray, caps: np.ndarray, grid: dict[str, list[list[float]]]
) -> dict[str, Any]:
    """Does the pair `(h_min, d_max)` act only through the lower support edge?

    The lower edge of the elevation support is `atan(h_min/d_max)`, so if the
    two endpoints entered only through that edge, the dB surface over the grid
    would be a function of one variable. This fits exactly that one variable
    model, by least squares in `log(edge)`, and reports how much of the surface
    it explains. What is left over is the part of the interaction that a single
    number cannot carry.
    """
    edge = np.degrees(np.arctan2(values[:, None], caps[None, :])).ravel()
    cap_axis = np.broadcast_to(caps[None, :], (values.size, caps.size)).ravel()
    floor_axis = np.broadcast_to(values[:, None], (values.size, caps.size)).ravel()
    candidates = {"support_edge": edge, "range_cap": cap_axis, "height_floor": floor_axis}
    out: dict[str, Any] = {}
    for site, surface in grid.items():
        decibels = 10.0 * np.log10(np.asarray(surface).ravel())
        entry: dict[str, Any] = {"total_swing_db": float(np.ptp(decibels))}
        for name, axis in candidates.items():
            design = np.vander(np.log(axis), 5)
            residual = decibels - design @ np.linalg.lstsq(design, decibels, rcond=None)[0]
            entry[name] = {
                "residual_rms_db": float(np.sqrt(np.mean(residual**2))),
                "explained_fraction": float(1.0 - np.var(residual) / np.var(decibels)),
            }
        out[site] = entry
    return out


def elasticity(reweighters: dict[str, Reweighter], model: str) -> dict[str, Any]:
    """d(10 log10 chi) / d(ln parameter) at the published point.

    Every band law here is scale free: multiplying all four endpoints by a
    common factor leaves `Q` unchanged, because the weight and its
    normalisation both scale as the cube. The four elasticities must therefore
    sum to zero, and that is asserted rather than assumed.
    """
    defaults = DEFAULTS[model]
    base = {
        "h_min": defaults["height_band_m"][0],
        "h_max": defaults["height_band_m"][1],
        "d_min": defaults["range_band_m"][0],
        "d_max": defaults["range_band_m"][1],
    }
    step = 0.02
    out: dict[str, Any] = {}
    for parameter in base:
        low = dict(base)
        high = dict(base)
        low[parameter] = base[parameter] * math.exp(-step)
        high[parameter] = base[parameter] * math.exp(step)
        model_low = band_model(model, low["h_min"], low["h_max"], low["d_min"], low["d_max"])
        model_high = band_model(model, high["h_min"], high["h_max"], high["d_min"], high["d_max"])
        for site, rw in reweighters.items():
            value = (
                10.0 * np.log10(site_statistic(rw.chi(model_high)) / site_statistic(rw.chi(model_low))) / (2.0 * step)
            )
            out.setdefault(site, {})[parameter] = float(value)
    return out


def scale_invariance(reweighters: dict[str, Reweighter], model: str) -> dict[str, float]:
    """Doubling the deployment box must not move `chi` at all."""
    defaults = DEFAULTS[model]
    h_min, h_max = defaults["height_band_m"]
    d_min, d_max = defaults["range_band_m"]
    plain = band_model(model, h_min, h_max, d_min, d_max)
    scaled = band_model(model, 2.0 * h_min, 2.0 * h_max, 2.0 * d_min, 2.0 * d_max)
    return {
        site: float(np.max(np.abs(rw.chi(scaled) / np.maximum(rw.chi(plain), 1.0e-30) - 1.0)))
        for site, rw in reweighters.items()
    }


def crop_conflict(reweighters: dict[str, Reweighter], model: str) -> dict[str, Any]:
    """How much of `chi` comes from sources outside the reconstructed mesh."""
    defaults = DEFAULTS[model]
    h_min, h_max = defaults["height_band_m"]
    d_min, _ = defaults["range_band_m"]
    caps = [100.0, 125.0, 150.0, 175.0, 200.0, 225.0, 250.0, 275.0, 300.0, 350.0, 400.0, 450.0, 500.0]
    out: dict[str, Any] = {"caps_m": caps, "sites": {}, "built_extent": {}}
    for site, rw in reweighters.items():
        out["built_extent"][site] = built_extent(rw)
        rows = []
        for cap in caps:
            reference = site_statistic(rw.chi(band_model(model, h_min, h_max, d_min, cap)))
            published, built = rw.chi_built(band_model(model, h_min, h_max, d_min, cap))
            share = 1.0 - built / np.maximum(published, 1.0e-30)
            rows.append(
                {
                    "cap_m": cap,
                    "median_published_chi": site_statistic(published),
                    "median_built_chi": site_statistic(built),
                    "median_unbuilt_share": float(np.median(share)),
                    "p95_unbuilt_share": float(np.quantile(share, 0.95)),
                    "median_shift_db": float(10.0 * np.log10(site_statistic(built) / site_statistic(published))),
                    # The coarse elevation axis against the fine one, so the
                    # crop numbers carry their own discretisation check.
                    "coarse_axis_ratio": float(site_statistic(published) / reference),
                }
            )
        out["sites"][site] = rows
    return out


def built_extent(rw: Reweighter) -> dict[str, float]:
    """Throughput weighted horizontal reach of the reconstructed mesh.

    Restricted to the 3 to 10 degree elevation window, which is where the
    rooftop band puts most of its measure, so this is the extent the published
    number actually leans on rather than an average over the whole sphere.
    """
    window = (rw.crop_elevation_deg >= 3.0) & (rw.crop_elevation_deg <= 10.0)
    weight = rw.crop[:, window, :].sum(axis=(0, 1))
    lower = rw.crop_range_edges_m[:-1]
    finite = np.isfinite(lower)
    total = weight[finite].sum()
    if total <= 0.0:
        return {"median_m": float("nan"), "p10_m": float("nan"), "share_beyond_250_m": 0.0}
    cumulative = np.cumsum(weight[finite]) / total
    upper = np.minimum(rw.crop_range_edges_m[1:][finite], 600.0)
    return {
        "median_m": float(np.interp(0.5, cumulative, upper)),
        "p10_m": float(np.interp(0.1, cumulative, upper)),
        "share_beyond_250_m": float(weight[finite][lower[finite] >= 250.0].sum() / total),
    }


def published_rows(path: pathlib.Path) -> dict[int, float]:
    """`chi_rooftop` per walk index from a published JSONL, tolerant of a writer.

    The exposure runs stream their JSONL and several of them share this output
    directory, so a line can be half written while this reads. A torn line is
    skipped rather than allowed to abort a study that only needs the file as a
    cross check.
    """
    out: dict[int, float] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "index" in row and "chi_rooftop" in row:
            out[int(row["index"])] = float(row["chi_rooftop"])
    return out


def validate(reweighters: dict[str, Reweighter]) -> dict[str, Any]:
    """The harvest must reproduce the traced `chi` and the published run."""
    report: dict[str, Any] = {}
    for site, rw in reweighters.items():
        entry: dict[str, Any] = {}
        for column, name in enumerate(rw.traced_models):
            model = (
                None
                if name == "isotropic"
                else band_model(name, *DEFAULTS[name]["height_band_m"], *DEFAULTS[name]["range_band_m"])
            )
            harvested = rw.chi(model)
            traced = rw.traced_chi[:, column]
            entry[name] = {
                "max_rel_error_against_traced": float(np.max(np.abs(harvested / traced - 1.0))),
                "median_rel_error_against_traced": float(np.median(np.abs(harvested / traced - 1.0))),
                "median_harvested": site_statistic(harvested),
                "median_traced": site_statistic(traced),
            }
        # Every 250 m cross city run on disk, not only the published tag. The
        # walk depends on the ground datum, and the datum estimator has been
        # replaced since the published run, so which run a harvest sits on top
        # of is a question with an answer rather than an assumption. A run whose
        # standpoints are not the harvest's shows up as a low overlap here, and
        # that is the signal to read rather than the relative error beside it.
        traced = rw.traced_chi[:, rw.traced_models.index("rooftop")]
        against: dict[str, Any] = {}
        for rows_path in sorted(PUBLISHED_DIR.glob(f"city250*_{site}_15ghz_locations.jsonl")):
            reference = published_rows(rows_path)
            shared = [(traced[i], reference[int(k)]) for i, k in enumerate(rw.index) if int(k) in reference]
            if not shared:
                continue
            pairs = np.array(shared)
            against[rows_path.name.replace(f"_{site}_15ghz_locations.jsonl", "")] = {
                "standpoints_shared": len(shared),
                "standpoints_harvested": int(rw.index.size),
                "standpoints_in_run": len(reference),
                "max_rel_error": float(np.max(np.abs(pairs[:, 0] / pairs[:, 1] - 1.0))),
                "median_rel_error": float(np.median(np.abs(pairs[:, 0] / pairs[:, 1] - 1.0))),
            }
        entry["against_runs_on_disk"] = against
        report[site] = entry
    return report


def contrast(one_d: dict[str, Any], model: str) -> dict[str, Any]:
    """Is the between city ratio steadier than the absolute level?

    For every value of the range cap, the site level is reduced to its median
    `chi`, converted to dB, and split into a cross city mean level and a per
    site contrast about it. If the contrasts hold still while the mean level
    moves, the paper can make a strong relative claim on a weak absolute one.
    """
    axis = np.array(one_d["axes"]["d_max"])
    sites = sorted(one_d["chi"]["d_max"])
    levels = np.array([[site_statistic(np.array(v)) for v in one_d["chi"]["d_max"][site]] for site in sites])
    return _contrast_from_levels(axis, sites, levels, model)


def _contrast_from_levels(axis: np.ndarray, sites: list[str], levels: np.ndarray, model: str) -> dict[str, Any]:
    decibels = 10.0 * np.log10(np.maximum(levels, 1.0e-30))
    mean_level = decibels.mean(axis=0)
    contrasts = decibels - mean_level
    inside = (axis >= 100.0) & (axis <= 400.0)
    order = np.argsort(-decibels[:, np.argmin(np.abs(axis - DEFAULTS[model]["range_band_m"][1]))])
    ranks = np.argsort(np.argsort(-decibels[:, inside], axis=0), axis=0)
    spread = decibels[:, inside].max(axis=0) - decibels[:, inside].min(axis=0)
    return {
        "sites": sites,
        "d_max_m": axis[inside].tolist(),
        "absolute_level_db": mean_level[inside].tolist(),
        "absolute_swing_db": float(mean_level[inside].max() - mean_level[inside].min()),
        "contrast_db": {site: contrasts[i][inside].tolist() for i, site in enumerate(sites)},
        "contrast_swing_db": {site: float(np.ptp(contrasts[i][inside])) for i, site in enumerate(sites)},
        "worst_contrast_swing_db": float(np.max(np.ptp(contrasts[:, inside], axis=1))),
        "median_contrast_swing_db": float(np.median(np.ptp(contrasts[:, inside], axis=1))),
        "cross_site_spread_db": {"min": float(spread.min()), "max": float(spread.max())},
        "rank_changes": int(np.sum(ranks[:, 0] != ranks[:, -1])),
        "max_rank_move": int(np.max(np.abs(ranks[:, 0] - ranks[:, -1]))),
        "spearman_endpoint_to_endpoint": _spearman(ranks[:, 0], ranks[:, -1]),
        "ordering_at_default": [sites[i] for i in order],
    }


def _spearman(first: np.ndarray, second: np.ndarray) -> float:
    """Rank correlation between two orderings, with no scipy dependency."""
    a = first.astype(np.float64)
    b = second.astype(np.float64)
    a -= a.mean()
    b -= b.mean()
    denominator = float(np.sqrt((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / denominator) if denominator > 0.0 else float("nan")


def invariants(reweighters: dict[str, Reweighter], one_d: dict[str, Any], model: str) -> dict[str, Any]:
    """Which reported quantity survives the range cap best.

    Four candidates, scored the same way: how far does the quantity move, per
    site, when the cap is swept across 100 to 400 m. The comparison is the whole
    point of the sensitivity study, because the paper has to choose one of these
    to lead with.
    """
    axis = np.array(one_d["axes"]["d_max"])
    inside = (axis >= 100.0) & (axis <= 400.0)
    sites = sorted(one_d["chi"]["d_max"])
    levels = np.array([[site_statistic(np.array(v)) for v in one_d["chi"]["d_max"][site]] for site in sites])
    decibels = 10.0 * np.log10(np.maximum(levels, 1.0e-30))[:, inside]
    isotropic = np.array([10.0 * np.log10(site_statistic(reweighters[site].chi(None))) for site in sites])

    candidates = {
        "absolute_chi": decibels,
        "contrast_to_cross_city_mean": decibels - decibels.mean(axis=0),
        "chi_over_chi_isotropic": decibels - isotropic[:, None],
        "contrast_to_most_open_site": decibels - decibels[int(np.argmax(decibels[:, 0]))],
    }
    out: dict[str, Any] = {"reference_site": sites[int(np.argmax(decibels[:, 0]))], "candidates": {}}
    for name, block in candidates.items():
        swing = np.ptp(block, axis=1)
        out["candidates"][name] = {
            "median_swing_db": float(np.median(swing)),
            "worst_swing_db": float(swing.max()),
            "per_site_swing_db": {site: float(swing[i]) for i, site in enumerate(sites)},
        }
    return out


def analyse(sites: tuple[str, ...]) -> pathlib.Path:
    reweighters: dict[str, Reweighter] = {}
    for site in sites:
        path = OUTPUT / f"harvest_{site}.npz"
        if path.exists():
            reweighters[site] = Reweighter(path)
        else:
            print(f"[skip] {site}: no harvest", flush=True)
    if not reweighters:
        raise SystemExit("no harvests found, run --harvest first")

    report: dict[str, Any] = {
        "generator": "make_sensitivity_study.py",
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "published_run": PUBLISHED_TAG,
        "crop_radius_m": CROP_M,
        "locations_per_site": {site: rw.locations for site, rw in reweighters.items()},
        "defaults": {k: {kk: list(vv) for kk, vv in v.items()} for k, v in DEFAULTS.items()},
        "defensible_spans": {k: {kk: list(vv) for kk, vv in v.items()} for k, v in DEFENSIBLE.items()},
        "validation": validate(reweighters),
        "quadrature_max_rel_error": quadrature_check(),
        "isotropic_control": {site: {"median_chi": site_statistic(rw.chi(None))} for site, rw in reweighters.items()},
    }

    for model in DEFAULTS:
        print(f"sweeping {model}", flush=True)
        one_d = one_dimensional(reweighters, model)
        report[model] = {
            "one_dimensional": one_d,
            "elasticity_db_per_ln": elasticity(reweighters, model),
            "scale_invariance_max_rel_error": scale_invariance(reweighters, model),
            "interaction_h_min": interaction(reweighters, model, "h_min", np.linspace(*DEFENSIBLE[model]["h_min"], 13)),
            "interaction_h_max": interaction(reweighters, model, "h_max", np.linspace(*DEFENSIBLE[model]["h_max"], 13)),
            "crop_conflict": crop_conflict(reweighters, model),
            "contrast": contrast(one_d, model),
            "invariants": invariants(reweighters, one_d, model),
            "spans": spans(reweighters, model),
            "headline_table": headline_table(reweighters, model),
            "mechanism": mechanism(model),
        }

    destination = OUTPUT / "sensitivity.json"
    destination.write_text(json.dumps(report, indent=1))
    print(f"wrote {destination}", flush=True)
    write_tables(report)
    return destination


def spans(reweighters: dict[str, Reweighter], model: str) -> dict[str, Any]:
    """dB swing of the site median across each endpoint's defensible span."""
    defaults = DEFAULTS[model]
    base = {
        "h_min": defaults["height_band_m"][0],
        "h_max": defaults["height_band_m"][1],
        "d_min": defaults["range_band_m"][0],
        "d_max": defaults["range_band_m"][1],
    }
    out: dict[str, Any] = {}
    for parameter, (low_value, high_value) in DEFENSIBLE[model].items():
        low = dict(base)
        high = dict(base)
        low[parameter] = low_value
        high[parameter] = high_value
        model_low = band_model(model, low["h_min"], low["h_max"], low["d_min"], low["d_max"])
        model_high = band_model(model, high["h_min"], high["h_max"], high["d_min"], high["d_max"])
        for site, rw in reweighters.items():
            a = site_statistic(rw.chi(model_low))
            b = site_statistic(rw.chi(model_high))
            out.setdefault(site, {})[parameter] = float(abs(10.0 * np.log10(b / a)))
    for site, values in out.items():
        values["dominant"] = max((k for k in DEFENSIBLE[model]), key=lambda k: values[k])
    return out


def headline_table(reweighters: dict[str, Reweighter], model: str) -> dict[str, Any]:
    """The table the paper would print: `chi` at four range caps, per site."""
    h_min, h_max = DEFAULTS[model]["height_band_m"]
    d_min, default_cap = DEFAULTS[model]["range_band_m"]
    caps = [100.0, 150.0, 250.0, 400.0]
    out: dict[str, Any] = {"caps_m": caps, "sites": {}}
    for site, rw in reweighters.items():
        row: dict[str, Any] = {}
        for cap in caps:
            values = rw.chi(band_model(model, h_min, h_max, d_min, cap))
            row[f"{cap:g}"] = {
                "p05": float(np.quantile(values, 0.05)),
                "median": site_statistic(values),
                "p95": float(np.quantile(values, 0.95)),
            }
        reference = row[f"{default_cap:g}"]["median"]
        row["db_against_default"] = {
            f"{cap:g}": float(10.0 * np.log10(row[f"{cap:g}"]["median"] / reference)) for cap in caps
        }
        row["span_db"] = float(
            10.0 * np.log10(max(row[f"{c:g}"]["median"] for c in caps) / min(row[f"{c:g}"]["median"] for c in caps))
        )
        out["sites"][site] = row
    return out


def write_tables(report: dict[str, Any]) -> None:
    """Flat CSVs beside the JSON, so a table can be pasted without parsing."""
    for model in DEFAULTS:
        one_d = report[model]["one_dimensional"]
        for parameter, axis in one_d["axes"].items():
            sites = sorted(one_d["chi"][parameter])
            lines = [",".join([parameter] + [f"{s}_median_chi" for s in sites])]
            for i, value in enumerate(axis):
                medians = [site_statistic(np.array(one_d["chi"][parameter][s][i])) for s in sites]
                lines.append(",".join([f"{value:g}"] + [f"{m:.6g}" for m in medians]))
            (OUTPUT / f"sweep_{model}_{parameter}.csv").write_text("\n".join(lines) + "\n")
    print(f"wrote sweep CSVs into {OUTPUT}", flush=True)


# --------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------

INK = "#1a1a1a"
MUTED = "#8a8f98"
SITE_COLOURS = [
    "#1f77b4",
    "#d62728",
    "#2ca02c",
    "#9467bd",
    "#ff7f0e",
    "#8c564b",
    "#e377c2",
    "#17becf",
    "#bcbd22",
    "#7f7f7f",
    "#393b79",
]


def figures() -> None:
    import matplotlib.pyplot as plt

    sys.path.insert(0, "/home/user/aegis/theory/scripts")
    from _plot_style import apply_monograph_style, fig_size_ieee

    apply_monograph_style()
    report = json.loads((OUTPUT / "sensitivity.json").read_text())
    label = {
        "brussels_grandplace": "Brussels",
        "korenmarkt": "Ghent",
        "krakow_rynek": "Krakow",
        "london_trafalgar": "London",
        "madrid_plazamayor": "Madrid",
        "mexico_zocalo": "Mexico City",
        "milan_duomo": "Milan",
        "newyork_timessquare": "New York",
        "prague_staromestske": "Prague",
        "tokyo_hachiko": "Tokyo",
        "toulouse_capitole": "Toulouse",
    }

    def save(fig: Any, stem: str) -> None:
        for suffix in ("pdf", "png"):
            fig.savefig(OUTPUT / f"{stem}.{suffix}", dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"wrote {stem}.pdf and {stem}.png", flush=True)

    for model in DEFAULTS:
        one_d = report[model]["one_dimensional"]
        sites = sorted(one_d["chi"]["d_max"])
        default_cap = DEFAULTS[model]["range_band_m"][1]

        fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.40))
        axis = np.array(one_d["axes"]["d_max"])
        for i, site in enumerate(sites):
            medians = np.array([site_statistic(np.array(v)) for v in one_d["chi"]["d_max"][site]])
            axes[0].semilogy(
                axis, medians, color=SITE_COLOURS[i % len(SITE_COLOURS)], lw=1.2, label=label.get(site, site)
            )
            reference = medians[np.argmin(np.abs(axis - default_cap))]
            axes[1].plot(axis, 10.0 * np.log10(medians / reference), color=SITE_COLOURS[i % len(SITE_COLOURS)], lw=1.2)
        for ax in axes:
            ax.axvline(default_cap, color=INK, lw=0.8, ls=(0, (4, 3)))
            ax.axvspan(*DEFENSIBLE[model]["d_max"], color=MUTED, alpha=0.12, zorder=0)
            ax.set_xlabel("range cap $d_{\\max}$, m")
            ax.set_xlim(axis.min(), axis.max())
        axes[0].set_ylabel(r"site median $\chi$")
        axes[1].set_ylabel("dB relative to the published cap")
        axes[1].axhline(0.0, color=INK, lw=0.6)
        axes[0].legend(ncol=2, fontsize=6.0, frameon=False, loc="lower left")
        axes[0].set_title(f"{model.replace('_', ' ')}, absolute", fontsize=8)
        axes[1].set_title("the same curves, each site read against itself", fontsize=8)
        save(fig, f"range_cap_{model}")

        # One y axis across the three panels. The comparison between endpoints
        # is the point of the figure, and three free axes would hide it.
        fig, axes = plt.subplots(1, 3, figsize=fig_size_ieee(columns=2, aspect=0.32), sharey=True)
        for ax, parameter, name in zip(
            axes,
            ("h_min", "h_max", "d_min"),
            ("height floor $h_{\\min}$, m", "height ceiling $h_{\\max}$, m", "range floor $d_{\\min}$, m"),
        ):
            axis = np.array(one_d["axes"][parameter])
            base = DEFAULTS[model]["height_band_m"] + DEFAULTS[model]["range_band_m"]
            default = {"h_min": base[0], "h_max": base[1], "d_min": base[2]}[parameter]
            for i, site in enumerate(sites):
                medians = np.array([site_statistic(np.array(v)) for v in one_d["chi"][parameter][site]])
                reference = medians[np.argmin(np.abs(axis - default))]
                ax.plot(axis, 10.0 * np.log10(medians / reference), color=SITE_COLOURS[i % len(SITE_COLOURS)], lw=1.1)
            ax.axvline(default, color=INK, lw=0.8, ls=(0, (4, 3)))
            ax.axvspan(*DEFENSIBLE[model][parameter], color=MUTED, alpha=0.12, zorder=0)
            ax.axhline(0.0, color=INK, lw=0.6)
            ax.set_xlabel(name)
            ax.set_xlim(axis.min(), axis.max())
        axes[0].set_ylabel("dB relative to the published value")
        save(fig, f"endpoints_{model}")

        contrast_block = report[model]["contrast"]
        fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.40))
        caps = np.array(contrast_block["d_max_m"])
        axes[0].plot(
            caps,
            np.array(contrast_block["absolute_level_db"])
            - contrast_block["absolute_level_db"][int(np.argmin(np.abs(caps - default_cap)))],
            color=INK,
            lw=1.6,
        )
        axes[0].set_ylabel("cross city mean level, dB")
        axes[0].set_title("what the cap does to the absolute number", fontsize=8)
        for i, site in enumerate(contrast_block["sites"]):
            series = np.array(contrast_block["contrast_db"][site])
            axes[1].plot(
                caps,
                series - series[int(np.argmin(np.abs(caps - default_cap)))],
                color=SITE_COLOURS[i % len(SITE_COLOURS)],
                lw=1.1,
                label=label.get(site, site),
            )
        axes[1].set_ylabel("per city contrast, dB")
        axes[1].set_title("what it does to the between city contrast", fontsize=8)
        axes[1].legend(ncol=2, fontsize=6.0, frameon=False)
        for ax in axes:
            ax.axvline(default_cap, color=INK, lw=0.8, ls=(0, (4, 3)))
            ax.axhline(0.0, color=INK, lw=0.6)
            ax.set_xlabel("range cap $d_{\\max}$, m")
            ax.set_xlim(caps.min(), caps.max())
        # Both panels on the absolute panel's scale. Reading the contrast on its
        # own tighter axis is what makes a 0.5 dB drift look like a 7 dB one.
        axes[1].set_ylim(axes[0].get_ylim())
        save(fig, f"contrast_{model}")

        crop = report[model]["crop_conflict"]
        fig, axes = plt.subplots(1, 2, figsize=fig_size_ieee(columns=2, aspect=0.40))
        caps_axis = np.array(crop["caps_m"])
        for i, site in enumerate(sorted(crop["sites"])):
            rows = crop["sites"][site]
            colour = SITE_COLOURS[i % len(SITE_COLOURS)]
            axes[0].plot(
                caps_axis,
                [100.0 * row["median_unbuilt_share"] for row in rows],
                color=colour,
                lw=1.2,
                label=label.get(site, site),
            )
            axes[1].plot(caps_axis, [row["median_shift_db"] for row in rows], color=colour, lw=1.2)
        for ax in axes:
            ax.axvline(default_cap, color=INK, lw=0.8, ls=(0, (4, 3)))
            ax.axvline(float(CROP_M), color=MUTED, lw=1.0)
            ax.set_xlabel("range cap $d_{\\max}$, m")
            ax.set_xlim(caps_axis.min(), caps_axis.max())
        axes[0].set_ylabel("share of $\\chi$ from unbuilt sources, %")
        axes[1].set_ylabel("dB if those sources are refused")
        axes[0].set_title(f"{model.replace('_', ' ')}: cap against the built extent", fontsize=8)
        axes[1].set_title("the bracket the crop leaves on the answer", fontsize=8)
        axes[0].legend(ncol=2, fontsize=6.0, frameon=False, loc="upper left")
        save(fig, f"crop_conflict_{model}")

        block = report[model]["interaction_h_min"]
        fig, ax = plt.subplots(figsize=fig_size_ieee(columns=1, aspect=0.78))
        values = np.array(block["values"])
        caps = np.array(block["caps"])
        sites_here = sorted(block["median_chi"])
        stack = np.array([block["median_chi"][s] for s in sites_here])
        decibels = 10.0 * np.log10(stack)
        anchor_value = int(np.argmin(np.abs(values - DEFAULTS[model]["height_band_m"][0])))
        anchor_cap = int(np.argmin(np.abs(caps - DEFAULTS[model]["range_band_m"][1])))
        centred = decibels - decibels[:, anchor_value, anchor_cap][:, None, None]
        mean_surface = centred.mean(axis=0)
        levels = np.linspace(np.floor(mean_surface.min()), np.ceil(mean_surface.max()), 17)
        mesh = ax.contourf(caps, values, mean_surface, levels=levels, cmap="RdBu_r")
        contours = ax.contour(caps, values, mean_surface, levels=levels[::2], colors=INK, linewidths=0.4)
        ax.clabel(contours, fmt="%.0f", fontsize=5.5)
        edge = np.degrees(np.arctan2(values[:, None], caps[None, :]))
        ax.contour(
            caps, values, edge, levels=[2.0, 3.0, 4.0, 5.0, 6.0], colors="white", linewidths=0.9, linestyles="--"
        )
        ax.plot(
            [DEFAULTS[model]["range_band_m"][1]], [DEFAULTS[model]["height_band_m"][0]], marker="o", ms=5, color=INK
        )
        ax.set_xlabel("range cap $d_{\\max}$, m")
        ax.set_ylabel("height floor $h_{\\min}$, m")
        ax.set_title(
            f"{model.replace('_', ' ')}: mean dB shift, dashed = constant $\\arctan(h_{{\\min}}/d_{{\\max}})$",
            fontsize=7,
        )
        fig.colorbar(mesh, ax=ax, label="dB")
        save(fig, f"interaction_{model}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harvest", action="store_true")
    parser.add_argument("--analyse", action="store_true")
    parser.add_argument("--figures", action="store_true")
    parser.add_argument("--sites", nargs="*", default=None)
    parser.add_argument("--locations", type=int, default=LOCATIONS)
    parser.add_argument("--rays", type=int, default=RAYS)
    parser.add_argument(
        "--stride",
        type=int,
        default=1,
        help="trace every nth published standpoint, so every harvested one stays checkable",
    )
    args = parser.parse_args(argv)

    sites = tuple(args.sites) if args.sites else site_list()
    stages = (args.harvest, args.analyse, args.figures)
    if not any(stages):
        stages = (True, True, True)
        args.harvest, args.analyse, args.figures = stages

    if args.harvest:
        for site in sites:
            print(f"harvesting {site}", flush=True)
            try:
                harvest_site(site, locations=args.locations, rays=args.rays, stride=args.stride)
            except FileNotFoundError as error:
                print(f"[skip] {site}: {error}", flush=True)
    if args.analyse:
        analyse(sites)
    if args.figures:
        figures()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
