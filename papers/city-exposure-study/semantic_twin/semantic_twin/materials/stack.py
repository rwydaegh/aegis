"""A facade as layers rather than as one label, and what a posterior over labels is worth.

Two things a single material name cannot express, both of them electromagnetics
rather than image processing, which is why they live here and not in the module
that asks a language model what a wall is made of.

A facade is not a half space. Render over brick, cladding over a ventilated
cavity, a sealed glazing unit: all layered, and at 15 GHz free space is 20 mm, so
a 15 mm coat is most of a wavelength in air and more than one inside a dielectric.
In that regime the stack reduces to neither its coating nor its substrate, and
:func:`layered_power_reflectance` is the transfer matrix that resolves it.

A patch whose material is uncertain does not reflect like its most probable
material. Mixing has to happen in power, because power is what the tracer
carries, and :func:`posterior_power_reflectance` is that mixture in closed form.
:func:`argmax_power_reflectance` is what the pipeline computes instead, kept
alongside so the two can be differenced rather than argued about. A three percent
chance of metal is not a three percent correction.

Nothing here is on the tracer's live path. The tracer takes one permittivity per
class from :func:`~.catalogue.load_table` and has no way to accept a stack.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .catalogue import IMAGE_MATERIALS, MATERIAL_SUBSTITUTION, MATERIAL_VOCABULARY

__all__ = [
    "MATERIAL_VOCABULARY",
    "Layer",
    "argmax_power_reflectance",
    "half_space_power_reflectance",
    "layer_permittivity",
    "layered_power_reflectance",
    "material_power_reflectance",
    "posterior_power_reflectance",
    "stack_power_reflectance",
]


@dataclass(frozen=True)
class Layer:
    """One layer of a facade stack, outermost first.

    ``thickness_mm`` is ``None`` for the substrate, which is treated as a half
    space. Every layer above the substrate must state a thickness, because a
    stack with an unknown interior thickness has no transfer matrix.
    """

    material: str
    thickness_mm: float | None

    def __post_init__(self) -> None:
        if self.material not in MATERIAL_VOCABULARY:
            raise ValueError(f"{self.material!r} is not in the RF material vocabulary")
        if self.thickness_mm is not None and self.thickness_mm <= 0.0:
            raise ValueError("layer thickness must be positive or None for a half space")


def layer_permittivity(material: str, frequency_hz: float, library: Any) -> complex:
    """Complex permittivity of one vocabulary name, through its ITU row."""
    spec = IMAGE_MATERIALS.get(material)
    row = spec.itu_row if spec is not None else MATERIAL_SUBSTITUTION.get(material, material)
    evaluation = library[row].evaluate(frequency_hz)
    return complex(evaluation.relative_permittivity_real, -evaluation.relative_permittivity_imag)


def layered_power_reflectance(
    permittivity: np.ndarray,
    thickness_m: np.ndarray,
    cos_incidence: float,
    frequency_hz: float,
) -> float:
    """Unpolarised power reflectance of a stack over a half space.

    ``permittivity`` is outermost first and its last entry is the substrate,
    which is a half space. ``thickness_m`` has one fewer entry. The recursion is
    the standard impedance transfer down the stack, evaluated separately for the
    two polarisations and averaged in power, which matches what
    ``fresnel_power_reflectance`` in the tracer does for a single interface and
    is the right weight for a depolarised field.

    The reason this exists is that at 15 GHz free space is 20 mm, so a 15 mm
    render coat is three quarters of a wavelength in air and, inside a material
    of relative permittivity near 3, more than a full wavelength. A stack in that
    regime reduces to neither its coating nor its substrate, and the difference
    between the two readings is the physics a single material label throws away.
    """
    permittivity = np.asarray(permittivity, dtype=np.complex128)
    thickness_m = np.asarray(thickness_m, dtype=np.float64)
    if permittivity.ndim != 1 or permittivity.size < 1:
        raise ValueError("permittivity must be a non-empty one dimensional array, outermost first")
    if thickness_m.size != permittivity.size - 1:
        raise ValueError("thickness must have one entry per layer above the substrate")
    if not 0.0 < cos_incidence <= 1.0:
        raise ValueError("cos_incidence must lie in (0, 1]")
    if frequency_hz <= 0.0:
        raise ValueError("frequency must be positive")

    wavenumber = 2.0 * np.pi * frequency_hz / 299792458.0
    sin_sq = 1.0 - cos_incidence**2
    # Transverse wavenumber is conserved across every interface, so each layer's
    # normal component follows from the incident angle alone.
    normal = np.sqrt(permittivity - sin_sq)
    incident_normal = complex(cos_incidence, 0.0)

    total = 0.0
    for polarisation in ("te", "tm"):
        if polarisation == "te":
            impedance = 1.0 / normal
            incident_impedance = 1.0 / incident_normal
        else:
            impedance = normal / permittivity
            incident_impedance = incident_normal
        load = impedance[-1]
        for index in range(permittivity.size - 2, -1, -1):
            phase = wavenumber * normal[index] * thickness_m[index]
            tangent = np.tan(phase)
            load = (
                impedance[index] * (load + 1j * impedance[index] * tangent) / (impedance[index] + 1j * load * tangent)
            )
        gamma = (load - incident_impedance) / (load + incident_impedance)
        total += float(abs(gamma) ** 2)
    return 0.5 * total


def half_space_power_reflectance(permittivity: complex, cos_incidence: float) -> float:
    """The single interface case, for comparison against a stack."""
    return layered_power_reflectance(np.array([permittivity]), np.zeros(0), cos_incidence, 1.0e9)


def stack_power_reflectance(
    stack: tuple[Layer, ...],
    frequency_hz: float,
    cos_incidence: float,
    library: Any,
) -> float:
    """Power reflectance of a model reported stack at one frequency and angle."""
    if not stack:
        raise ValueError("an empty stack has no reflectance")
    permittivity = np.array([layer_permittivity(layer.material, frequency_hz, library) for layer in stack])
    thickness = np.array([layer.thickness_mm for layer in stack[:-1]], dtype=np.float64) / 1000.0
    return layered_power_reflectance(permittivity, thickness, cos_incidence, frequency_hz)


def material_power_reflectance(frequency_hz: float, cos_incidence: float, library: Any) -> dict[str, float]:
    """Half space power reflectance of every vocabulary entry at one geometry.

    ``unknown`` is deliberately absent. A material with no row cannot be given a
    reflectance, and giving it one silently would be the same class of mistake as
    the argmax this module exists to replace.
    """
    out: dict[str, float] = {}
    for material in MATERIAL_VOCABULARY:
        if material == "unknown":
            continue
        permittivity = layer_permittivity(material, frequency_hz, library)
        out[material] = half_space_power_reflectance(permittivity, cos_incidence)
    return out


def posterior_power_reflectance(
    posterior: dict[str, float],
    reflectance: dict[str, float],
    *,
    unknown_policy: str = "renormalise",
) -> float:
    """Ensemble mean reflectance under a material posterior.

    Mixing in power rather than picking a label is the whole point. The two
    differ whenever the posterior is broad, and they differ most when a small
    amount of mass sits on a strong reflector, because power is what the tracer
    carries and a 3 percent chance of metal is not a 3 percent correction.

    ``unknown_policy`` is ``renormalise``, which spreads the unknown mass over
    the materials that do have rows, or ``drop``, which treats an unknown patch
    as contributing nothing. There is no third option that does not invent a
    number.
    """
    mass = {name: float(value) for name, value in posterior.items() if name != "unknown"}
    total = sum(mass.values())
    if total <= 0.0:
        raise ValueError("posterior puts all its mass on unknown, so it has no reflectance")
    if unknown_policy == "renormalise":
        return float(sum(value / total * reflectance[name] for name, value in mass.items()))
    if unknown_policy == "drop":
        return float(sum(value * reflectance[name] for name, value in mass.items()))
    raise ValueError(f"unknown_policy must be 'renormalise' or 'drop', not {unknown_policy!r}")


def argmax_power_reflectance(posterior: dict[str, float], reflectance: dict[str, float]) -> float:
    """What the current pipeline computes: the reflectance of the modal label."""
    ranked = sorted(((value, name) for name, value in posterior.items() if name != "unknown"), reverse=True)
    if not ranked:
        raise ValueError("posterior has no material with a row")
    return float(reflectance[ranked[0][1]])
