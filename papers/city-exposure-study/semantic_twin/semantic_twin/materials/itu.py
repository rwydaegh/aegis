"""Recommendation ITU-R P.2040-4 Table 3, and what it does not supply.

Every dielectric constant in this study comes from one place: the power law
``eps' = a f_GHz**b`` and ``sigma = c f_GHz**d`` of P.2040-4, loaded from
``config/itu_p2040_4.json``. The recommendation states a validity band per
material and says nothing about the curve outside it, so leaving the band is
opt-in and the result carries an inflated uncertainty multiplier.

What the recommendation does not supply is as important as what it does. It
gives no slab thickness, no surface roughness and no cross-polarisation ratio.
:func:`radio_material_from_roughness` therefore refuses to default any of them
and labels each one in the provenance it writes.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from .roughness import roughness_to_scattering_coefficient


@dataclass(frozen=True)
class MaterialEvaluation:
    name: str
    frequency_hz: float
    relative_permittivity_real: float
    conductivity_s_per_m: float
    relative_permittivity_imag: float
    applicability: str
    uncertainty_multiplier: float
    provenance: dict[str, Any]

    @property
    def complex_relative_permittivity(self) -> complex:
        return complex(self.relative_permittivity_real, -self.relative_permittivity_imag)


@dataclass(frozen=True)
class RadioMaterialParameters:
    """Complete frequency-specific material state consumed by Sionna RT."""

    name: str
    frequency_hz: float
    relative_permittivity: float
    conductivity_s_per_m: float
    thickness_m: float
    scattering_coefficient: float
    xpd_coefficient: float
    scattering_pattern: str
    applicability: str
    provenance: dict[str, Any]

    def __post_init__(self) -> None:
        if self.frequency_hz <= 0.0:
            raise ValueError("frequency must be positive")
        if self.relative_permittivity < 1.0:
            raise ValueError("relative permittivity must be at least one")
        if self.conductivity_s_per_m < 0.0 or self.thickness_m < 0.0:
            raise ValueError("conductivity and thickness must be non-negative")
        if not 0.0 <= self.scattering_coefficient <= 1.0:
            raise ValueError("scattering coefficient must be between zero and one")
        if not 0.0 <= self.xpd_coefficient <= 1.0:
            raise ValueError("XPD coefficient must be between zero and one")


def radio_material_from_roughness(
    evaluation: MaterialEvaluation,
    *,
    name: str,
    thickness_m: float,
    rms_height_m: float,
    reference_incidence_deg: float,
    xpd_coefficient: float,
) -> RadioMaterialParameters:
    """Close an ITU dielectric prior with explicit slab and roughness inputs.

    Thickness, roughness, reference incidence, and XPD must come from scene
    evidence, calibration, or a separately labelled engineering prior. They are
    intentionally not defaulted because Recommendation ITU-R P.2040 does not
    provide them.
    """
    incidence_cosine = np.cos(np.radians(reference_incidence_deg))
    scattering = float(roughness_to_scattering_coefficient(rms_height_m, incidence_cosine, evaluation.frequency_hz))
    provenance = {
        "dielectric_model": evaluation.provenance,
        "roughness_closure": {
            "model": "Gaussian coherent-power loss mapped to Sionna diffuse amplitude",
            "status": "engineering approximation, not ITU-R P.2040",
            "rms_height_m": float(rms_height_m),
            "reference_incidence_deg": float(reference_incidence_deg),
            "limitation": "A single material coefficient approximates an incidence-dependent rough-surface response.",
        },
        "thickness_status": "caller supplied, not ITU-R P.2040",
        "xpd_status": "caller supplied, not ITU-R P.2040",
    }
    return RadioMaterialParameters(
        name=name,
        frequency_hz=evaluation.frequency_hz,
        relative_permittivity=evaluation.relative_permittivity_real,
        conductivity_s_per_m=evaluation.conductivity_s_per_m,
        thickness_m=float(thickness_m),
        scattering_coefficient=scattering,
        xpd_coefficient=float(xpd_coefficient),
        scattering_pattern="lambertian",
        applicability=evaluation.applicability,
        provenance=provenance,
    )


@dataclass(frozen=True)
class PowerLawMaterial:
    name: str
    a: float
    b: float
    c: float
    d: float
    minimum_ghz: float
    maximum_ghz: float
    hard_limit: bool
    eps_fractional_std: float
    sigma_log_std: float
    provenance: dict[str, Any]

    def evaluate(self, frequency_hz: float, *, allow_extrapolation: bool = False) -> MaterialEvaluation:
        """Evaluate the ITU power-law curve, refusing to leave its stated range.

        Recommendation ITU-R P.2040-4 Table 3 states a validity band per
        material and says nothing about the curve outside it. Extrapolation is
        therefore opt-in: a caller that wants an indicative value above the
        band has to ask for it, and gets ``applicability`` set to
        ``indicative_extrapolation`` with an inflated uncertainty multiplier.
        ``hard_limit`` records the rows where even that is not defensible.
        """
        frequency_ghz = frequency_hz / 1e9
        if frequency_ghz <= 0.0:
            raise ValueError("frequency must be positive")
        inside = self.minimum_ghz <= frequency_ghz <= self.maximum_ghz
        if not inside and (self.hard_limit or not allow_extrapolation):
            raise ValueError(
                f"{self.name} is supported over {self.minimum_ghz:g}-{self.maximum_ghz:g} GHz, "
                f"not {frequency_ghz:g} GHz"
            )
        clamped = np.clip(frequency_ghz, self.minimum_ghz, self.maximum_ghz)
        extrapolation_octaves = abs(np.log2(frequency_ghz / clamped))
        applicability = "within_recommendation_range" if inside else "indicative_extrapolation"
        relative_permittivity = self.a * frequency_ghz**self.b
        conductivity = self.c * frequency_ghz**self.d
        imaginary_permittivity = 17.98 * conductivity / frequency_ghz
        return MaterialEvaluation(
            name=self.name,
            frequency_hz=frequency_hz,
            relative_permittivity_real=float(relative_permittivity),
            conductivity_s_per_m=float(conductivity),
            relative_permittivity_imag=float(imaginary_permittivity),
            applicability=applicability,
            uncertainty_multiplier=float(1.0 + extrapolation_octaves),
            provenance=self.provenance,
        )

    def sample(
        self,
        frequency_hz: float,
        count: int,
        rng: np.random.Generator,
        *,
        allow_extrapolation: bool = False,
    ) -> tuple[np.ndarray, np.ndarray]:
        evaluation = self.evaluate(frequency_hz, allow_extrapolation=allow_extrapolation)
        scale = evaluation.uncertainty_multiplier
        eps = rng.normal(
            evaluation.relative_permittivity_real,
            self.eps_fractional_std * scale * evaluation.relative_permittivity_real,
            size=count,
        )
        eps = np.maximum(eps, 1.0)
        if evaluation.conductivity_s_per_m == 0.0:
            sigma = np.zeros(count)
        else:
            sigma = rng.lognormal(
                np.log(evaluation.conductivity_s_per_m),
                self.sigma_log_std * scale,
                size=count,
            )
        return eps, sigma


class MaterialLibrary:
    def __init__(self, source: dict[str, Any], materials: dict[str, PowerLawMaterial]) -> None:
        self.source = source
        self.materials = materials

    def __getitem__(self, name: str) -> PowerLawMaterial:
        return self.materials[name]

    @classmethod
    def load(cls, path: pathlib.Path) -> MaterialLibrary:
        document = json.loads(path.read_text())
        source = document["source"]
        materials = {}
        for record in document["materials"]:
            lower, upper = record["f_ghz"]
            material = PowerLawMaterial(
                name=record["name"],
                a=float(record["a"]),
                b=float(record["b"]),
                c=float(record["c"]),
                d=float(record["d"]),
                minimum_ghz=float(lower),
                maximum_ghz=float(upper),
                hard_limit=bool(record.get("hard_limit", False)),
                eps_fractional_std=float(record.get("eps_fractional_std", 0.2)),
                sigma_log_std=float(record.get("sigma_log_std", 0.6)),
                provenance={**source, "material_record": record["name"]},
            )
            materials[material.name] = material
        return cls(source, materials)
