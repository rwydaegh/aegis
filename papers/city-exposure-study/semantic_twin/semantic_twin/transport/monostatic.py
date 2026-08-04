"""The co-located branch: what a radar standing where the pedestrian stands receives.

MONOSTATIC_SBR.md section 3 derives this quantity and then demotes it, correctly,
because it is a quadratic functional of the one way Green's function and cannot
be inverted for the transfer tensor the exposure integral needs. Demoted is not
deleted. Section 3.3 keeps it on the grounds that it costs almost nothing on top
of the adjoint trace and that whether it predicts the exposure ratio is an
empirical question worth a result either way, and section 11.6 states that
question. This module is that branch, and MONOSTATIC.md is the answer.

What is computed is `g = P_r / P_t` for an isotropic transmitter and an isotropic
receiver at the same point `S`, dimensionless, with the receive aperture
`A_e = G_r lam^2 / (4 pi)`. Nothing about it is normalised away, so the number is
directly a link budget: measured over eleven squares at 15 GHz and head height it
sits at -70.8 dB with a five decibel spread, and 98 % of it is the pavement under
the observer at a four metre round trip, which
:func:`half_space_first_order_return` reproduces in closed form to 0.2 dB.

The measure zero trap, and the two estimators
---------------------------------------------

A ray that leaves `S` returns to the point `S` with probability zero, exactly as
in section 5.1, so the naive implementation that waits for a ray to come back
collects nothing at all and reports a clean zero. Two things are done instead,
and they split the return along the same Rayleigh boundary the tracer already
uses to split its own scattering.

The incoherent part is a next event estimate. At every surface interaction the
path already carries the correct incident power, and the diffuse lobe of the
surface radiates a finite radiance back toward `S`, so one occlusion ray per
vertex collects it with finite variance. This is :class:`MonostaticGather`, and
it shares the adjoint trace: the departure measure is already uniform on the
sphere, which is what an isotropic transmitter illuminates with, and the path
prefix already carries the throughput. Attaching it changes no random draw.

The coherent part cannot be sampled at all, in either estimator, and is computed
deterministically instead. A specular retro reflection at first order requires
the surface normal to point at `S`, so the contributing set is the feet of the
perpendiculars from `S` onto the facet planes, which is a finite set that
:func:`specular_glints` enumerates. Its weight is the image source result
`(lam / (4 pi L))^2` over the round trip `L = 2 d`, reduced to the physical
optics plate result when the facet is smaller than the first Fresnel zone.

What is missing, and it is the one term worth naming, is the purely specular
chain of order two and above, of which the wall to ground dihedral is the member
that matters. Section 5.1 is explicit that corner reflectors are where the
monostatic response is largest and the estimator least stable. The gather does
carry every chain whose last interaction is diffuse, so the omission is narrower
than it sounds, and MONOSTATIC.md reports how much of the measured total the
first order coherent term already is.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .tracer import PointResult, SbrTracer, fresnel_power_reflectance, specular_share

SPEED_OF_LIGHT_M_S = 299_792_458.0


@dataclass(frozen=True)
class MonostaticConfig:
    """Everything that changes the co-located number, and nothing that does not."""

    #: Interaction orders resolved separately. Anything deeper folds into the
    #: last bin rather than being dropped.
    max_order: int = 8
    #: Two way range profile resolution, in metres of round trip path.
    range_bin_m: float = 2.0
    #: Two way range the profile covers. Beyond it a return is still counted in
    #: the total and in the last profile bin.
    max_two_way_range_m: float = 600.0
    #: Isotropic receive by default, so `A_e = lam^2 / (4 pi)`.
    receive_gain: float = 1.0
    #: Offset along the surface normal before the occlusion ray is shot, and the
    #: slack allowed on its length before a hit counts as a blocker.
    shadow_epsilon_m: float = 2.0e-3
    #: Facets beyond this range are not searched for a specular glint. The crop
    #: radius of the mesh is the natural value.
    glint_max_range_m: float = 400.0


@dataclass
class MonostaticResult:
    """The co-located return at one observation point. No paths, by design."""

    origin: np.ndarray
    gain: float  # total P_r / P_t, dimensionless
    gain_diffuse: float
    gain_glint: float
    gain_by_order: np.ndarray  # (max_order + 1,) incoherent, index is the interaction order
    range_profile: np.ndarray  # incoherent power against two way range
    range_bin_m: float
    mean_two_way_range_m: float
    relative_standard_error: float
    glint_facets: int
    glint_subfresnel_facets: int
    glint_nearest_m: float
    shadow_rays: int
    blocked_fraction: float
    rays: int
    seconds: float
    coverage: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def scalars(self) -> dict[str, float]:
        """The row a run writes next to the exposure scalars."""
        total = self.gain
        first = float(self.gain_by_order[1]) if self.gain_by_order.size > 1 else 0.0
        out = {
            "mono_gain": total,
            "mono_gain_db": to_db(total),
            "mono_gain_diffuse": self.gain_diffuse,
            "mono_gain_glint": self.gain_glint,
            "mono_glint_share": self.gain_glint / total if total > 0.0 else 0.0,
            "mono_first_order_share": first / total if total > 0.0 else 0.0,
            "mono_mean_two_way_range_m": self.mean_two_way_range_m,
            "mono_relative_standard_error": self.relative_standard_error,
            "mono_glint_facets": float(self.glint_facets),
            "mono_blocked_fraction": self.blocked_fraction,
            "mono_seconds": self.seconds,
        }
        for order in range(1, self.gain_by_order.size):
            out[f"mono_gain_order_{order}"] = float(self.gain_by_order[order])
        if self.coverage.get("available"):
            out["mono_evidence_chain_share"] = self.coverage["closed_loop_chain_observed_total"]
            out["mono_evidence_last_share"] = self.coverage["closed_loop_last_surface_observed_total"]
            for order in range(1, min(4, self.gain_by_order.size)):
                out[f"mono_evidence_chain_share_order_{order}"] = self.coverage["closed_loop_chain_observed"][order]
                out[f"adjoint_evidence_chain_share_order_{order}"] = self.coverage["open_path_chain_observed"][order]
        return out


def half_space_first_order_return(
    height_m: float,
    permittivity: complex,
    rms_height_m: float,
    wavelength_m: float,
    *,
    receive_gain: float = 1.0,
    samples: int = 20_001,
) -> float:
    """Closed form incoherent return of a rough half space under the observer.

    Derived here rather than borrowed. An isotropic transmitter puts
    `dP = P_t dOmega / (4 pi)` into the direction at polar angle `th` from nadir,
    which reaches the ground at range `r = h / cos(th)`. The surface sends
    `R (1 - kappa) cos(th) / pi` of that back per steradian and the receiver
    collects `A_e / r^2`, so with `mu = cos(th)`

        g_1 = (A_e / (2 pi h^2)) * int_0^1 R(mu) (1 - kappa(mu)) mu^3 dmu

    The `mu^3` is the whole content of the geometry: one power from the range
    being `h / mu` squared against one from the cosine of the return lobe.

    This is the reference the measured city number is checked against, and it is
    what makes the interpretation of section 6 of MONOSTATIC.md quantitative
    rather than a hunch: at 15 GHz over P.2040 pavement at 1.5 m it gives
    -70.99 dB, against a measured median of -70.84 dB over eleven squares.
    """
    mu = np.linspace(1.0e-6, 1.0, int(samples))
    reflectance = fresnel_power_reflectance(mu, np.full(mu.shape, complex(permittivity)))
    coherent = specular_share(np.full(mu.shape, float(rms_height_m)), mu, wavelength_m)
    integral = float(np.trapezoid(reflectance * (1.0 - coherent) * mu**3, mu))
    aperture = receive_gain * wavelength_m**2 / (4.0 * np.pi)
    return aperture / (2.0 * np.pi * height_m**2) * integral


def to_db(value: float | np.ndarray) -> float | np.ndarray:
    """Power ratio to dB, with a floor so an empty square is finite."""
    array = np.asarray(value, dtype=np.float64)
    out = 10.0 * np.log10(np.maximum(array, 1.0e-300))
    return float(out) if out.ndim == 0 else out


class MonostaticGather:
    """Next event estimate of the incoherent return, one occlusion ray per vertex.

    The estimator, derived from the transport chain of MONOSTATIC_SBR.md section
    3.1. A ray leaving an isotropic transmitter of total power `P_t`, one of `N`
    drawn uniformly on the sphere, carries `P_t / N` and arrives at the interaction
    `m` carrying `P_t W_m / N`, where `W_m` is the tracer's throughput after the
    reflectance of that interaction has been applied. The surface re-radiates
    toward `S` with intensity `W_m (1 - kappa) cos(th_s) / pi` per unit incident
    power, `kappa` being the Rayleigh coherent share that the coherent branch owns
    instead, and the receiver collects `A_e / r^2` of the sphere at range `r`. So

        g = (1 / N) sum over rays sum over vertices
            W_m * (1 - kappa_m) * cos(th_s) / pi * A_e / r^2 * V(x_m, S)

    with `A_e = G_r lam^2 / (4 pi)` and `V` the occlusion indicator. The cosine
    lobe is the tracer's own diffuse lobe, so the incoming direction never enters,
    which is why the reduction needs no more state than it is handed.

    Why this shares the adjoint trace rather than owning one. The departure
    distribution the adjoint estimator needs is uniform on the sphere, and that is
    exactly what an isotropic transmitter illuminates with, so the same rays are
    the correct sample for both. The path prefix carries the same throughput for
    both. Nothing is resampled and no random number is drawn here, so the traced
    :class:`~.tracer.PointResult` is bit identical with a gather attached. The
    cost is one occlusion ray per surface interaction, against one intersection
    ray per interaction that the trace already pays.
    """

    def __init__(
        self,
        origin: np.ndarray,
        geometry: Any,
        wavelength_m: float,
        config: MonostaticConfig | None = None,
        observed: np.ndarray | None = None,
    ) -> None:
        self.origin = np.asarray(origin, dtype=np.float64)
        self.geometry = geometry
        self.wavelength_m = float(wavelength_m)
        self.config = config or MonostaticConfig()
        self.observed = None if observed is None else np.asarray(observed, dtype=bool)
        self.aperture_m2 = self.config.receive_gain * self.wavelength_m**2 / (4.0 * np.pi)
        self.gain_by_order = np.zeros(self.config.max_order + 1)
        shape = self.config.max_order + 1
        # The evidence ledger, and the reason this module exists. ``incident`` is
        # the open path denominator: the power the path carries away from its
        # interaction of that order, whether or not it ever comes back, which is
        # what the adjoint estimator goes on to deposit at the sky. ``returned``
        # is the part of it the co-located receiver actually collects. Each is
        # split by whether that interaction is on panorama observed material and
        # by whether every interaction of the chain up to it is. The two
        # denominators are the same weight, so the ratio of the two chain shares
        # is the price of not closing the loop.
        self.incident_power = np.zeros(shape)
        self.incident_observed = np.zeros(shape)
        self.incident_chain_observed = np.zeros(shape)
        self.returned_observed = np.zeros(shape)
        self.returned_chain_observed = np.zeros(shape)
        self._chain: np.ndarray | None = None
        self.bins = max(1, int(round(self.config.max_two_way_range_m / self.config.range_bin_m)))
        self.range_profile = np.zeros(self.bins)
        self.shadow_rays = 0
        self.blocked = 0
        self.contributions = 0
        self._range_weighted = 0.0
        self._sum = 0.0
        self._sum_squares = 0.0
        self._rays = 0
        self._per_ray: np.ndarray | None = None

    def begin(self, origin: np.ndarray, count: int) -> None:
        """Start a batch. Called by the tracer, once per batch of rays."""
        del origin
        self._flush()
        self._per_ray = np.zeros(int(count))
        self._chain = np.ones(int(count), dtype=bool)

    def _flush(self) -> None:
        if self._per_ray is None:
            return
        self._sum += float(self._per_ray.sum())
        self._sum_squares += float(np.square(self._per_ray).sum())
        self._rays += int(self._per_ray.size)
        self._per_ray = None

    def vertex(
        self,
        index: np.ndarray,
        position: np.ndarray,
        incoming: np.ndarray,
        normal: np.ndarray,
        throughput: np.ndarray,
        share: np.ndarray,
        order: np.ndarray,
        path_length: np.ndarray,
        face: np.ndarray | None = None,
    ) -> None:
        """Connect one batch of surface interactions back to the observation point.

        ``normal`` is the tracer's already flipped normal, facing the incoming
        ray. ``throughput`` is after the reflectance of this interaction, so the
        albedo is in it and must not be applied again. ``share`` is the Rayleigh
        coherent fraction, whose complement is the diffuse lobe this estimator
        owns. ``incoming`` is unused by the cosine lobe and is accepted so the
        signature does not change if a directive model is added. ``face`` indexes
        the triangle, and is what the observed mask is read with.
        """
        del incoming
        cfg = self.config
        index = np.asarray(index)
        bin_order = np.minimum(order, cfg.max_order)
        if self.observed is not None and face is not None and self._chain is not None:
            here = self.observed[np.asarray(face, dtype=np.int64)]
            self._chain[index] &= here
            np.add.at(self.incident_power, bin_order, throughput)
            np.add.at(self.incident_observed, bin_order[here], throughput[here])
            clean = self._chain[index]
            np.add.at(self.incident_chain_observed, bin_order[clean], throughput[clean])
        to_origin = self.origin[None, :] - position
        distance = np.linalg.norm(to_origin, axis=1)
        safe = np.maximum(distance, 1.0e-12)
        direction = to_origin / safe[:, None]
        cos_s = np.einsum("ij,ij->i", normal, direction)
        diffuse = 1.0 - share
        live = (cos_s > 0.0) & (diffuse > 0.0) & (throughput > 0.0) & (distance > 10.0 * cfg.shadow_epsilon_m)
        candidate = np.flatnonzero(live)
        if candidate.size == 0:
            return

        start = position[candidate] + cfg.shadow_epsilon_m * normal[candidate]
        hit, blocker, _, _ = self.geometry.intersect(start, direction[candidate])
        clear = (~hit) | (blocker > distance[candidate] - 4.0 * cfg.shadow_epsilon_m)
        self.shadow_rays += int(candidate.size)
        self.blocked += int(np.count_nonzero(~clear))
        keep = candidate[clear]
        if keep.size == 0:
            return

        contribution = (
            throughput[keep] * diffuse[keep] * cos_s[keep] / np.pi * self.aperture_m2 / np.square(distance[keep])
        )
        self.contributions += int(keep.size)
        if self._per_ray is not None:
            np.add.at(self._per_ray, index[keep], contribution)
        else:  # pragma: no cover - only if a caller drives vertex() without begin()
            self._sum += float(contribution.sum())
        np.add.at(self.gain_by_order, bin_order[keep], contribution)
        if self.observed is not None and face is not None and self._chain is not None:
            on_evidence = here[keep]
            np.add.at(self.returned_observed, bin_order[keep][on_evidence], contribution[on_evidence])
            whole = self._chain[index[keep]]
            np.add.at(self.returned_chain_observed, bin_order[keep][whole], contribution[whole])
        two_way = path_length[keep] + distance[keep]
        self._range_weighted += float(np.sum(contribution * two_way))
        bin_index = np.clip((two_way / cfg.range_bin_m).astype(np.int64), 0, self.bins - 1)
        np.add.at(self.range_profile, bin_index, contribution)

    def finalise(self, rays: int) -> tuple[float, np.ndarray, np.ndarray, float, float]:
        """Divide the accumulators by the ray count. Returns the reduced pieces."""
        self._flush()
        rays = int(rays)
        if rays <= 0:
            raise ValueError("a monostatic gather needs at least one ray")
        total = self._sum / rays
        mean_range = self._range_weighted / self._sum if self._sum > 0.0 else 0.0
        variance = max(self._sum_squares / rays - (self._sum / rays) ** 2, 0.0)
        standard_error = float(np.sqrt(variance / rays))
        relative = standard_error / total if total > 0.0 else 0.0
        return total, self.gain_by_order / rays, self.range_profile / rays, mean_range, relative

    def coverage(self) -> dict[str, Any]:
        """The evidence ledger, as shares of power rather than counts of faces.

        Two questions, one trace. ``closed_loop`` is the share of the power the
        co-located receiver collects whose whole interaction chain sits on
        triangles a registered panorama observed. ``open_path`` is the same share
        of the power the path carries on past that interaction, which is what the
        adjoint estimator eventually deposits at the sky. The first hit is common
        to both and is visible from the observation point by construction, so any
        gap between the two columns at order two and beyond is the price of not
        closing the loop.
        """
        if self.observed is None:
            return {"available": False}
        with np.errstate(invalid="ignore", divide="ignore"):
            open_last = _share(self.incident_observed, self.incident_power)
            open_chain = _share(self.incident_chain_observed, self.incident_power)
            closed_last = _share(self.returned_observed, self.gain_by_order)
            closed_chain = _share(self.returned_chain_observed, self.gain_by_order)
        total = float(self.gain_by_order.sum())
        return {
            "available": True,
            "order": list(range(self.config.max_order + 1)),
            "carried_power": self.incident_power.tolist(),
            "returned_power": self.gain_by_order.tolist(),
            "open_path_last_surface_observed": open_last,
            "open_path_chain_observed": open_chain,
            "closed_loop_last_surface_observed": closed_last,
            "closed_loop_chain_observed": closed_chain,
            "closed_loop_chain_observed_total": (
                float(self.returned_chain_observed.sum() / total) if total > 0.0 else None
            ),
            "closed_loop_last_surface_observed_total": (
                float(self.returned_observed.sum() / total) if total > 0.0 else None
            ),
        }


def _share(numerator: np.ndarray, denominator: np.ndarray) -> list[float | None]:
    """Element wise ratio, None where the denominator carried no power at all."""
    return [
        float(n / d) if d > 0.0 else None for n, d in zip(np.asarray(numerator), np.asarray(denominator), strict=True)
    ]


@dataclass(frozen=True)
class GlintResult:
    """The deterministic first order specular return."""

    gain: float
    facets: int
    subfresnel_facets: int
    nearest_m: float
    searched_facets: int
    occluded_facets: int
    per_facet_gain: np.ndarray
    per_facet_range_m: np.ndarray


def specular_glints(
    origin: np.ndarray,
    *,
    vertices: np.ndarray,
    faces: np.ndarray,
    face_class: np.ndarray | None,
    permittivity: np.ndarray,
    rms_height_m: np.ndarray,
    wavelength_m: float,
    geometry: Any,
    config: MonostaticConfig | None = None,
) -> GlintResult:
    """First order coherent retro reflection, enumerated rather than sampled.

    A specular return to the transmitter at first order needs the outgoing mirror
    direction to be the reverse of the incoming one, which happens only where the
    surface normal points at `S`. On a triangulated scene that is the foot of the
    perpendicular from `S` onto each facet plane, so the contributing set is at
    most one point per facet and is found by enumeration. Sampling cannot find it:
    this is the measure zero set of MONOSTATIC_SBR.md section 5.1.

    The weight is the image source result. A facet large enough to contain the
    first Fresnel zone of the round trip behaves as the infinite plane it lies in,
    giving `g = |Gamma|^2 (lam / (4 pi L))^2` over `L = 2 d`, which is free space
    spreading over the unfolded path and nothing else. A facet smaller than that
    zone radiates less, and physical optics gives the flat plate result
    `sigma = 4 pi A^2 / lam^2`, so `g = |Gamma|^2 A^2 / (16 pi^2 d^4)`. The two
    forms are equal at `A = lam d / 2`, which is what fixes the crossover, and the
    implementation is the plane form times `min(1, A / (lam d / 2))^2`. Both limits
    are tested.

    Only the Rayleigh coherent share of the reflected power is taken here. Its
    complement is the diffuse lobe, which :class:`MonostaticGather` already
    collects, so the two branches partition the reflected power and neither double
    counts the other.
    """
    cfg = config or MonostaticConfig()
    point = np.asarray(origin, dtype=np.float64)
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    a = vertices[faces[:, 0]]
    b = vertices[faces[:, 1]]
    c = vertices[faces[:, 2]]
    cross = np.cross(b - a, c - a)
    twice_area = np.linalg.norm(cross, axis=1)
    good = twice_area > 0.0
    normal = np.zeros_like(cross)
    normal[good] = cross[good] / twice_area[good][:, None]
    area = 0.5 * twice_area

    signed = np.einsum("ij,ij->i", normal, point[None, :] - a)
    distance = np.abs(signed)
    foot = point[None, :] - signed[:, None] * normal
    near = good & (distance > 1.0e-6) & (distance <= cfg.glint_max_range_m)

    inside = np.zeros(faces.shape[0], dtype=bool)
    if np.any(near):
        idx = np.flatnonzero(near)
        inside[idx] = _inside_triangle(foot[idx], a[idx], b[idx], c[idx], normal[idx])
    candidate = np.flatnonzero(near & inside)
    searched = int(candidate.size)
    if searched == 0:
        return GlintResult(0.0, 0, 0, float("inf"), 0, 0, np.zeros(0), np.zeros(0))

    towards = foot[candidate] - point[None, :]
    length = np.linalg.norm(towards, axis=1)
    towards /= np.maximum(length, 1.0e-12)[:, None]
    hit, first, _, _ = geometry.intersect(np.tile(point, (searched, 1)) + cfg.shadow_epsilon_m * towards, towards)
    tolerance = np.maximum(5.0e-3, 1.0e-4 * length)
    visible = hit & (first > length - tolerance)
    occluded = searched - int(np.count_nonzero(visible))
    keep = candidate[visible]
    if keep.size == 0:
        return GlintResult(0.0, 0, 0, float("inf"), searched, occluded, np.zeros(0), np.zeros(0))

    klass = np.zeros(keep.size, dtype=np.int64) if face_class is None else np.asarray(face_class)[keep]
    ones = np.ones(keep.size)
    reflectance = fresnel_power_reflectance(ones, np.asarray(permittivity)[klass])
    coherent = specular_share(np.asarray(rms_height_m)[klass], ones, wavelength_m)
    range_m = distance[keep]
    fresnel_area = 0.5 * wavelength_m * range_m
    fill = np.minimum(1.0, area[keep] / fresnel_area)
    gain = (
        cfg.receive_gain * coherent * reflectance * np.square(wavelength_m / (8.0 * np.pi * range_m)) * np.square(fill)
    )
    return GlintResult(
        gain=float(gain.sum()),
        facets=int(keep.size),
        subfresnel_facets=int(np.count_nonzero(fill < 1.0)),
        nearest_m=float(range_m.min()),
        searched_facets=searched,
        occluded_facets=occluded,
        per_facet_gain=gain,
        per_facet_range_m=range_m,
    )


def _inside_triangle(point: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray, normal: np.ndarray) -> np.ndarray:
    """Whether ``point``, known to lie in the plane of the triangle, is inside it."""
    first = np.einsum("ij,ij->i", np.cross(b - a, point - a), normal)
    second = np.einsum("ij,ij->i", np.cross(c - b, point - b), normal)
    third = np.einsum("ij,ij->i", np.cross(a - c, point - c), normal)
    return ((first >= 0.0) & (second >= 0.0) & (third >= 0.0)) | ((first <= 0.0) & (second <= 0.0) & (third <= 0.0))


def trace_monostatic(
    tracer: SbrTracer,
    origin: np.ndarray,
    models: dict[str, Any],
    *,
    ground_z_m: float = 0.0,
    seed: int | None = None,
    config: MonostaticConfig | None = None,
    glints: bool = True,
    observed: np.ndarray | None = None,
) -> tuple[PointResult, MonostaticResult]:
    """One trace, two answers: the adjoint transfer and the co-located return.

    The gather rides the trace, so this costs one trace plus one occlusion ray per
    surface interaction. The glint enumeration is a separate deterministic pass
    over the facets and needs a geometry that exposes ``vertices`` and ``faces``,
    which the analytic geometries do not, so it is skipped where it cannot run.
    """
    cfg = config or MonostaticConfig()
    started = time.perf_counter()
    gather = MonostaticGather(origin, tracer.geometry, tracer.wavelength_m, cfg, observed=observed)
    point = tracer.trace(origin, models, ground_z_m=ground_z_m, seed=seed, gather=gather)
    total, by_order, profile, mean_range, relative = gather.finalise(point.rays)

    glint = GlintResult(0.0, 0, 0, float("inf"), 0, 0, np.zeros(0), np.zeros(0))
    has_mesh = hasattr(tracer.geometry, "vertices") and hasattr(tracer.geometry, "faces")
    if glints and has_mesh:
        glint = specular_glints(
            origin,
            vertices=tracer.geometry.vertices,
            faces=tracer.geometry.faces,
            face_class=tracer.face_class,
            permittivity=tracer.permittivity,
            rms_height_m=tracer.rms_height_m,
            wavelength_m=tracer.wavelength_m,
            geometry=tracer.geometry,
            config=cfg,
        )

    result = MonostaticResult(
        origin=np.asarray(origin, dtype=np.float64),
        gain=total + glint.gain,
        gain_diffuse=total,
        gain_glint=glint.gain,
        gain_by_order=by_order,
        range_profile=profile,
        range_bin_m=cfg.range_bin_m,
        mean_two_way_range_m=mean_range,
        relative_standard_error=relative,
        glint_facets=glint.facets,
        glint_subfresnel_facets=glint.subfresnel_facets,
        glint_nearest_m=glint.nearest_m,
        shadow_rays=gather.shadow_rays,
        blocked_fraction=gather.blocked / max(gather.shadow_rays, 1),
        rays=point.rays,
        seconds=time.perf_counter() - started,
        coverage=gather.coverage(),
        diagnostics={
            "glint_searched_facets": glint.searched_facets,
            "glint_occluded_facets": glint.occluded_facets,
            "gather_contributions": gather.contributions,
            "glints_enumerated": bool(glints and has_mesh),
        },
    )
    return point, result
