"""How rough a surface is, and what that costs the specular direction.

One closure runs the whole study: a Gaussian height field keeps
``exp(-g**2)`` of its reflected power in the specular direction, with
``g = 4 pi s cos(theta) / lambda``. Everything here is either that formula, the
prior that supplies ``s``, or a statement about where the formula stops being
the right model.

The prior and the closure are deliberately separate objects.
:class:`SurfaceRoughnessPrior` is a lognormal read from
``config/surface_roughness.json`` with its evidence grade attached, and it
knows whether the Gaussian closure describes it at all. Several classes say no:
a mortar joint grid and a sett pavement diffract into discrete orders, and a
coherent fraction that decays smoothly does not describe that. Those classes
refuse :meth:`SurfaceRoughnessPrior.specular_power_fraction` unless the caller
asks for the indicative value on purpose.

:func:`effective_rms_height` is the reduction the tracer runs on, and it is the
weakest link in this file. See its docstring.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np

SPEED_OF_LIGHT_M_S = 299_792_458.0


def wavelength_m(frequency_hz: float | np.ndarray) -> np.ndarray:
    """Free space wavelength, the yardstick every quantity here is measured against."""
    frequency = np.asarray(frequency_hz, dtype=np.float64)
    if np.any(frequency <= 0.0):
        raise ValueError("frequency must be positive")
    return SPEED_OF_LIGHT_M_S / frequency


GAUSSIAN_STRUCTURE = "gaussian_random"
PERIODIC_STRUCTURES = ("periodic_dominant", "two_scale_periodic_plus_random")


def rayleigh_roughness_parameter(
    rms_height_m: float | np.ndarray,
    incidence_cosine: float | np.ndarray,
    frequency_hz: float | np.ndarray,
) -> np.ndarray:
    """Dimensionless surface roughness relative to wavelength and incidence."""
    cosine = np.clip(np.asarray(incidence_cosine, dtype=np.float64), 0.0, 1.0)
    return 4.0 * np.pi * np.asarray(rms_height_m) * cosine / wavelength_m(frequency_hz)


def specular_power_fraction(
    rms_height_m: float | np.ndarray,
    incidence_cosine: float | np.ndarray,
    frequency_hz: float | np.ndarray,
) -> np.ndarray:
    """Coherent share of reflected power for a Gaussian rough surface.

    This is the Ament factor ``exp(-g**2)`` with ``g = 4 pi s cos(theta) / lam``.
    Recommendation ITU-R P.2146-0 equation 11 carries the same factor written as
    ``exp{-(2 k s cos(theta))**2}``, which is identical, and defines ``s`` there
    as the total RMS surface height rather than a two-scale component. P.2146-0
    is a sea-surface Recommendation, so the functional form is the ITU anchor
    and the application to a facade is this repository's extrapolation.
    """
    g = rayleigh_roughness_parameter(rms_height_m, incidence_cosine, frequency_hz)
    return np.exp(-(g**2))


def rayleigh_smooth_threshold_m(
    frequency_hz: float | np.ndarray,
    incidence_cosine: float | np.ndarray,
) -> np.ndarray:
    """RMS height at which the Rayleigh criterion stops calling a surface smooth.

    The criterion is ``s < lam / (8 cos(theta))``, which is ``g < pi / 2``. It is
    a threshold on a phase spread, not a statement about how much specular power
    survives, so it is reported alongside :func:`specular_power_fraction` rather
    than used to gate it.
    """
    cosine = np.clip(np.asarray(incidence_cosine, dtype=np.float64), 1e-6, 1.0)
    return wavelength_m(frequency_hz) / (8.0 * cosine)


def roughness_to_scattering_coefficient(
    rms_height_m: float | np.ndarray,
    incidence_cosine: float | np.ndarray,
    frequency_hz: float | np.ndarray,
) -> np.ndarray:
    """Map Gaussian roughness to Sionna's diffuse amplitude coefficient.

    The coherent reflected power fraction is approximated as ``exp(-g**2)``,
    where ``g`` is the Rayleigh roughness parameter. The remaining reflected
    power is assigned to Sionna's diffuse component, whose power fraction is
    ``S**2``. This is an engineering closure, not an ITU-R P.2040 parameter.
    """
    g = rayleigh_roughness_parameter(rms_height_m, incidence_cosine, frequency_hz)
    return np.sqrt(np.maximum(0.0, -np.expm1(-(g**2))))


@dataclass(frozen=True)
class SurfaceRoughnessPrior:
    """A per-class RMS height prior with its evidence grade attached.

    ``rms_height_m`` is the median of a lognormal, not a measured constant. The
    specular fraction ``exp(-g**2)`` is exponential in the square of the RMS
    height, so a caller that collapses this prior to its median before tracing
    will get an answer that is far from the ensemble mean. Use :meth:`sample`.
    """

    name: str
    rms_height_m: float
    log_standard_deviation: float
    plausible_range_m: tuple[float, float]
    correlation_length_m: float | None
    correlation_length_status: str
    evidence_grade: str
    radio_fitted: bool
    structure: str
    gaussian_closure_reliable: bool
    mean_texture_depth_m: float | None
    periodic_component: dict[str, Any] | None
    concepts: tuple[str, ...]
    itu_rows: tuple[str, ...]
    provenance: dict[str, Any]

    def __post_init__(self) -> None:
        if self.rms_height_m <= 0.0:
            raise ValueError("RMS height must be positive")
        if self.log_standard_deviation <= 0.0:
            raise ValueError("log standard deviation must be positive")
        lower, upper = self.plausible_range_m
        if not 0.0 < lower <= upper:
            raise ValueError("plausible range must be positive and ordered")
        if not lower <= self.rms_height_m <= upper:
            raise ValueError("central RMS height must lie inside its own plausible range")
        if self.radio_fitted:
            raise ValueError(
                f"{self.name} takes its central value from a radio-fitted source. Using one as a physical prior "
                "double counts the radio evidence, so it must not enter the library."
            )

    @property
    def gaussian_model_applies(self) -> bool:
        """Whether the Rayleigh closure is the right model for this class at all."""
        return self.structure == GAUSSIAN_STRUCTURE

    def sample(self, count: int, rng: np.random.Generator) -> np.ndarray:
        """Draw RMS heights from the lognormal, clipped to the plausible range."""
        draws = rng.lognormal(np.log(self.rms_height_m), self.log_standard_deviation, size=count)
        return np.clip(draws, *self.plausible_range_m)

    def specular_power_fraction(
        self,
        frequency_hz: float,
        incidence_deg: float | np.ndarray,
        *,
        allow_periodic: bool = False,
    ) -> np.ndarray:
        """Coherent power share at the median RMS height.

        Classes whose height field is dominated by a periodic component are
        refused unless ``allow_periodic`` is set, in the same spirit as
        :meth:`~.itu.PowerLawMaterial.evaluate` refusing to leave its frequency
        band. A mortar joint grid or a sett pavement diffracts into discrete
        orders, and a Gaussian coherent fraction does not describe that.
        """
        if not self.gaussian_model_applies and not allow_periodic:
            raise ValueError(
                f"{self.name} has structure '{self.structure}', so the Gaussian Rayleigh closure "
                "does not describe it. Pass allow_periodic=True to get the indicative value anyway."
            )
        cosine = np.cos(np.radians(incidence_deg))
        return specular_power_fraction(self.rms_height_m, cosine, frequency_hz)

    def smooth_at(self, frequency_hz: float, incidence_deg: float) -> bool:
        """Whether the median RMS height clears the Rayleigh smoothness criterion."""
        threshold = rayleigh_smooth_threshold_m(frequency_hz, np.cos(np.radians(incidence_deg)))
        return bool(self.rms_height_m < threshold)


class SurfaceRoughnessLibrary:
    def __init__(self, source: dict[str, Any], classes: dict[str, SurfaceRoughnessPrior]) -> None:
        self.source = source
        self.classes = classes

    def __getitem__(self, name: str) -> SurfaceRoughnessPrior:
        return self.classes[name]

    def __len__(self) -> int:
        return len(self.classes)

    def for_concept(self, prompt: str) -> list[SurfaceRoughnessPrior]:
        """Every roughness class that claims a given concept prompt."""
        return [entry for entry in self.classes.values() if prompt in entry.concepts]

    @classmethod
    def load(cls, path: pathlib.Path) -> SurfaceRoughnessLibrary:
        document = json.loads(path.read_text())
        source = document["source"]
        classes = {}
        for record in document["classes"]:
            lower, upper = record["plausible_range_mm"]
            correlation_mm = record.get("correlation_length_mm")
            texture_mm = record.get("mean_texture_depth_mm")
            entry = SurfaceRoughnessPrior(
                name=record["name"],
                rms_height_m=float(record["rms_height_mm"]) / 1000.0,
                log_standard_deviation=float(record["log_standard_deviation"]),
                plausible_range_m=(float(lower) / 1000.0, float(upper) / 1000.0),
                correlation_length_m=None if correlation_mm is None else float(correlation_mm) / 1000.0,
                correlation_length_status=record["correlation_length_status"],
                evidence_grade=record["evidence_grade"],
                radio_fitted=bool(record.get("radio_fitted", False)),
                structure=record["structure"],
                gaussian_closure_reliable=bool(record.get("gaussian_closure_reliable_28ghz", False)),
                mean_texture_depth_m=None if texture_mm is None else float(texture_mm) / 1000.0,
                periodic_component=record.get("periodic_component"),
                concepts=tuple(record.get("concepts", ())),
                itu_rows=tuple(record.get("itu_rows", ())),
                provenance={
                    "source": source,
                    "evidence_grade": record["evidence_grade"],
                    "citations": record.get("citations", []),
                    "note": record.get("note", ""),
                    "mean_texture_depth_status": record.get("mean_texture_depth_status"),
                },
            )
            classes[entry.name] = entry
        return cls(source, classes)


#: Tag written into the material table's provenance by :func:`effective_rms_height`.
QUADRATURE_RULE = "quadrature"

#: Tag written by :func:`masonry_equivalent_rms_height`.
MASONRY_RULE = "masonry_two_level"


def effective_rms_height(prior: SurfaceRoughnessPrior) -> float:
    """Wall scale RMS height, folding in the periodic component when present.

    ``config/surface_roughness.json`` is emphatic that the monolithic finish and
    the metre scale facade structure are different quantities. A metre scale
    patch is what a tracer facet stands for, so the periodic relief is the one
    that governs. Where a periodic component is tabulated its relief amplitude
    is combined in quadrature with the finish, which is the crudest defensible
    way to feed a two scale surface into a single Rayleigh closure. It
    overstates the coherent loss for a strictly periodic grating, which
    redirects rather than destroys power, so the resulting specular fractions
    are a lower bound and the diffuse share an upper bound.

    This is the reduction every published number ran through, and it is finding
    2 in ``docs/BUGS.md``: ``unit_scatter_mm`` never enters, so the term the
    Rayleigh closure is wrong for is kept and the term it is right for is
    dropped. The behaviour is preserved here on purpose. Fixing it is a physics
    commit with its own before and after number, not a side effect of a move.
    :func:`masonry_equivalent_rms_height` is the alternative that does read a
    declared unit scatter, and it is not the default.
    """
    finish = float(prior.rms_height_m)
    periodic = prior.periodic_component
    if not periodic:
        return finish
    step_mm = periodic.get("step_height_mm")
    if step_mm is None:
        return finish
    relief = float(step_mm) / 1000.0
    return float(np.hypot(finish, relief / np.sqrt(12.0)))


def masonry_equivalent_rms_height(
    prior: SurfaceRoughnessPrior,
    *,
    brick_format: str = "standard_metric",
    bond: str = "running",
    tolerance_class: str = "R1",
) -> float:
    """RMS height of a coursed wall derived from its construction documents.

    The route :func:`effective_rms_height` does not take. A brick elevation is a
    two level height field, not a Gaussian one: a fraction ``f`` of it is mortar
    sitting ``d`` behind the face, and the rest is brick face scattered about
    the plane by the unit to unit offset ``sigma``. Matching the specular
    retention of that field to ``exp(-(psi s)**2)`` at small phase gives

        ``s**2 = f (1 - f) d**2 + (1 - f) sigma**2``

    Every term is read rather than guessed. ``f`` follows from the unit format
    and the joint width the prior already declares, ``d`` is the prior's own
    ``step_height_mm``, and ``sigma`` is its ``unit_scatter_mm``, falling back
    to the BS EN 771-1 range class evaluated on the unit width. The default
    ``standard_metric`` format is the one the brick row's own
    ``dimensions_status`` cites, 215 by 102.5 by 65 mm on a 10 mm joint, which
    is where its 75 mm course pitch comes from.

    Two refusals, both deliberate. A class the library calls Gaussian has no
    two level field to build, so its median is returned unchanged. A periodic
    class with no joint width is a corrugation rather than a bond, and this
    model does not describe one.

    Not the default anywhere. Reading ``unit_scatter_mm`` at all is what
    finding 2 in ``docs/BUGS.md`` asks for, and switching the default is that
    fix, which belongs with its own before and after number.

    Nothing on this path touches :mod:`~.masonry.rcwa` or the Kirchhoff order
    machinery. It is closed form algebra over the wall's geometry, which is why
    it can be offered while findings 5 and 10 stand.
    """
    if prior.gaussian_model_applies:
        return float(prior.rms_height_m)
    periodic = prior.periodic_component or {}
    joint_mm = periodic.get("joint_width_mm")
    if joint_mm is None:
        raise ValueError(
            f"{prior.name} declares a periodic component with no joint width, so it is a profiled "
            "surface rather than a coursed one and this two level model does not describe it"
        )
    from .masonry import BONDS, BRICK_FORMATS, TOLERANCE_CLASSES, JointGeometry, MasonryWall, equivalent_rms_height_m

    brick = BRICK_FORMATS[brick_format]
    joint_m = float(joint_mm) / 1000.0
    wall = MasonryWall(
        brick=brick,
        joint=JointGeometry(
            bed_m=joint_m,
            perp_m=joint_m,
            recess_m=float(periodic.get("step_height_mm", 0.0)) / 1000.0,
            profile="from_roughness_prior",
            source=f"periodic_component of {prior.name} in config/surface_roughness.json",
        ),
        bond=BONDS[bond],
    )
    scatter_mm = periodic.get("unit_scatter_mm")
    if scatter_mm is None:
        sigma = TOLERANCE_CLASSES[tolerance_class].standard_deviation_m(1000.0 * brick.width_m)
    else:
        sigma = float(scatter_mm) / 1000.0
    return float(equivalent_rms_height_m(wall, piston_sigma_m=sigma))
