"""Refine a camera pose by matching its segmented skyline to the tile mesh.

Provider metadata gives a strong horizontal and orientation prior but no
altitude. This optimiser compares the panorama's sky boundary with the angular
envelope of the photogrammetry vertices. Ground level tile noise is therefore
absent from the objective, which is the reason skyline registration is preferred
here.

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

Third, **the reported residual is not an error bar and it is not a pose
quality.** Every pose therefore ships with an ensemble covariance over
independent optimiser seeds, and with the sky conflict of
:mod:`~semantic_twin.vision.conflict`, which does not use this objective at all.
:class:`~semantic_twin.vision.provenance.Registration` is what carries all three
downstream, and it is the type anything asking "how good is this pose" should
use rather than reading the residual out of the file.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.ndimage import percentile_filter
from scipy.optimize import differential_evolution, minimize

from ..pano_geometry import panorama_to_world_matrix

PARAMETER_NAMES = ("dx_m", "dy_m", "dz_m", "yaw_deg", "pitch_delta_deg", "roll_delta_deg")
BIAS_NAME = "skyline_bias_deg"
DEFAULT_SEEDS = (0xAE615, 1, 2, 3, 5, 8, 13, 21)


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
