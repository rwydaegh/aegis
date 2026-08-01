"""Refine Street View pose by matching its segmented skyline to the tile mesh.

Inhouse metadata gives a strong horizontal/orientation prior but no altitude. This
optimizer compares the panorama's sky boundary with the angular envelope of the
photogrammetry vertices. Ground-level tile noise is therefore absent from the
objective, which is the reason skyline registration is preferred here.

Three properties of the objective decide what the output means, and all three
were measured rather than assumed.

First, the mesh skyline is a biased estimate of the true skyline, and the bias is
mostly the estimator's own fault. The photogrammetry rounds off balustrades,
chimneys and pinnacle tips, and the azimuthal median filter that rejects wire
spikes also shaves every convex roof peak. Both push the modelled skyline down,
and the optimiser buys residual back by sinking the camera. At the camera's
measured altitude the observed skyline sat 3.83 degrees above the modelled one at
Korenmarkt and 1.56 at Milan under the median filter, falling to 1.11 and 0.52
under an upper quantile. ``smoothing_percentile`` is that knob and it is why the
dz bound stopped being load-bearing.

Second, a residual elevation bias and a camera altitude offset are degenerate. A
roofline too low by ``d`` metres and a camera too high by ``d`` metres produce the
same angular error ``d cos^2(e) / R`` at every azimuth. Fitting both at
Korenmarkt traces a straight valley at 1.47 degrees of bias per metre of altitude
along which three metres of altitude cost 0.05 degrees of residual, so the bias
term is a diagnostic and the altitude is measured against the support mesh
instead of being inferred.

Third, the reported residual is not an error bar. Every pose therefore ships with
an ensemble covariance over independent optimiser seeds. The sky-conflict metric
is the one check that does not use this objective at all.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import percentile_filter
from scipy.optimize import differential_evolution, minimize

from .pano_geometry import (
    directions_to_equirectangular,
    equirectangular_directions,
    panorama_to_world_matrix,
    streetview_orientation_prior,
)
from .support_mesh import first_hit_range, ground_elevation, read_binary_ply, read_binary_ply_vertices

PARAMETER_NAMES = ("dx_m", "dy_m", "dz_m", "yaw_deg", "pitch_delta_deg", "roll_delta_deg")
BIAS_NAME = "skyline_bias_deg"
DEFAULT_SEEDS = (0xAE615, 1, 2, 3, 5, 8, 13, 21)
STRUCTURAL_LABELS = frozenset({"building", "wall", "bridge", "tunnel"})

__all__ = [
    "SkylineEnsemble",
    "SkylineFit",
    "SkylineSettings",
    "SkyConflict",
    "candidate_vertices",
    "ensemble_covariance",
    "fit_pose",
    "mesh_skyline",
    "observed_skyline",
    "profile_intervals",
    "read_binary_ply_vertices",
    "seed_study",
    "sky_conflict",
    "skyline_cost",
]


@dataclass(frozen=True)
class SkylineSettings:
    """Everything that decides what the skyline objective measures.

    ``smoothing_percentile`` is the one knob with a physical meaning. 50
    reproduces the azimuthal median filter, which rejects isolated wire spikes but
    also shaves convex roof peaks and is what pinned the altitude against its
    search bound. The default of 90 keeps the second highest of eleven
    neighbouring bins, so a spike narrower than two bins is still rejected while
    a chimney or balustrade several bins wide survives. ``robust_quantile`` is
    the fraction of skyline samples allowed to dominate the mean before their
    residual is clipped, which is what keeps trees and cranes from steering the
    fit.
    """

    n_bins: int = 1024
    minimum_distance_m: float = 8.0
    smoothing_size: int = 11
    smoothing_percentile: float = 90.0
    robust_quantile: float = 0.8
    orientation_prior_weight: float = 0.001

    def __post_init__(self) -> None:
        if self.n_bins < 16:
            raise ValueError("n_bins must be at least 16")
        if self.smoothing_size < 1 or self.smoothing_size % 2 == 0:
            raise ValueError("smoothing_size must be a positive odd number of bins")
        if not 0.0 < self.smoothing_percentile <= 100.0:
            raise ValueError("smoothing_percentile must lie in (0, 100]")
        if not 0.0 < self.robust_quantile <= 1.0:
            raise ValueError("robust_quantile must lie in (0, 1]")


@dataclass(frozen=True)
class SkylineFit:
    """One optimiser run, with enough state to say whether it actually converged."""

    params: np.ndarray
    cost: float
    residual_deg: float
    bias_deg: float
    seed: int
    n_iterations: int
    n_evaluations: int
    converged: bool
    dz_bounds_m: tuple[float, float]

    def as_dict(self) -> dict[str, Any]:
        record: dict[str, Any] = {"seed": self.seed}
        record.update({name: float(value) for name, value in zip(PARAMETER_NAMES, self.params, strict=False)})
        record.update(
            {
                BIAS_NAME: self.bias_deg,
                "residual_deg": self.residual_deg,
                "n_iterations": self.n_iterations,
                "n_evaluations": self.n_evaluations,
                "converged": self.converged,
            }
        )
        return record


@dataclass(frozen=True)
class SkylineEnsemble:
    """Repeated independent seeds on the same data, and the spread they expose.

    The covariance is the width of the cost valley sampled by a stochastic global
    optimiser, not a posterior from a noise model. It is reported because it is
    measurable and because it is the honest lower bound on how well a single
    panorama's skyline pins a pose.
    """

    fits: list[SkylineFit]
    best: SkylineFit
    covariance: np.ndarray
    names: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        samples = np.array([np.r_[fit.params, fit.bias_deg] for fit in self.fits])
        residuals = np.array([fit.residual_deg for fit in self.fits])
        return {
            "parameter_names": list(self.names),
            "covariance": self.covariance.tolist(),
            "standard_deviation": np.sqrt(np.diag(self.covariance)).tolist(),
            "mean": samples.mean(axis=0).tolist(),
            "min": samples.min(axis=0).tolist(),
            "max": samples.max(axis=0).tolist(),
            "residual_deg": {
                "mean": float(residuals.mean()),
                "std": float(residuals.std(ddof=1)) if residuals.size > 1 else 0.0,
                "min": float(residuals.min()),
                "max": float(residuals.max()),
            },
            "n_seeds": len(self.fits),
            "n_converged": sum(1 for fit in self.fits if fit.converged),
            "runs": [fit.as_dict() for fit in self.fits],
            "note": (
                "Covariance over independent optimiser seeds on identical data. It measures the width of the "
                "cost valley, not a formal pose posterior."
            ),
        }


@dataclass(frozen=True)
class SkyConflict:
    """Agreement between the segmented sky mask and the support-mesh silhouette.

    Independent of the skyline objective: it uses the whole two-dimensional mask
    including courtyard gaps, arcade openings and sky seen between towers, and it
    is a first-hit ray cast rather than a per-azimuth envelope. ``sky_with_mesh``
    is mesh where the image sees sky, and ``structure_without_mesh`` is the
    opposite error, so their balance says which way a misregistration points.

    ``sky_with_distant_mesh`` drops hits nearer than ``minimum_range_m``. That
    split matters because a photogrammetry tree canopy arching over the camera
    produces sky conflicts at a few metres that no pose can remove, and at
    Korenmarkt those are more than half the raw count.
    """

    sky_with_mesh: float
    sky_with_distant_mesh: float
    structure_without_mesh: float
    n_sky: int
    n_structure: int
    n_directions: int
    conflict_median_range_m: float
    settings: dict[str, Any] = field(default_factory=dict)

    @property
    def disagreement(self) -> float:
        """Both errors together, which is what tracks pose quality.

        Deliberately built on ``sky_with_mesh`` rather than the distant-only
        variant. A camera driven below the pavement puts every conflict within a
        metre, so a range-filtered term reads as a perfect score exactly where the
        pose is most wrong.
        """
        return self.sky_with_mesh + self.structure_without_mesh

    def as_dict(self) -> dict[str, Any]:
        return {
            "sky_with_mesh_hit_fraction": self.sky_with_mesh,
            "sky_with_distant_mesh_hit_fraction": self.sky_with_distant_mesh,
            "structure_without_mesh_hit_fraction": self.structure_without_mesh,
            "disagreement": self.disagreement,
            "n_sky_directions": self.n_sky,
            "n_structure_directions": self.n_structure,
            "n_directions": self.n_directions,
            "conflict_median_range_m": self.conflict_median_range_m,
            **self.settings,
        }


def observed_skyline(
    entity: np.ndarray,
    sky_id: int,
    n_bins: int,
    structural_ids: set[int] | None = None,
) -> np.ndarray:
    """Bottom edge of the top-connected sky, as panorama-local unit rays."""
    height, width = entity.shape
    columns = np.linspace(0, width - 1, n_bins, dtype=np.int32)
    sky = entity[:, columns] == sky_id
    limit = int(height * 0.72)
    rows = np.arange(limit)[:, None]
    # A pole or cable can punch a tiny hole in otherwise connected sky. The
    # bottommost sky pixel is robust to that and the median removes tree gaps.
    boundary = np.max(np.where(sky[:limit], rows, -1), axis=0)
    # A column with no sky at all has no skyline. Substituting a nominal row
    # would fabricate an observation, so those columns are dropped instead.
    has_sky = boundary >= 0
    boundary[~has_sky] = int(height * 0.25)
    boundary = percentile_filter(boundary.astype(float), 50, size=11, mode="wrap")
    if structural_ids:
        sample_row = np.clip(np.rint(boundary + max(2, height // 256)).astype(int), 0, height - 1)
        support = np.isin(entity[sample_row, columns], list(structural_ids)) & has_sky
    else:
        support = has_sky
    u = (columns + 0.5) / width
    v = (boundary + 0.5) / height
    yaw = (u - 0.5) * 2.0 * np.pi
    pitch = (0.5 - v) * np.pi
    cp = np.cos(pitch)
    rays = np.stack([np.sin(yaw) * cp, np.cos(yaw) * cp, np.sin(pitch)], axis=1)
    return rays[support]


def mesh_skyline(
    vertices: np.ndarray,
    camera: np.ndarray,
    n_bins: int,
    minimum_distance_m: float = 8.0,
    *,
    smoothing_size: int = 11,
    smoothing_percentile: float = 90.0,
) -> np.ndarray:
    """Angular upper envelope of the support mesh seen from ``camera``.

    The per-bin maximum is the silhouette. The azimuthal filter that follows is
    there to reject the thin wires and isolated high vertices the photogrammetry
    contains, and at ``smoothing_percentile = 50`` it is the shipped median
    filter. That filter is not neutral: a roofline is convex upward almost
    everywhere it matters, so a median over neighbouring azimuths systematically
    removes peaks. Raising the percentile keeps spike rejection while shrinking
    that bias.
    """
    delta = vertices - camera
    horizontal = np.hypot(delta[:, 0], delta[:, 1])
    keep = horizontal > minimum_distance_m
    azimuth = np.arctan2(delta[keep, 0], delta[keep, 1])
    elevation = np.arctan2(delta[keep, 2], horizontal[keep])
    bins = np.floor((azimuth / (2.0 * np.pi) + 0.5) * n_bins).astype(int) % n_bins
    skyline = np.full(n_bins, -np.pi / 2.0)
    np.maximum.at(skyline, bins, elevation)
    valid = skyline > -np.pi / 2.0
    if not np.all(valid):
        x = np.arange(n_bins)
        xp = x[valid]
        fp = skyline[valid]
        skyline = np.interp(x, np.r_[xp - n_bins, xp, xp + n_bins], np.tile(fp, 3))
    if smoothing_size <= 1:
        return skyline
    return percentile_filter(skyline, smoothing_percentile, size=smoothing_size, mode="wrap")


def candidate_vertices(
    vertices: np.ndarray,
    camera: np.ndarray,
    n_bins: int,
    minimum_distance_m: float = 8.0,
    *,
    margin_deg: float = 4.0,
    search_box_m: tuple[tuple[float, float], ...] | None = None,
    smoothing_size: int = 11,
    smoothing_percentile: float = 90.0,
) -> np.ndarray:
    """Retain geometry that can reach the skyline anywhere in the search box.

    Pruning at the initial camera alone is wrong as soon as the optimiser moves
    the camera, because a vertex hidden from the start position can become the
    silhouette from a metre away. The prune is therefore taken as the union over
    the corners and centre of the translation search box, which is the region the
    optimiser is allowed to explore.
    """
    corners: list[np.ndarray] = [np.zeros(3)]
    if search_box_m is not None:
        if len(search_box_m) != 3:
            raise ValueError("search_box_m must give a (low, high) pair for each of dx, dy and dz")
        axes = [np.array(bound, dtype=float) for bound in search_box_m]
        corners = [np.array([x, y, z]) for x in axes[0] for y in axes[1] for z in axes[2]]
        corners.append(np.zeros(3))
    keep = np.zeros(len(vertices), dtype=bool)
    for offset in corners:
        origin = np.asarray(camera, dtype=float) + offset
        delta = vertices - origin
        horizontal = np.hypot(delta[:, 0], delta[:, 1])
        near = horizontal > minimum_distance_m
        azimuth = np.arctan2(delta[:, 0], delta[:, 1])
        elevation = np.arctan2(delta[:, 2], np.maximum(horizontal, 1e-8))
        bins = np.floor((azimuth / (2.0 * np.pi) + 0.5) * n_bins).astype(int) % n_bins
        envelope = mesh_skyline(
            vertices,
            origin,
            n_bins,
            minimum_distance_m,
            smoothing_size=smoothing_size,
            smoothing_percentile=smoothing_percentile,
        )
        keep |= near & (elevation > envelope[bins] - np.radians(margin_deg))
    keep[::40] = True
    return vertices[keep]


def _predicted_and_observed(
    params: np.ndarray,
    *,
    vertices: np.ndarray,
    local_skyline: np.ndarray,
    position: np.ndarray,
    heading_deg: float,
    pitch_prior_deg: float,
    roll_prior_deg: float,
    settings: SkylineSettings,
) -> tuple[np.ndarray, np.ndarray]:
    """Modelled and observed elevation in radians at every skyline sample.

    One implementation, because the previous seed-study driver kept a second copy
    of this arithmetic and the two were free to drift apart.
    """
    dx, dy, dz, yaw, pitch_delta, roll_delta = params[:6]
    bias_deg = float(params[6]) if len(params) > 6 else 0.0
    model = mesh_skyline(
        vertices,
        position + np.array([dx, dy, dz]),
        settings.n_bins,
        settings.minimum_distance_m,
        smoothing_size=settings.smoothing_size,
        smoothing_percentile=settings.smoothing_percentile,
    )
    rotation = panorama_to_world_matrix(
        heading_deg + yaw,
        pitch_deg=pitch_prior_deg + pitch_delta,
        roll_deg=roll_prior_deg + roll_delta,
    )
    world = local_skyline @ rotation.T
    azimuth = np.arctan2(world[:, 0], world[:, 1])
    elevation = np.arcsin(np.clip(world[:, 2], -1.0, 1.0))
    index = ((azimuth / (2.0 * np.pi) + 0.5) * settings.n_bins) % settings.n_bins
    lo = np.floor(index).astype(int)
    hi = (lo + 1) % settings.n_bins
    frac = index - lo
    return model[lo] * (1.0 - frac) + model[hi] * frac + math.radians(bias_deg), elevation


def skyline_cost(params: np.ndarray, **kwargs: Any) -> float:
    """Robust mean angular skyline error in radians, plus the orientation prior.

    ``params`` is ``(dx, dy, dz, yaw, pitch_delta, roll_delta)`` and optionally a
    seventh elevation bias in degrees added to the modelled skyline. The remaining
    arguments are those of :func:`_predicted_and_observed`.
    """
    settings: SkylineSettings = kwargs["settings"]
    predicted, elevation = _predicted_and_observed(params, **kwargs)
    residual = np.abs(predicted - elevation)
    cutoff = np.quantile(residual, settings.robust_quantile)
    robust_error = np.mean(np.minimum(residual, cutoff))
    pitch_delta, roll_delta = params[4], params[5]
    orientation_prior = settings.orientation_prior_weight * ((pitch_delta / 3.0) ** 2 + (roll_delta / 3.0) ** 2)
    return float(robust_error + orientation_prior)


def signed_skyline_residual(params: np.ndarray, **kwargs: Any) -> np.ndarray:
    """Observed minus modelled elevation in radians, one entry per skyline sample.

    Positive means the image skyline sits above the mesh skyline, which is the
    direction the photogrammetry's rounded roof detail biases it.
    """
    predicted, elevation = _predicted_and_observed(params, **kwargs)
    return elevation - predicted


def _bounds(
    dz_bounds: tuple[float, float],
    *,
    translation_m: float,
    yaw_deg: float,
    orientation_deg: float,
    bias_bounds_deg: tuple[float, float] | None,
) -> list[tuple[float, float]]:
    bounds = [
        (-translation_m, translation_m),
        (-translation_m, translation_m),
        tuple(float(value) for value in dz_bounds),
        (-yaw_deg, yaw_deg),
        (-orientation_deg, orientation_deg),
        (-orientation_deg, orientation_deg),
    ]
    if bias_bounds_deg is not None:
        bounds.append(tuple(float(value) for value in bias_bounds_deg))
    return bounds  # type: ignore[return-value]


def fit_pose(
    vertices: np.ndarray,
    local_skyline: np.ndarray,
    position: np.ndarray,
    heading_deg: float,
    pitch_prior_deg: float,
    roll_prior_deg: float,
    *,
    settings: SkylineSettings | None = None,
    maxiter: int = 600,
    seed: int = 0xAE615,
    dz_bounds: tuple[float, float] = (-3.0, 3.0),
    translation_bound_m: float = 4.0,
    yaw_bound_deg: float = 20.0,
    orientation_bound_deg: float = 6.0,
    bias_bounds_deg: tuple[float, float] | None = None,
) -> SkylineFit:
    """Global fit of the skyline objective from one optimiser seed."""
    settings = settings or SkylineSettings()
    bounds = _bounds(
        dz_bounds,
        translation_m=translation_bound_m,
        yaw_deg=yaw_bound_deg,
        orientation_deg=orientation_bound_deg,
        bias_bounds_deg=bias_bounds_deg,
    )
    kwargs = {
        "vertices": vertices,
        "local_skyline": local_skyline,
        "position": position,
        "heading_deg": heading_deg,
        "pitch_prior_deg": pitch_prior_deg,
        "roll_prior_deg": roll_prior_deg,
        "settings": settings,
    }
    result = differential_evolution(
        lambda params: skyline_cost(params, **kwargs),
        bounds=bounds,
        seed=seed,
        popsize=7,
        maxiter=maxiter,
        polish=True,
        updating="immediate",
        # The relative convergence test never fires on a cost that approaches
        # zero, which is the synthetic case. This floor is far below the angular
        # resolution of any real skyline.
        atol=1e-7,
    )
    bias = float(result.x[6]) if bias_bounds_deg is not None else 0.0
    return SkylineFit(
        params=np.asarray(result.x[:6], dtype=float),
        cost=float(result.fun),
        residual_deg=float(np.degrees(result.fun)),
        bias_deg=bias,
        seed=int(seed),
        n_iterations=int(result.nit),
        n_evaluations=int(result.nfev),
        converged=bool(result.success) and int(result.nit) < maxiter,
        dz_bounds_m=(float(dz_bounds[0]), float(dz_bounds[1])),
    )


def ensemble_covariance(fits: list[SkylineFit]) -> np.ndarray:
    """Sample covariance of the fitted parameters across optimiser seeds."""
    samples = np.array([np.r_[fit.params, fit.bias_deg] for fit in fits])
    if len(samples) < 2:
        return np.zeros((samples.shape[1], samples.shape[1]))
    return np.cov(samples, rowvar=False)


def seed_study(
    vertices: np.ndarray,
    local_skyline: np.ndarray,
    position: np.ndarray,
    heading_deg: float,
    pitch_prior_deg: float,
    roll_prior_deg: float,
    *,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    progress: bool = False,
    **fit_kwargs: Any,
) -> SkylineEnsemble:
    """Repeat the fit from independent seeds and keep the spread as the error bar."""
    fits: list[SkylineFit] = []
    for seed in seeds:
        fit = fit_pose(
            vertices,
            local_skyline,
            position,
            heading_deg,
            pitch_prior_deg,
            roll_prior_deg,
            seed=seed,
            **fit_kwargs,
        )
        fits.append(fit)
        if progress:
            print(
                f"[seed {fit.seed:>7}] dz={fit.params[2]:+.3f} m yaw={fit.params[3]:+.3f} deg "
                f"bias={fit.bias_deg:+.3f} deg residual={fit.residual_deg:.3f} deg",
                flush=True,
            )
    best = min(fits, key=lambda fit: fit.cost)
    names = (*PARAMETER_NAMES, BIAS_NAME)
    return SkylineEnsemble(fits=fits, best=best, covariance=ensemble_covariance(fits), names=names)


def profile_intervals(
    best: np.ndarray,
    bounds: list[tuple[float, float]],
    *,
    tolerance_deg: float,
    steps: int = 9,
    **cost_kwargs: Any,
) -> dict[str, dict[str, float]]:
    """Per-axis profile: how far each parameter moves before the cost really rises.

    The other parameters are re-minimised at every scan point, so this is a
    profile rather than a slice and it reports the width of the valley the seed
    ensemble samples. ``tolerance_deg`` is the cost rise treated as insignificant.
    """
    tolerance = math.radians(tolerance_deg)
    reference = skyline_cost(best, **cost_kwargs)
    intervals: dict[str, dict[str, float]] = {}
    names = (*PARAMETER_NAMES, BIAS_NAME)
    for axis, (low, high) in enumerate(bounds):
        grid = np.linspace(low, high, steps)
        free = [index for index in range(len(best)) if index != axis]
        inside: list[float] = []
        for value in grid:

            def partial(reduced: np.ndarray, value: float = value, axis: int = axis, free: list[int] = free) -> float:
                trial = best.copy()
                trial[axis] = value
                trial[free] = reduced
                return skyline_cost(trial, **cost_kwargs)

            outcome = minimize(
                partial,
                best[free],
                method="Nelder-Mead",
                options={"xatol": 1e-3, "fatol": 1e-6, "maxiter": 600},
            )
            if float(outcome.fun) - reference <= tolerance:
                inside.append(float(value))
        intervals[names[axis]] = {
            "best": float(best[axis]),
            "low": float(min(inside)) if inside else float(best[axis]),
            "high": float(max(inside)) if inside else float(best[axis]),
            "half_width": (float(max(inside)) - float(min(inside))) / 2.0 if len(inside) > 1 else 0.0,
            "reached_bound": bool(inside) and (min(inside) <= low + 1e-9 or max(inside) >= high - 1e-9),
        }
    intervals["_tolerance_deg"] = {
        "value": float(tolerance_deg),
        "reference_residual_deg": float(np.degrees(reference)),
    }
    return intervals


def sky_conflict(
    vertices: np.ndarray,
    faces: np.ndarray,
    entity: np.ndarray,
    sky_id: int,
    structural_ids: set[int],
    camera: np.ndarray,
    *,
    heading_deg: float,
    pitch_deg: float,
    roll_deg: float,
    width: int = 512,
    height: int = 256,
    min_elevation_deg: float = -60.0,
    minimum_range_m: float = 8.0,
) -> SkyConflict:
    """Compare the segmented sky mask with the support-mesh silhouette.

    This is the second opinion: it never touches the skyline objective, uses the
    full two-dimensional mask rather than one boundary per azimuth, and asks a
    first-hit ray cast whether geometry stands where the image sees sky. Rays
    below ``min_elevation_deg`` are dropped because the camera rig and the road
    surface directly under the vehicle are not a registration signal.
    """
    directions = equirectangular_directions(width, height)
    rotation = panorama_to_world_matrix(heading_deg, pitch_deg=pitch_deg, roll_deg=roll_deg)
    world = directions.reshape(-1, 3) @ rotation.T
    elevation_deg = np.degrees(np.arcsin(np.clip(world[:, 2], -1.0, 1.0)))
    usable = elevation_deg >= min_elevation_deg
    ranges = np.full(len(world), np.nan)
    ranges[usable] = first_hit_range(vertices, faces, np.asarray(camera, dtype=float), world[usable])

    rows = np.clip((np.arange(height) + 0.5) / height * entity.shape[0], 0, entity.shape[0] - 1).astype(int)
    columns = np.clip((np.arange(width) + 0.5) / width * entity.shape[1], 0, entity.shape[1] - 1).astype(int)
    labels = entity[np.ix_(rows, columns)].reshape(-1)

    hit = np.isfinite(ranges)
    distant = hit & (ranges > minimum_range_m)
    is_sky = (labels == sky_id) & usable
    is_structure = np.isin(labels, list(structural_ids)) & usable
    conflict = is_sky & hit
    n_sky = max(int(is_sky.sum()), 1)
    return SkyConflict(
        sky_with_mesh=float(conflict.sum() / n_sky),
        sky_with_distant_mesh=float((is_sky & distant).sum() / n_sky),
        structure_without_mesh=float((is_structure & ~hit).sum() / max(int(is_structure.sum()), 1)),
        n_sky=int(is_sky.sum()),
        n_structure=int(is_structure.sum()),
        n_directions=int(usable.sum()),
        conflict_median_range_m=float(np.median(ranges[conflict])) if conflict.any() else float("nan"),
        settings={
            "grid": [height, width],
            "min_elevation_deg": min_elevation_deg,
            "minimum_range_m": minimum_range_m,
            "method": "equirectangular first-hit ray cast against the support mesh",
        },
    )


def draw_diagnostic(
    panorama_path: pathlib.Path,
    output: pathlib.Path,
    local_observed: np.ndarray,
    vertices: np.ndarray,
    camera: np.ndarray,
    heading: float,
    pitch: float,
    roll: float,
    settings: SkylineSettings,
) -> None:
    Image.MAX_IMAGE_PIXELS = None
    with Image.open(panorama_path) as source:
        image = source.resize((2048, 1024)).convert("RGB")
    draw = ImageDraw.Draw(image)
    obs_u, obs_v = directions_to_equirectangular(local_observed)
    observed = [(int(u * image.width), int(v * image.height)) for u, v in zip(obs_u, obs_v, strict=True)]
    for point in observed:
        draw.ellipse((point[0] - 2, point[1] - 2, point[0] + 2, point[1] + 2), fill=(0, 255, 255))

    model = mesh_skyline(
        vertices,
        camera,
        settings.n_bins,
        settings.minimum_distance_m,
        smoothing_size=settings.smoothing_size,
        smoothing_percentile=settings.smoothing_percentile,
    )
    azimuth = (np.arange(settings.n_bins) / settings.n_bins - 0.5) * 2.0 * np.pi
    cp = np.cos(model)
    world = np.stack([np.sin(azimuth) * cp, np.cos(azimuth) * cp, np.sin(model)], axis=1)
    rotation = panorama_to_world_matrix(heading, pitch_deg=pitch, roll_deg=roll)
    local = world @ rotation
    model_u, model_v = directions_to_equirectangular(local)
    order = np.argsort(model_u)
    predicted = [(int(model_u[i] * image.width), int(model_v[i] * image.height)) for i in order]
    draw.line(predicted, fill=(255, 40, 190), width=3)
    image.save(output, quality=94)


def _semantic_ids(document: dict[str, Any]) -> tuple[int, set[int], dict[int, str]]:
    id2label = {int(key): value for key, value in document["entity_id2label"].items()}
    sky_id = next((index for index, label in id2label.items() if label.casefold() == "sky"), None)
    if sky_id is None:
        raise SystemExit("segmentation vocabulary has no sky class")
    structural = {index for index, label in id2label.items() if label.casefold() in STRUCTURAL_LABELS}
    return sky_id, structural, id2label


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mesh", type=pathlib.Path, required=True)
    parser.add_argument("--semantics", type=pathlib.Path, required=True)
    parser.add_argument("--semantics-json", type=pathlib.Path, required=True)
    parser.add_argument("--pose", type=pathlib.Path, required=True)
    parser.add_argument("--panorama", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--bins", type=int, default=1024)
    parser.add_argument("--maxiter", type=int, default=600)
    parser.add_argument("--minimum-skyline-distance", type=float, default=8.0)
    parser.add_argument(
        "--skyline-percentile",
        type=float,
        default=90.0,
        help="Azimuthal filter percentile on the mesh skyline. 50 is the median filter that shaves roof peaks.",
    )
    parser.add_argument("--smoothing-size", type=int, default=11)
    parser.add_argument(
        "--dz-bounds",
        type=float,
        nargs=2,
        default=(-3.0, 3.0),
        help="Vertical search bound in metres around the measured camera altitude",
    )
    parser.add_argument(
        "--fit-bias",
        type=float,
        nargs=2,
        default=(0.0, 0.0),
        help=(
            "Bounds in degrees for a jointly fitted mesh-skyline elevation bias. Off by default because it is "
            "degenerate with dz: measured at Korenmarkt, three metres of altitude cost 0.05 degrees of residual "
            "once the bias is free. Useful as a diagnostic, not as a production parameter."
        ),
    )
    parser.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_SEEDS))
    parser.add_argument(
        "--ground-from-mesh",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Replace the scene-wide camera_ground_z_m with a downward ray cast under this camera",
    )
    parser.add_argument("--ground-patch-m", type=float, default=3.0)
    parser.add_argument(
        "--camera-height-m",
        type=float,
        help=(
            "Override the scene's assumed rig height above the ground. Supply a measured value and a tight "
            "--dz-bounds to pin altitude externally, which is the only way the skyline bias becomes identifiable."
        ),
    )
    parser.add_argument(
        "--sky-conflict",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Also compute the sky-conflict metric, which is independent of the skyline objective",
    )
    parser.add_argument("--sky-conflict-width", type=int, default=512)
    parser.add_argument("--profile", action="store_true", help="Also profile each axis, which is slow")
    parser.add_argument("--profile-tolerance-deg", type=float, default=0.02)
    return parser


def main() -> None:
    args = _parser().parse_args()

    entity = np.load(args.semantics)["entity"]
    sky_id, structural_ids, _ = _semantic_ids(json.loads(args.semantics_json.read_text()))
    pose = json.loads(args.pose.read_text())
    initial_position = np.asarray(pose["position_enu_m"], dtype=float)
    initial_heading = float(pose["heading_deg"])
    pitch_prior, roll_prior = streetview_orientation_prior(
        float(pose.get("tilt_deg", 90.0)),
        float(pose.get("roll_deg", 0.0)),
    )

    vertices, faces = read_binary_ply(args.mesh)

    ground: dict[str, Any] = {}
    if args.ground_from_mesh:
        camera_height = float(args.camera_height_m or pose.get("camera_height_m", 2.5))
        sample = ground_elevation(
            vertices,
            faces,
            float(initial_position[0]),
            float(initial_position[1]),
            ceiling_z_m=float(initial_position[2]),
            patch_m=args.ground_patch_m,
        )
        ground = sample.as_dict()
        ground["camera_height_m"] = camera_height
        ground["camera_height_source"] = (
            "measured, supplied on the command line" if args.camera_height_m else "scene config"
        )
        ground["scene_constant_z_m"] = float(initial_position[2] - float(pose.get("camera_height_m", 2.5)))
        ground["correction_m"] = float(sample.elevation_m + camera_height - initial_position[2])
        initial_position = np.array([initial_position[0], initial_position[1], sample.elevation_m + camera_height])
        print(f"[align] ground under camera {sample.elevation_m:.3f} m, correction {ground['correction_m']:+.3f} m")

    settings = SkylineSettings(
        n_bins=args.bins,
        minimum_distance_m=args.minimum_skyline_distance,
        smoothing_size=args.smoothing_size,
        smoothing_percentile=args.skyline_percentile,
    )
    bias_bounds = None if tuple(args.fit_bias) == (0.0, 0.0) else tuple(args.fit_bias)
    dz_bounds = (float(args.dz_bounds[0]), float(args.dz_bounds[1]))
    candidates = candidate_vertices(
        vertices,
        initial_position,
        settings.n_bins,
        settings.minimum_distance_m,
        search_box_m=((-4.0, 4.0), (-4.0, 4.0), dz_bounds),
        smoothing_size=settings.smoothing_size,
        smoothing_percentile=settings.smoothing_percentile,
    )
    observed = observed_skyline(entity, sky_id, settings.n_bins, structural_ids)
    if len(observed) < settings.n_bins // 8:
        raise SystemExit(f"only {len(observed)} structurally supported skyline samples")

    fit_kwargs: dict[str, Any] = {
        "settings": settings,
        "maxiter": args.maxiter,
        "dz_bounds": dz_bounds,
        "bias_bounds_deg": bias_bounds,
    }
    ensemble = seed_study(
        candidates,
        observed,
        initial_position,
        initial_heading,
        pitch_prior,
        roll_prior,
        seeds=tuple(args.seeds),
        progress=True,
        **fit_kwargs,
    )
    best = ensemble.best
    dx, dy, dz, yaw, pitch_delta, roll_delta = best.params
    pitch = pitch_prior + pitch_delta
    roll = roll_prior + roll_delta
    camera = initial_position + best.params[:3]

    cost_kwargs = {
        "vertices": candidates,
        "local_skyline": observed,
        "position": initial_position,
        "heading_deg": initial_heading,
        "pitch_prior_deg": pitch_prior,
        "roll_prior_deg": roll_prior,
        "settings": settings,
    }
    best_vector = np.r_[best.params, best.bias_deg] if bias_bounds is not None else best.params
    reprune = candidate_vertices(
        vertices,
        camera,
        settings.n_bins,
        settings.minimum_distance_m,
        smoothing_size=settings.smoothing_size,
        smoothing_percentile=settings.smoothing_percentile,
    )
    recheck = skyline_cost(best_vector, **{**cost_kwargs, "vertices": reprune})
    signed = signed_skyline_residual(best_vector, **cost_kwargs)

    aligned = dict(pose)
    aligned.update(
        {
            "position_enu_m": camera.tolist(),
            "heading_deg": initial_heading + yaw,
            "pitch_correction_deg": pitch,
            "roll_correction_deg": roll,
            "pitch_metadata_prior_deg": pitch_prior,
            "roll_metadata_prior_deg": roll_prior,
            "pitch_metadata_delta_deg": pitch_delta,
            "roll_metadata_delta_deg": roll_delta,
            "skyline_score_mean_rad": best.cost,
            "skyline_score_mean_deg": best.residual_deg,
            "skyline_bias_deg": best.bias_deg,
            "skyline_signed_residual_median_deg": float(np.degrees(np.median(signed))),
            "skyline_smoothing_percentile": settings.smoothing_percentile,
            "skyline_dz_bounds_m": list(dz_bounds),
            "skyline_dz_at_bound": bool(min(abs(dz - dz_bounds[0]), abs(dz - dz_bounds[1])) < 0.1),
            "pose_uncertainty": ensemble.as_dict(),
            "skyline_start_position_enu_m": initial_position.tolist(),
            "candidate_prune_recheck_deg": float(np.degrees(recheck) - best.residual_deg),
            "initial_pose": pose,
            "alignment_method": "streetview_orientation_prior_plus_segmented_structural_skyline",
            "n_candidate_vertices": len(candidates),
            "n_observed_structural_skyline_samples": len(observed),
            "minimum_skyline_distance_m": settings.minimum_distance_m,
        }
    )
    if ground:
        aligned["ground_measurement"] = ground

    if args.sky_conflict:
        try:
            conflict = sky_conflict(
                vertices,
                faces,
                entity,
                sky_id,
                structural_ids,
                camera,
                heading_deg=initial_heading + yaw,
                pitch_deg=pitch,
                roll_deg=roll,
                width=args.sky_conflict_width,
                height=args.sky_conflict_width // 2,
            )
        except ImportError as exc:
            aligned["sky_conflict"] = {"unavailable": str(exc)}
            print(f"[align] sky conflict skipped: {exc}")
        else:
            aligned["sky_conflict"] = conflict.as_dict()
            print(
                f"[align] sky with mesh hit {conflict.sky_with_mesh:.4f}, "
                f"structure without mesh hit {conflict.structure_without_mesh:.4f}"
            )

    if args.profile:
        aligned["pose_profile"] = profile_intervals(
            best_vector,
            _bounds(
                dz_bounds,
                translation_m=4.0,
                yaw_deg=20.0,
                orientation_deg=6.0,
                bias_bounds_deg=bias_bounds,
            ),
            tolerance_deg=args.profile_tolerance_deg,
            **cost_kwargs,
        )

    args.out.mkdir(parents=True, exist_ok=True)
    pose_path = args.out / "pose_aligned.json"
    pose_path.write_text(json.dumps(aligned, indent=2))
    if args.panorama is not None:
        draw_diagnostic(
            args.panorama,
            args.out / "skyline_alignment.jpg",
            observed,
            vertices,
            camera,
            float(aligned["heading_deg"]),
            pitch,
            roll,
            settings,
        )
    deviation = np.sqrt(np.diag(ensemble.covariance))
    print(f"[align] correction xyz={best.params[:3].round(3).tolist()} m")
    print(f"[align] residual correction ypr={best.params[3:].round(3).tolist()} deg")
    print(f"[align] total pitch/roll={[round(pitch, 3), round(roll, 3)]} deg")
    print(f"[align] mean robust skyline error={best.residual_deg:.3f} deg, bias={best.bias_deg:+.3f} deg")
    print(
        f"[align] seed spread 1 sigma xyz={deviation[:3].round(3).tolist()} m ypr={deviation[3:6].round(3).tolist()} deg"
    )
    print(f"[align] -> {pose_path}")


if __name__ == "__main__":
    main()
