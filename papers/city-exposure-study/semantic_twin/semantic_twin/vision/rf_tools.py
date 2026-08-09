"""Small numerical RF workbench exposed to exploratory vision agents."""

from __future__ import annotations

import pathlib
from functools import lru_cache
from typing import Any

import numpy as np

from semantic_twin.materials.itu import MaterialLibrary
from semantic_twin.materials.roughness import (
    SurfaceRoughnessLibrary,
    rayleigh_roughness_parameter,
    rayleigh_smooth_threshold_m,
    specular_power_fraction,
)
from semantic_twin.materials.stack import half_space_power_reflectance

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"


@lru_cache(maxsize=1)
def _materials() -> MaterialLibrary:
    return MaterialLibrary.load(CONFIG / "itu_p2040_4.json")


@lru_cache(maxsize=1)
def _roughness() -> SurfaceRoughnessLibrary:
    return SurfaceRoughnessLibrary.load(CONFIG / "surface_roughness.json")


def itu_material_state(material: str, frequency_ghz: float) -> dict[str, Any]:
    """Evaluate one named ITU-R P.2040 row at the requested carrier."""
    evaluation = _materials()[material].evaluate(float(frequency_ghz) * 1e9)
    return {
        "material": material,
        "frequency_ghz": float(frequency_ghz),
        "relative_permittivity_real": evaluation.relative_permittivity_real,
        "relative_permittivity_imag": evaluation.relative_permittivity_imag,
        "conductivity_s_per_m": evaluation.conductivity_s_per_m,
        "applicability": evaluation.applicability,
    }


def roughness_priors(*, itu_material: str | None = None, query: str = "") -> list[dict[str, Any]]:
    """Find measured or engineering roughness priors relevant to a visual hypothesis."""
    words = {word for word in query.lower().replace("_", " ").split() if len(word) > 2}
    matches = []
    for prior in _roughness().classes.values():
        concept_text = " ".join(prior.concepts).lower()
        name_text = prior.name.lower().replace("_", " ")
        material_match = itu_material is None or itu_material in prior.itu_rows
        query_match = not words or any(word in concept_text or word in name_text for word in words)
        if not material_match or not query_match:
            continue
        matches.append(
            {
                "name": prior.name,
                "rms_height_mm": 1000.0 * prior.rms_height_m,
                "plausible_range_mm": [1000.0 * value for value in prior.plausible_range_m],
                "evidence_grade": prior.evidence_grade,
                "structure": prior.structure,
                "concepts": list(prior.concepts),
                "itu_rows": list(prior.itu_rows),
                "note": prior.provenance.get("note", ""),
            }
        )
    return matches


def rough_surface_response(rms_height_mm: float, frequency_ghz: float, incidence_deg: float) -> dict[str, float | bool]:
    """Evaluate the classic Gaussian rough-surface closure for one RMS guess."""
    if rms_height_mm < 0.0:
        raise ValueError("rms_height_mm must be nonnegative")
    if not 0.0 <= incidence_deg <= 90.0:
        raise ValueError("incidence_deg must lie in [0, 90]")
    frequency_hz = float(frequency_ghz) * 1e9
    cosine = float(np.cos(np.radians(incidence_deg)))
    rms_m = float(rms_height_mm) / 1000.0
    g = float(rayleigh_roughness_parameter(rms_m, cosine, frequency_hz))
    coherent = float(specular_power_fraction(rms_m, cosine, frequency_hz))
    threshold_mm = float(1000.0 * rayleigh_smooth_threshold_m(frequency_hz, cosine))
    return {
        "rms_height_mm": float(rms_height_mm),
        "frequency_ghz": float(frequency_ghz),
        "incidence_deg": float(incidence_deg),
        "rayleigh_parameter_g": g,
        "coherent_specular_power_fraction": coherent,
        "noncoherent_power_fraction": 1.0 - coherent,
        "rayleigh_smooth_threshold_mm": threshold_mm,
        "rayleigh_smooth": bool(rms_height_mm < threshold_mm),
    }


def compare_surface_hypotheses(
    hypotheses: list[dict[str, Any]], frequency_ghz: float, incidence_deg: float
) -> list[dict[str, Any]]:
    """Compare material and RMS guesses at one path interaction."""
    if not hypotheses:
        raise ValueError("at least one hypothesis is required")
    cosine = float(np.cos(np.radians(incidence_deg)))
    out = []
    for hypothesis in hypotheses:
        label = str(hypothesis.get("label", hypothesis["itu_material"]))
        material = str(hypothesis["itu_material"])
        rms_height_mm = float(hypothesis["rms_height_mm"])
        state = itu_material_state(material, frequency_ghz)
        permittivity = complex(state["relative_permittivity_real"], -state["relative_permittivity_imag"])
        reflectance = half_space_power_reflectance(permittivity, cosine)
        rough = rough_surface_response(rms_height_mm, frequency_ghz, incidence_deg)
        coherent = float(rough["coherent_specular_power_fraction"])
        out.append(
            {
                "label": label,
                "itu_material": material,
                "rms_height_mm": rms_height_mm,
                "smooth_interface_power_reflectance": reflectance,
                "coherent_reflected_power": reflectance * coherent,
                "noncoherent_reflected_power": reflectance * (1.0 - coherent),
                "coherent_specular_power_fraction": coherent,
                "relative_permittivity": [
                    state["relative_permittivity_real"],
                    -state["relative_permittivity_imag"],
                ],
                "conductivity_s_per_m": state["conductivity_s_per_m"],
            }
        )
    return out
