"""Vegetation as a participating medium, grounded in Recommendation ITU-R P.833-10.

Why this module is not a material row
-------------------------------------
Every other class in this twin is a surface. Vegetation is not. A canopy is a
sparse cloud of scatterers in air, and the quantity that governs it is an
optical depth along a chord, not a reflection coefficient at an interface.
``config/semantic_concepts.json`` already says so in the ``vegetation_effective``
entry, and until now the pipeline substituted the P.2040-4 ``wood`` row through
``MATERIAL_SUBSTITUTION`` in :mod:`~.catalogue`. That substitution turns a tree
into a smooth slab of timber with an RMS height of 0.05 mm, which is
radio-smooth at every frequency in this study. This module replaces it.

Two independent things are wrong with photogrammetric vegetation, and they need
separating because they push in opposite directions.

The geometry is wrong. Photorealistic 3D Tiles reconstructs a tree as a lumpy
opaque blob, because multi view stereo cannot resolve a canopy of leaves. What
the blob does get roughly right is its silhouette and its depth, which is
exactly the envelope a participating medium needs, and exactly the part that a
surface model throws away.

The material is wrong. The tracer's surface response is
``fresnel_power_reflectance``, a half space reflectance. A leaf is 0.2 mm thick
(Recommendation ITU-R P.833-10, Table 9, "leaves ... 0.02 cm thick"), which is
a small fraction of a wavelength in the leaf at every frequency here, so a half
space reflectance is the wrong limit for a leaf by construction.
:func:`leaf_reflectance_ratio_db` quantifies that, and it is the reason
replacing the blob with explicit procedural leaf geometry would make the
physics worse rather than better while costing far more rays.

What the standard actually supplies
-----------------------------------
Recommendation ITU-R P.833-10 (09/2021), "Attenuation in vegetation", in force,
nominally 30 MHz to 100 GHz. That range is a union over disjoint sub models and
no single model in it is validated across it. The radiative energy transfer
model of section 3.2.1.4 is the only part of the recommendation with a
parameterisation a volume renderer can consume, and its four parameters
(alpha, beta, albedo W, and the combined absorption and scatter coefficient)
are tabulated in Tables 5 to 8 at exactly these frequencies:

    UK species set     1.3, 2, 2.2, 11, 37, 61.5 GHz
    Korean species set 1.5, 2.5, 3.5, 4.5, 5.5, 12.5 GHz

and sparsely even there. Between 12.5 GHz and 37 GHz the tables are empty. At
37 GHz exactly one column exists, London plane in leaf. So for FR3 and FR2 this
recommendation supports interpolation across 1.5 octaves between two different
species sets from two different campaigns, and nothing better. Every function
here that leaves the tabulated grid says so in its return value rather than
returning a bare float.

Provenance of the tables themselves, which matters because ROUGHNESS.md found
the same pattern in facade metrology. The RET theory is Johnson and Schwering,
CECOM-TR-85-1, 1985. The UK rows are one 2002 UK Radiocommunications Agency
project (Rogers et al., QINETIQ/KI/COM/CR020196/1.0). The Korean rows entered
at P.833-6 in 2007. Tables 5 to 8 have not changed since 2005 and 2007
respectively. The specific attenuation curve of Figure 2 is uncited, unchanged
since 1999, and its plotted range ends at about 30 GHz.

The delta-M identity this module leans on
------------------------------------------
Equation (14) of the recommendation defines a reduced albedo
``W_hat = (1 - alpha) W / (1 - alpha W)`` and equation (13) a reduced optical
depth ``tau_hat = tau (1 - alpha W)``. That is the standard delta-M scaling: a
medium whose phase function puts a fraction ``alpha`` of its scattered power
into a narrow forward lobe is equivalent, for everything except the shape of
that lobe, to a medium with a smaller extinction and a smaller albedo and an
isotropic phase function. The recommendation therefore already commits to the
volumetric picture, and a Monte Carlo transport solver with the two lobe phase
function is the same physics its series solution solves, not a different model.
:func:`delta_m_scaling` implements it and ``tests/test_foliage.py`` checks that
the Monte Carlo obeys the identity, which is the strongest available validation
in the absence of measurements.

The recommendation never writes down the functional form of the phase function.
Only alpha and beta are exposed. The Gaussian forward lobe used here is
therefore an interpolation, labelled as one, and the delta-M test is what shows
the answer does not depend on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from .catalogue import MaterialSpec

SPEED_OF_LIGHT = 299_792_458.0

#: Recommendation ITU-R P.833-10 (09/2021), Tables 4 to 8, transcribed from the
#: in force PDF. One record per (species, leaf state, frequency) cell that has
#: entries in all four of Tables 5 to 8. Cells where the recommendation leaves a
#: blank are simply absent, they are not filled in.
#:
#: Fields: species, leaf state, frequency in GHz, alpha (Table 5, forward
#: scattered share of scattered power), beta (Table 6, phase function beamwidth
#: in degrees), albedo W (Table 7), sigma_tau (Table 8, combined absorption and
#: scatter coefficient). The recommendation does not print units for sigma_tau,
#: but section 3.2.1.4 defines ``tau = (sigma_a + sigma_s) z`` with z the
#: distance into the vegetation in metres, so it is per metre, that is nepers
#: per metre.
_RET_ROWS: tuple[tuple[str, str, str, float, float, float, float, float], ...] = (
    # set, species, leaf state, f_GHz, alpha, beta_deg, albedo, sigma_tau_per_m
    ("uk", "horse_chestnut", "in_leaf", 1.3, 0.90, 21.0, 0.25, 0.772),
    ("uk", "horse_chestnut", "in_leaf", 2.0, 0.75, 80.0, 0.55, 0.091),
    ("uk", "horse_chestnut", "in_leaf", 11.0, 0.85, 69.0, 0.95, 0.124),
    ("uk", "silver_maple", "in_leaf", 1.3, 0.95, 14.0, 0.95, 0.241),
    ("uk", "silver_maple", "in_leaf", 11.0, 0.90, 58.0, 0.95, 0.321),
    ("uk", "silver_maple", "in_leaf", 61.5, 0.80, 48.0, 0.80, 0.567),
    ("uk", "silver_maple", "out_of_leaf", 1.3, 0.90, 43.0, 0.25, 0.139),
    ("uk", "silver_maple", "out_of_leaf", 2.0, 0.95, 31.0, 0.95, 0.176),
    ("uk", "silver_maple", "out_of_leaf", 2.2, 0.95, 25.0, 0.95, 0.377),
    ("uk", "london_plane", "in_leaf", 1.3, 0.95, 42.0, 0.95, 0.147),
    ("uk", "london_plane", "in_leaf", 2.0, 0.95, 49.0, 0.95, 0.203),
    ("uk", "london_plane", "in_leaf", 2.2, 0.50, 13.0, 0.45, 0.244),
    ("uk", "london_plane", "in_leaf", 11.0, 0.70, 100.0, 0.95, 0.750),
    ("uk", "london_plane", "in_leaf", 37.0, 0.95, 18.0, 0.95, 0.441),
    ("uk", "london_plane", "in_leaf", 61.5, 0.25, 2.0, 0.50, 0.498),
    ("uk", "london_plane", "out_of_leaf", 1.3, 0.90, 16.0, 0.95, 0.221),
    ("uk", "london_plane", "out_of_leaf", 11.0, 0.95, 19.0, 0.95, 0.459),
    ("uk", "common_lime", "in_leaf", 1.3, 0.90, 76.0, 0.95, 0.220),
    ("uk", "common_lime", "in_leaf", 11.0, 0.95, 78.0, 0.75, 0.560),
    ("uk", "common_lime", "out_of_leaf", 1.3, 0.95, 50.0, 0.95, 0.591),
    ("uk", "common_lime", "out_of_leaf", 2.0, 0.95, 60.0, 0.95, 0.692),
    ("uk", "common_lime", "out_of_leaf", 11.0, 0.95, 48.0, 0.95, 0.757),
    ("uk", "sycamore_maple", "in_leaf", 61.5, 0.90, 59.0, 0.90, 0.647),
    ("uk", "sycamore_maple", "out_of_leaf", 1.3, 0.95, 70.0, 0.85, 0.360),
    ("uk", "sycamore_maple", "out_of_leaf", 2.0, 0.95, 62.0, 0.95, 0.249),
    ("uk", "sycamore_maple", "out_of_leaf", 11.0, 0.95, 44.0, 0.95, 0.179),
    ("kr", "ginkgo", "in_leaf", 1.5, 0.90, 28.65, 0.95, 0.40),
    ("kr", "ginkgo", "in_leaf", 2.5, 0.90, 36.89, 0.92, 1.10),
    ("kr", "ginkgo", "in_leaf", 3.5, 0.30, 57.30, 0.10, 0.30),
    ("kr", "ginkgo", "in_leaf", 4.5, 0.40, 28.65, 0.83, 0.46),
    ("kr", "ginkgo", "in_leaf", 5.5, 0.40, 28.65, 0.90, 0.48),
    ("kr", "ginkgo", "in_leaf", 12.5, 0.20, 3.58, 0.97, 0.74),
    ("kr", "cherry_japanese", "in_leaf", 1.5, 0.95, 57.30, 0.95, 0.30),
    ("kr", "cherry_japanese", "in_leaf", 2.5, 0.93, 57.30, 0.95, 0.49),
    ("kr", "cherry_japanese", "in_leaf", 3.5, 0.90, 114.59, 0.95, 0.21),
    ("kr", "cherry_japanese", "in_leaf", 4.5, 0.90, 114.59, 0.30, 0.20),
    ("kr", "cherry_japanese", "in_leaf", 5.5, 0.95, 229.18, 0.90, 0.24),
    ("kr", "cherry_japanese", "in_leaf", 12.5, 0.16, 3.38, 0.90, 0.18),
    ("kr", "trident_maple", "in_leaf", 1.5, 0.95, 18.47, 0.96, 0.47),
    ("kr", "trident_maple", "in_leaf", 2.5, 0.95, 45.34, 0.95, 0.73),
    ("kr", "trident_maple", "in_leaf", 3.5, 0.95, 13.43, 0.95, 0.73),
    ("kr", "trident_maple", "in_leaf", 4.5, 0.90, 57.30, 0.95, 0.27),
    ("kr", "trident_maple", "in_leaf", 5.5, 0.90, 114.59, 0.95, 0.31),
    ("kr", "trident_maple", "in_leaf", 12.5, 0.25, 4.25, 0.94, 0.47),
    ("kr", "korean_pine", "in_leaf", 1.5, 0.70, 70.0, 0.78, 0.215),
    ("kr", "korean_pine", "in_leaf", 2.5, 0.82, 55.0, 0.92, 0.617),
    ("kr", "korean_pine", "in_leaf", 3.5, 0.74, 72.0, 0.71, 0.334),
    ("kr", "korean_pine", "in_leaf", 4.5, 0.72, 71.0, 0.87, 0.545),
    ("kr", "korean_pine", "in_leaf", 5.5, 0.73, 75.0, 0.75, 0.310),
    ("kr", "korean_pine", "in_leaf", 12.5, 0.23, 4.37, 0.98, 0.500),
    ("kr", "himalayan_cedar", "in_leaf", 1.5, 0.48, 51.5, 0.43, 0.271),
    ("kr", "himalayan_cedar", "in_leaf", 2.5, 0.74, 77.5, 0.71, 0.402),
    ("kr", "himalayan_cedar", "in_leaf", 3.5, 0.92, 103.0, 0.87, 0.603),
    ("kr", "himalayan_cedar", "in_leaf", 4.5, 0.91, 94.0, 0.92, 0.540),
    ("kr", "himalayan_cedar", "in_leaf", 5.5, 0.96, 100.0, 0.97, 0.502),
    ("kr", "himalayan_cedar", "in_leaf", 12.5, 0.27, 3.54, 0.98, 0.900),
    ("kr", "plane_tree_american", "in_leaf", 1.5, 0.95, 61.0, 0.88, 0.490),
    ("kr", "plane_tree_american", "in_leaf", 2.5, 0.74, 23.0, 0.71, 0.486),
    ("kr", "plane_tree_american", "in_leaf", 3.5, 0.85, 105.0, 0.84, 0.513),
    ("kr", "plane_tree_american", "in_leaf", 4.5, 0.75, 65.0, 0.95, 0.691),
    ("kr", "plane_tree_american", "in_leaf", 5.5, 0.70, 77.0, 0.96, 0.558),
    ("kr", "plane_tree_american", "in_leaf", 12.5, 0.71, 2.36, 0.25, 0.170),
    ("kr", "dawn_redwood", "in_leaf", 1.5, 0.93, 44.0, 0.98, 0.261),
    ("kr", "dawn_redwood", "in_leaf", 2.5, 0.82, 71.0, 0.97, 0.350),
    ("kr", "dawn_redwood", "in_leaf", 3.5, 0.85, 65.0, 0.93, 0.370),
    ("kr", "dawn_redwood", "in_leaf", 4.5, 0.89, 34.0, 0.99, 0.266),
    ("kr", "dawn_redwood", "in_leaf", 5.5, 0.82, 77.0, 0.94, 0.200),
    ("kr", "dawn_redwood", "in_leaf", 12.5, 0.21, 2.57, 0.99, 0.440),
)

#: Recommendation ITU-R P.833-10, Table 4. Leaf area index and leaf size, used
#: here only to derive a canopy volume fraction, not to select a species.
LEAF_AREA_INDEX: dict[str, float] = {
    "silver_maple": 1.691,
    "london_plane": 1.930,
    "common_lime": 1.475,
    "sycamore_maple": 1.631,
    "ginkgo": 2.08,
    "cherry_japanese": 1.45,
    "trident_maple": 1.95,
}

#: Recommendation ITU-R P.833-10, Table 9. The one leaf thickness the
#: recommendation prints anywhere, given for the Boxtel oak of the slant path
#: model as "0.02 cm thick".
LEAF_THICKNESS_M = 0.0002

#: Recommendation ITU-R P.833-10, Table 10. Wood relative permittivity at 40%
#: gravimetric moisture and 20 C, as (frequency GHz, eps_real, tan delta). The
#: recommendation gives no leaf permittivity at all, so this is the nearest
#: thing it prints and it is a lower bound on a leaf, which holds more water
#: than 40% moisture wood.
WOOD_DIELECTRIC_P833_TABLE10: tuple[tuple[float, float, float], ...] = (
    (1.0, 7.2, 0.29),
    (2.4, 6.2, 0.30),
    (5.8, 6.0, 0.37),
    (30.0, 5.3, 0.43),
)

#: Frequencies where Tables 5 to 8 have at least one complete cell.
TABULATED_FREQUENCIES_GHZ: tuple[float, ...] = tuple(sorted({row[3] for row in _RET_ROWS}))


@dataclass(frozen=True)
class RetParameters:
    """One cell of Recommendation ITU-R P.833-10 Tables 5 to 8, with its distance.

    ``frequency_gap_octaves`` is how far the requested frequency is from the
    tabulated row, in octaves. It is not a correction, it is a warning, and
    anything above about 0.5 means the recommendation has no data there and the
    number should be swept rather than quoted.
    """

    species: str
    species_set: str
    leaf_state: str
    tabulated_frequency_ghz: float
    requested_frequency_ghz: float
    alpha: float
    phase_beamwidth_deg: float
    albedo: float
    sigma_tau_per_m: float

    @property
    def frequency_gap_octaves(self) -> float:
        return float(abs(np.log2(self.requested_frequency_ghz / self.tabulated_frequency_ghz)))

    @property
    def in_table(self) -> bool:
        return self.frequency_gap_octaves < 1.0e-6

    @property
    def specific_attenuation_db_per_m(self) -> float:
        """``sigma_tau`` read as nepers per metre and converted to dB per metre.

        The constant here is the amplitude conversion, ``20 / ln 10``, and it is
        finding 4 in ``docs/BUGS.md``. Equation (12) of the recommendation reads
        ``Lscat = -10 log10 { e^-tau ... }``, so ``e^-tau`` is a power
        transmittance and the right constant is ``10 / ln 10 = 4.343``. The same
        sigma through :func:`slab_transmission` gives exactly half of what this
        returns, so the module contradicts itself.

        Left wrong on purpose. The fix is its own commit with its own before and
        after number, because ``FOLIAGE.md`` quotes a whole crossing table at
        the doubled optical depth this feeds.
        """
        return float(8.685889638065035 * self.sigma_tau_per_m)

    def provenance(self) -> dict[str, Any]:
        return {
            "recommendation": "ITU-R P.833-10 (09/2021), section 3.2.1.4, Tables 5 to 8",
            "species": self.species,
            "species_set": {
                "uk": "Rogers et al. 2002, QINETIQ/KI/COM/CR020196/1.0",
                "kr": "P.833-6 (2007) contribution",
            }[self.species_set],
            "leaf_state": self.leaf_state,
            "tabulated_frequency_ghz": self.tabulated_frequency_ghz,
            "requested_frequency_ghz": self.requested_frequency_ghz,
            "frequency_gap_octaves": round(self.frequency_gap_octaves, 3),
            "in_table": self.in_table,
            "status": (
                "tabulated"
                if self.in_table
                else "nearest tabulated frequency, the recommendation has no entry at the requested frequency"
            ),
        }


def ret_parameters(
    frequency_hz: float,
    *,
    species: str | None = None,
    leaf_state: str = "in_leaf",
    species_set: str | None = None,
) -> RetParameters:
    """Nearest complete cell of Tables 5 to 8, in log frequency.

    The recommendation's own instruction (section 3.2.1.4) is to "assume the
    nearest match from the species listed to the Tables", so nearest neighbour
    is what it asks for. Nearest is taken in log frequency because the tables
    span 1.3 to 61.5 GHz and a linear metric would make 37 GHz the nearest row
    to 25 GHz while 12.5 GHz is closer by ratio.
    """
    frequency_ghz = float(frequency_hz) / 1.0e9
    if frequency_ghz <= 0.0:
        raise ValueError("frequency must be positive")
    rows = [
        row
        for row in _RET_ROWS
        if (species is None or row[1] == species)
        and (leaf_state is None or row[2] == leaf_state)
        and (species_set is None or row[0] == species_set)
    ]
    if not rows:
        raise KeyError(f"no P.833-10 row for species={species!r} leaf_state={leaf_state!r} set={species_set!r}")
    best = min(rows, key=lambda row: abs(np.log2(frequency_ghz / row[3])))
    return RetParameters(
        species=best[1],
        species_set=best[0],
        leaf_state=best[2],
        tabulated_frequency_ghz=best[3],
        requested_frequency_ghz=frequency_ghz,
        alpha=best[4],
        phase_beamwidth_deg=best[5],
        albedo=best[6],
        sigma_tau_per_m=best[7],
    )


def ret_parameter_envelope(frequency_hz: float, *, leaf_state: str = "in_leaf") -> dict[str, tuple[float, float]]:
    """Min and max of each RET parameter across every species at the nearest rows.

    This is the honest replacement for picking one species. The tables disagree
    with each other by a factor of six in ``sigma_tau`` at 11 to 12.5 GHz, so a
    single species is a choice the evidence does not support and the spread is
    the result.
    """
    species = sorted({row[1] for row in _RET_ROWS if row[2] == leaf_state})
    picks = [ret_parameters(frequency_hz, species=name, leaf_state=leaf_state) for name in species]
    keep = [p for p in picks if p.frequency_gap_octaves <= 1.6] or picks
    return {
        "alpha": (min(p.alpha for p in keep), max(p.alpha for p in keep)),
        "phase_beamwidth_deg": (min(p.phase_beamwidth_deg for p in keep), max(p.phase_beamwidth_deg for p in keep)),
        "albedo": (min(p.albedo for p in keep), max(p.albedo for p in keep)),
        "sigma_tau_per_m": (min(p.sigma_tau_per_m for p in keep), max(p.sigma_tau_per_m for p in keep)),
    }


def figure2_specific_attenuation_db_per_m(frequency_hz: float | np.ndarray) -> np.ndarray:
    """Recommendation ITU-R P.833-10 Figure 2, above the polarisation merge.

    Figure 2 is a graph with no accompanying table, so this is a power law fit
    to a digitisation of the printed curve, ``gamma = 0.19 f_GHz**1.02`` dB/m,
    valid where the two polarisation branches have merged, which is above about
    1 GHz. Treat it as plus or minus 25%.

    Two limits that matter. The recommendation describes Figure 2 as "derived
    from various measurements over the frequency range 30 MHz to about 30 GHz"
    and cites none of them, and the curve is drawn no further than 30 GHz. And
    the figure carries no in leaf or out of leaf split at any frequency, only
    the sentence that at "frequencies of the order of 1 GHz" in leaf attenuation
    is about 20% higher, a sentence that read "10 GHz" in P.833-1 in 1994 and
    was silently rewritten in 1999.
    """
    f_ghz = np.asarray(frequency_hz, dtype=np.float64) / 1.0e9
    return 0.19 * f_ghz**1.02


@dataclass(frozen=True)
class FoliageMedium:
    """A homogeneous participating medium standing in for a canopy volume.

    ``extinction_per_m`` is the combined absorption and scatter coefficient in
    nepers per metre, that is Recommendation ITU-R P.833-10's ``sigma_tau``.
    ``albedo`` is its ``W``, ``forward_fraction`` its ``alpha`` and
    ``phase_beamwidth_deg`` its ``beta``.
    """

    extinction_per_m: float
    albedo: float
    forward_fraction: float
    phase_beamwidth_deg: float
    provenance: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.extinction_per_m < 0.0:
            raise ValueError("extinction must be non-negative")
        if not 0.0 <= self.albedo <= 1.0:
            raise ValueError("albedo must be between zero and one")
        if not 0.0 <= self.forward_fraction <= 1.0:
            raise ValueError("forward fraction must be between zero and one")
        if self.phase_beamwidth_deg <= 0.0:
            raise ValueError("phase beamwidth must be positive")

    @classmethod
    def from_p833(
        cls,
        frequency_hz: float,
        *,
        species: str | None = None,
        leaf_state: str = "in_leaf",
        extinction_per_m: float | None = None,
    ) -> FoliageMedium:
        """Build from the nearest RET table cell, optionally overriding extinction.

        ``extinction_per_m`` is the one parameter a sensitivity study should
        sweep rather than read, because it is the parameter the tables disagree
        on most and the only one the answer is strongly sensitive to.
        """
        p = ret_parameters(frequency_hz, species=species, leaf_state=leaf_state)
        return cls(
            extinction_per_m=p.sigma_tau_per_m if extinction_per_m is None else float(extinction_per_m),
            albedo=p.albedo,
            forward_fraction=p.alpha,
            phase_beamwidth_deg=p.phase_beamwidth_deg,
            provenance=p.provenance() | {"extinction_overridden": extinction_per_m is not None},
        )

    def optical_depth(self, path_length_m: float | np.ndarray) -> np.ndarray:
        """``tau = sigma_tau * z``, section 3.2.1.4."""
        return self.extinction_per_m * np.asarray(path_length_m, dtype=np.float64)

    def reduced(self) -> FoliageMedium:
        """Delta-M scaled equivalent with an isotropic phase function.

        Equations (13) and (14) of Recommendation ITU-R P.833-10 define exactly
        this pair, ``tau_hat = tau (1 - alpha W)`` and
        ``W_hat = (1 - alpha) W / (1 - alpha W)``. Scaling the optical depth is
        the same as scaling the extinction, since the geometry is unchanged.
        """
        scale = 1.0 - self.forward_fraction * self.albedo
        if scale <= 0.0:
            raise ValueError("delta-M scaling degenerates when alpha*W reaches one")
        return FoliageMedium(
            extinction_per_m=self.extinction_per_m * scale,
            albedo=(1.0 - self.forward_fraction) * self.albedo / scale,
            forward_fraction=0.0,
            phase_beamwidth_deg=180.0,
            provenance=self.provenance | {"delta_m": "reduced per ITU-R P.833-10 equations (13) and (14)"},
        )


def delta_m_scaling(alpha: float, albedo: float) -> tuple[float, float]:
    """``(extinction scale, reduced albedo)`` of equations (13) and (14)."""
    scale = 1.0 - alpha * albedo
    if scale <= 0.0:
        raise ValueError("delta-M scaling degenerates when alpha*W reaches one")
    return scale, (1.0 - alpha) * albedo / scale


def sample_phase_function(
    incoming: np.ndarray,
    medium: FoliageMedium,
    rng: np.random.Generator,
) -> np.ndarray:
    """Scattered directions for the two lobe phase function of section 3.2.1.4.

    With probability ``alpha`` the direction is drawn from a forward lobe whose
    full width at half maximum is ``beta``, and otherwise it is isotropic. The
    recommendation exposes ``alpha`` and ``beta`` but never writes the lobe's
    functional form down, so the Gaussian used here is an interpolation. The
    delta-M test in ``tests/test_foliage.py`` is what establishes that the
    escaping power does not depend on that choice.
    """
    count = incoming.shape[0]
    forward = rng.random(count) < medium.forward_fraction
    sigma_rad = np.radians(medium.phase_beamwidth_deg) / (2.0 * np.sqrt(2.0 * np.log(2.0)))
    theta = np.abs(rng.normal(0.0, sigma_rad, size=count))
    cos_theta = np.cos(np.minimum(theta, np.pi))
    isotropic_cos = rng.uniform(-1.0, 1.0, size=count)
    cos_theta = np.where(forward, cos_theta, isotropic_cos)
    sin_theta = np.sqrt(np.maximum(0.0, 1.0 - cos_theta**2))
    phi = rng.uniform(0.0, 2.0 * np.pi, size=count)

    axis = incoming / np.linalg.norm(incoming, axis=1, keepdims=True)
    helper = np.where(np.abs(axis[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
    tangent = np.cross(helper, axis)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    bitangent = np.cross(axis, tangent)
    out = (
        (sin_theta * np.cos(phi))[:, None] * tangent
        + (sin_theta * np.sin(phi))[:, None] * bitangent
        + cos_theta[:, None] * axis
    )
    return out / np.linalg.norm(out, axis=1, keepdims=True)


def canopy_volume_fraction(
    leaf_area_index: float, canopy_depth_m: float, leaf_thickness_m: float = LEAF_THICKNESS_M
) -> float:
    """Leaf material volume per unit canopy volume, from LAI and leaf thickness.

    Leaf area index is one sided leaf area per unit ground area, so the leaf
    material volume per unit ground area is ``LAI * thickness`` and dividing by
    the canopy depth gives the volume fraction. Both inputs come from
    Recommendation ITU-R P.833-10, Table 4 and Table 9, so this is derived from
    the recommendation rather than fitted.
    """
    if canopy_depth_m <= 0.0:
        raise ValueError("canopy depth must be positive")
    return float(leaf_area_index * leaf_thickness_m / canopy_depth_m)


def canopy_boundary_reflectance(
    leaf_area_index: float,
    canopy_depth_m: float,
    leaf_permittivity: complex = complex(25.0, -10.0),
    leaf_thickness_m: float = LEAF_THICKNESS_M,
) -> dict[str, float]:
    """Fresnel reflectance of the air to canopy interface, via Maxwell Garnett.

    This is the number that decides whether a canopy has a boundary at all. A
    Maxwell Garnett mixture of leaf material at volume fraction ``f_v`` in air
    has ``eps_eff = 1 + 3 f_v (eps_l - 1)/(eps_l + 2)`` to first order in
    ``f_v``, and with the LAI and leaf thickness the recommendation prints,
    ``f_v`` is of order 1e-4. The resulting normal incidence power reflectance
    is of order 1e-9, that is roughly 90 dB below the reflectance the pipeline
    currently gives a tree by substituting the P.2040-4 wood row.

    So there is no interface. Putting a Fresnel surface on the canopy hull
    invents a reflection that the medium does not have, and that is the single
    largest error in the surface treatment.
    """
    f_v = canopy_volume_fraction(leaf_area_index, canopy_depth_m, leaf_thickness_m)
    eps_eff = 1.0 + 3.0 * f_v * (leaf_permittivity - 1.0) / (leaf_permittivity + 2.0)
    n_eff = np.sqrt(eps_eff)
    reflectance = float(np.abs((1.0 - n_eff) / (1.0 + n_eff)) ** 2)
    wood = complex(1.99, -0.0)
    n_wood = np.sqrt(wood)
    wood_reflectance = float(np.abs((1.0 - n_wood) / (1.0 + n_wood)) ** 2)
    return {
        "volume_fraction": f_v,
        "effective_permittivity_real": float(np.real(eps_eff)),
        "normal_incidence_reflectance": reflectance,
        "p2040_wood_normal_incidence_reflectance": wood_reflectance,
        "excess_of_wood_substitution_db": float(10.0 * np.log10(wood_reflectance / max(reflectance, 1.0e-300))),
    }


def _half_space_reflection(cos_i: np.ndarray, permittivity: complex) -> tuple[np.ndarray, np.ndarray]:
    cos_i = np.clip(cos_i, 0.0, 1.0).astype(np.complex128)
    root = np.sqrt(permittivity - (1.0 - cos_i**2))
    te = (cos_i - root) / (cos_i + root)
    tm = (permittivity * cos_i - root) / (permittivity * cos_i + root)
    return te, tm


def leaf_reflectance_ratio_db(
    frequency_hz: float,
    incidence_deg: float | np.ndarray = 45.0,
    *,
    thickness_m: float = LEAF_THICKNESS_M,
    permittivity: complex | None = None,
) -> dict[str, np.ndarray]:
    """How wrong a half space Fresnel model is for a single leaf.

    The tracer's surface response, ``fresnel_power_reflectance``, is a half
    space reflectance. A leaf is a slab 0.2 mm thick. For a slab the coherent
    reflectance is the two interface sum

        ``Gamma_slab = r (1 - e^{-2 j delta}) / (1 - r^2 e^{-2 j delta})``

    with ``delta = 2 pi d sqrt(eps - sin^2 theta) / lambda`` the one way
    electrical thickness. As ``delta`` goes to zero so does the reflectance,
    because the two interfaces cancel. The half space limit is only reached when
    the slab is many wavelengths thick, which a leaf never is.

    The returned ``excess_db`` is what a tracer would over-report per leaf face
    if explicit leaf geometry were substituted for the canopy blob and the
    existing half space material model were applied to it. That is the
    quantitative reason not to replace the blob with procedural leaves.
    """
    if permittivity is None:
        eps_real = float(
            np.interp(
                frequency_hz / 1.0e9,
                [row[0] for row in WOOD_DIELECTRIC_P833_TABLE10],
                [row[1] for row in WOOD_DIELECTRIC_P833_TABLE10],
            )
        )
        tan_delta = float(
            np.interp(
                frequency_hz / 1.0e9,
                [row[0] for row in WOOD_DIELECTRIC_P833_TABLE10],
                [row[2] for row in WOOD_DIELECTRIC_P833_TABLE10],
            )
        )
        permittivity = complex(eps_real, -eps_real * tan_delta)
    wavelength = SPEED_OF_LIGHT / float(frequency_hz)
    cos_i = np.cos(np.radians(np.asarray(incidence_deg, dtype=np.float64)))
    sin_sq = 1.0 - cos_i**2
    te, tm = _half_space_reflection(cos_i, permittivity)
    half_space = 0.5 * (np.abs(te) ** 2 + np.abs(tm) ** 2)

    root = np.sqrt(permittivity - sin_sq)
    phase = np.exp(-2.0j * (2.0 * np.pi * thickness_m * root / wavelength))
    slab_te = te * (1.0 - phase) / (1.0 - te**2 * phase)
    slab_tm = tm * (1.0 - phase) / (1.0 - tm**2 * phase)
    slab = 0.5 * (np.abs(slab_te) ** 2 + np.abs(slab_tm) ** 2)
    return {
        "half_space_reflectance": np.asarray(half_space, dtype=np.float64),
        "slab_reflectance": np.asarray(slab, dtype=np.float64),
        "excess_db": np.asarray(10.0 * np.log10(half_space / np.maximum(slab, 1.0e-300)), dtype=np.float64),
        "electrical_thickness_rad": np.asarray(
            np.real(2.0 * np.pi * thickness_m * root / wavelength), dtype=np.float64
        ),
        "permittivity": permittivity,
    }


class CanopyCanyonGeometry:
    """A street canyon with an optional canopy box, all analytic.

    Faces are ``0`` ground, ``1`` and ``2`` the two facades, ``3`` the canopy
    box. Everything is a plane or an axis aligned box so the sweep costs no mesh
    and the canopy solid angle is set exactly by one number.

    The canopy is a box because a sensitivity study needs a canopy fraction it
    can dial, not a tree it can render. The conclusion transfers because what
    the medium sees is a chord length distribution and a subtended solid angle,
    and a box supplies both.
    """

    def __init__(
        self,
        *,
        street_width_m: float = 18.0,
        street_length_m: float = 120.0,
        facade_height_m: float = 18.0,
        canopy_half_width_m: float = 0.0,
        canopy_base_m: float = 4.0,
        canopy_depth_m: float = 6.0,
    ) -> None:
        self.street_width_m = float(street_width_m)
        self.street_length_m = float(street_length_m)
        self.facade_height_m = float(facade_height_m)
        self.canopy_half_width_m = float(canopy_half_width_m)
        self.canopy_base_m = float(canopy_base_m)
        self.canopy_depth_m = float(canopy_depth_m)
        self.has_canopy = self.canopy_half_width_m > 0.0 and self.canopy_depth_m > 0.0

    @property
    def canopy_face(self) -> int:
        return 3

    def _box_hit(
        self, origins: np.ndarray, directions: np.ndarray, low: np.ndarray, high: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        with np.errstate(divide="ignore", invalid="ignore"):
            inv = 1.0 / directions
            t0 = (low - origins) * inv
            t1 = (high - origins) * inv
        t_near = np.minimum(t0, t1)
        t_far = np.maximum(t0, t1)
        enter = np.nanmax(t_near, axis=1)
        exit_ = np.nanmin(t_far, axis=1)
        hit = (exit_ > np.maximum(enter, 0.0)) & np.isfinite(enter)
        distance = np.where(enter > 0.0, enter, exit_)
        hit &= distance > 0.0
        axis = np.argmax(np.where(np.isfinite(t_near), t_near, -np.inf), axis=1)
        inside = enter <= 0.0
        axis_out = np.where(inside, np.argmin(np.where(np.isfinite(t_far), t_far, np.inf), axis=1), axis)
        normal = np.zeros_like(origins)
        rows = np.arange(origins.shape[0])
        normal[rows, axis_out] = -np.sign(directions[rows, axis_out])
        return hit, distance, normal

    def intersect(
        self, origins: np.ndarray, directions: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        count = origins.shape[0]
        infinity = 1.0e30
        best_t = np.full(count, infinity)
        best_normal = np.zeros((count, 3))
        best_normal[:, 2] = 1.0
        best_face = np.zeros(count, dtype=np.int64)

        def offer(hit: np.ndarray, t: np.ndarray, normal: np.ndarray, face: int) -> None:
            take = hit & (t < best_t) & (t > 0.0)
            best_t[take] = t[take]
            best_normal[take] = normal[take]
            best_face[take] = face

        half = 0.5 * self.street_width_m
        length = 0.5 * self.street_length_m

        with np.errstate(divide="ignore", invalid="ignore"):
            t_ground = -origins[:, 2] / directions[:, 2]
        point = origins + np.where(np.isfinite(t_ground), t_ground, 0.0)[:, None] * directions
        ground_hit = (
            np.isfinite(t_ground) & (t_ground > 0.0) & (np.abs(point[:, 0]) <= half) & (np.abs(point[:, 1]) <= length)
        )
        ground_normal = np.tile(np.array([0.0, 0.0, 1.0]), (count, 1))
        offer(ground_hit, np.where(np.isfinite(t_ground), t_ground, infinity), ground_normal, 0)

        for face, x_plane in ((1, -half), (2, half)):
            with np.errstate(divide="ignore", invalid="ignore"):
                t_wall = (x_plane - origins[:, 0]) / directions[:, 0]
            point = origins + np.where(np.isfinite(t_wall), t_wall, 0.0)[:, None] * directions
            wall_hit = (
                np.isfinite(t_wall)
                & (t_wall > 0.0)
                & (point[:, 2] >= 0.0)
                & (point[:, 2] <= self.facade_height_m)
                & (np.abs(point[:, 1]) <= length)
            )
            wall_normal = np.zeros((count, 3))
            wall_normal[:, 0] = -np.sign(x_plane)
            offer(wall_hit, np.where(np.isfinite(t_wall), t_wall, infinity), wall_normal, face)

        if self.has_canopy:
            low = np.array([-self.canopy_half_width_m, -length, self.canopy_base_m])
            high = np.array([self.canopy_half_width_m, length, self.canopy_base_m + self.canopy_depth_m])
            box_hit, box_t, box_normal = self._box_hit(origins, directions, low[None, :], high[None, :])
            offer(box_hit, np.where(box_hit, box_t, infinity), box_normal, self.canopy_face)

        hit = best_t < infinity
        return hit, np.where(hit, best_t, infinity), best_normal, best_face


@dataclass
class FoliageTraceResult:
    """What one sweep point produces. Scalars only, like the rest of the twin."""

    susceptibility: dict[str, float]
    canopy_solid_angle_fraction: float
    sky_fraction: float
    mean_surface_bounces: float
    mean_medium_collisions: float
    absorbed_in_medium_fraction: float
    truncated_fraction: float
    rays: int
    seconds: float

    def as_dict(self) -> dict[str, Any]:
        out = dict(self.__dict__)
        out["susceptibility"] = dict(self.susceptibility)
        return out


class FoliageTracer:
    """Adjoint shoot and bounce with an optional participating medium region.

    Deliberately a separate estimator from
    :class:`semantic_twin.transport.tracer.SbrTracer` rather than a change to
    it, because that module is shared. It reproduces the same susceptibility to
    Monte Carlo error when the medium is absent, which
    ``tests/test_foliage.py`` checks against the closed form ground plane, and
    it is the identity that makes the three treatments comparable.

    The estimator is the direct form of the same integral:
    ``chi = (4 pi / N) sum_i throughput_i Q(u_exit,i)`` for directions sampled
    uniformly on the sphere. In free space every throughput is one and the sum
    is the mean of ``Q``, which is ``1/(4 pi)``, so ``chi`` is one.
    """

    def __init__(
        self,
        geometry: CanopyCanyonGeometry,
        *,
        permittivity: np.ndarray,
        rms_height_m: np.ndarray,
        frequency_hz: float,
        medium: FoliageMedium | None = None,
        canopy_is_surface: bool = False,
        rays: int = 200_000,
        max_events: int = 256,
        max_surface_bounces: int = 12,
        ray_epsilon_m: float = 1.0e-4,
        seed: int = 0,
    ) -> None:
        self.geometry = geometry
        self.permittivity = np.asarray(permittivity, dtype=np.complex128)
        self.rms_height_m = np.asarray(rms_height_m, dtype=np.float64)
        self.frequency_hz = float(frequency_hz)
        self.wavelength_m = SPEED_OF_LIGHT / self.frequency_hz
        self.medium = medium
        self.canopy_is_surface = bool(canopy_is_surface)
        self.rays = int(rays)
        self.max_events = int(max_events)
        self.max_surface_bounces = int(max_surface_bounces)
        self.ray_epsilon_m = float(ray_epsilon_m)
        self.seed = int(seed)
        if medium is not None and canopy_is_surface:
            raise ValueError("a canopy is either a medium or a surface, not both")

    def trace(self, origin: np.ndarray, models: dict[str, Any]) -> FoliageTraceResult:
        import time

        from ..illumination import sample_sphere
        from ..transport.tracer import fresnel_power_reflectance, specular_share

        started = time.perf_counter()
        rng = np.random.default_rng(self.seed)
        count = self.rays
        normalisations = {name: model.normalisation() for name, model in models.items()}
        accumulated = {name: 0.0 for name in models}

        direction = sample_sphere(count, rng)
        position = np.tile(np.asarray(origin, dtype=np.float64), (count, 1))
        throughput = np.ones(count)
        # Finding 9 in ``docs/BUGS.md``. This asserts that every ray starts
        # outside the canopy hull, and nothing checks it. An observer inside the
        # hull inverts the parity flag for the whole trace and the ray then
        # collides in vacuum forever: chi comes back exactly 0.000000 against an
        # exact 0.26244, and absorbed_in_medium_fraction reads 1.0000, which is
        # impossible at albedo 0.9. It does not fire in run_foliage_study.py,
        # where the observer sits at 1.5 m and the canopy base at 4.0 m. Left as
        # it is so the fix carries its own before and after number.
        inside = np.zeros(count, dtype=bool)
        surface_bounces = np.zeros(count, dtype=np.int64)
        collisions = np.zeros(count, dtype=np.int64)
        alive = np.arange(count)
        first_hit_face = np.full(count, -1, dtype=np.int64)
        first_hit_seen = np.zeros(count, dtype=bool)

        escaped_direct = 0
        absorbed = 0
        truncated_weight = 0.0

        for _ in range(self.max_events):
            if alive.size == 0:
                break
            origins = position[alive] + self.ray_epsilon_m * direction[alive]
            hit, distance, normal, face = self.geometry.intersect(origins, direction[alive])

            fresh = ~first_hit_seen[alive]
            if np.any(fresh):
                index = alive[fresh]
                first_hit_face[index] = np.where(hit[fresh], face[fresh], -1)
                first_hit_seen[index] = True

            if self.medium is not None:
                free_flight = -np.log(np.maximum(rng.random(alive.size), 1.0e-300)) / max(
                    self.medium.extinction_per_m, 1.0e-300
                )
                collide = inside[alive] & (free_flight < distance)
            else:
                free_flight = np.zeros(alive.size)
                collide = np.zeros(alive.size, dtype=bool)

            escaping = (~hit) & (~collide)
            if np.any(escaping):
                index = alive[escaping]
                exit_direction = direction[index]
                for name, model in models.items():
                    accumulated[name] += float(
                        np.sum(throughput[index] * model.density(exit_direction, normalisations[name]))
                    )
                escaped_direct += int(np.count_nonzero(surface_bounces[index] == 0))

            keep = ~escaping
            alive = alive[keep]
            if alive.size == 0:
                break
            hit = hit[keep]
            distance = distance[keep]
            normal = normal[keep]
            face = face[keep]
            collide = collide[keep]
            free_flight = free_flight[keep]

            if np.any(collide):
                index = alive[collide]
                position[index] = position[index] + free_flight[collide][:, None] * direction[index]
                collisions[index] += 1
                survive = rng.random(index.size) < self.medium.albedo
                absorbed += int(np.count_nonzero(~survive))
                scattered = index[survive]
                if scattered.size:
                    direction[scattered] = sample_phase_function(direction[scattered], self.medium, rng)
                dead = index[~survive]
                if dead.size:
                    throughput[dead] = 0.0

            surface = ~collide
            if np.any(surface):
                index = alive[surface]
                position[index] = position[index] + (distance[surface] + self.ray_epsilon_m)[:, None] * direction[index]
                face_here = face[surface]
                normal_here = normal[surface]

                canopy = face_here == self.geometry.canopy_face
                if self.medium is not None and np.any(canopy):
                    # No dielectric interface. See canopy_boundary_reflectance.
                    crossing = index[canopy]
                    inside[crossing] = ~inside[crossing]

                opaque = ~canopy if self.medium is not None else np.ones(index.size, dtype=bool)
                if np.any(opaque):
                    idx = index[opaque]
                    incoming = direction[idx]
                    n = normal_here[opaque]
                    facing = np.sign(-np.einsum("ij,ij->i", incoming, n))
                    facing[facing == 0.0] = 1.0
                    n = n * facing[:, None]
                    cos_i = np.clip(-np.einsum("ij,ij->i", incoming, n), 0.0, 1.0)
                    klass = face_here[opaque]
                    reflectance = fresnel_power_reflectance(cos_i, self.permittivity[klass])
                    share = specular_share(self.rms_height_m[klass], cos_i, self.wavelength_m)
                    throughput[idx] *= reflectance
                    take_specular = rng.random(idx.size) < share
                    mirror = incoming - 2.0 * np.einsum("ij,ij->i", incoming, n)[:, None] * n
                    diffuse = _cosine_hemisphere(n, rng)
                    new_direction = np.where(take_specular[:, None], mirror, diffuse)
                    direction[idx] = new_direction / np.linalg.norm(new_direction, axis=1, keepdims=True)
                    surface_bounces[idx] += 1

            live = (throughput[alive] > 0.0) & (surface_bounces[alive] <= self.max_surface_bounces)
            alive = alive[live]
            if alive.size == 0:
                break
            deep = surface_bounces[alive] >= 3
            if np.any(deep):
                index = alive[deep]
                probability = np.clip(throughput[index], 0.05, 1.0)
                survive = rng.random(index.size) < probability
                throughput[index] /= probability
                alive = np.concatenate([alive[~deep], index[survive]])
        else:
            truncated_weight = float(throughput[alive].sum())

        canopy_fraction = float(np.count_nonzero(first_hit_face == self.geometry.canopy_face) / count)
        susceptibility = {name: 4.0 * np.pi * value / count for name, value in accumulated.items()}
        return FoliageTraceResult(
            susceptibility=susceptibility,
            canopy_solid_angle_fraction=canopy_fraction,
            sky_fraction=escaped_direct / count,
            mean_surface_bounces=float(surface_bounces.mean()),
            mean_medium_collisions=float(collisions.mean()),
            absorbed_in_medium_fraction=absorbed / count,
            truncated_fraction=truncated_weight / count,
            rays=count,
            seconds=time.perf_counter() - started,
        )


def _cosine_hemisphere(normals: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    count = normals.shape[0]
    u1 = rng.random(count)
    u2 = rng.random(count)
    radius = np.sqrt(u1)
    phi = 2.0 * np.pi * u2
    x = radius * np.cos(phi)
    y = radius * np.sin(phi)
    z = np.sqrt(np.maximum(0.0, 1.0 - u1))
    helper = np.where(np.abs(normals[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
    tangent = np.cross(helper, normals)
    tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
    bitangent = np.cross(normals, tangent)
    return x[:, None] * tangent + y[:, None] * bitangent + z[:, None] * normals


def medium_for_spec(
    spec: MaterialSpec,
    frequency_hz: float,
    *,
    species: str | None = None,
    leaf_state: str = "in_leaf",
    extinction_per_m: float | None = None,
) -> FoliageMedium | None:
    """The participating medium a material spec asks for, or ``None``.

    This is the one place the catalogue and this module meet. A spec whose
    ``medium`` is :data:`~.catalogue.P833_CANOPY` is a volume rather than an
    interface, and it resolves to a P.833 medium here; every other spec returns
    ``None`` and stays a surface.

    What it does not do is make the tracer use it. ``SbrTracer`` reflects off
    every face it hits, so the vegetation faces of a live run still take the
    P.2040 vacuum row that :data:`~.catalogue.IMAGE_MATERIALS` gives them. What
    this closes is the gap that made that unavoidable: a transport estimator can
    now ask a binding which of its classes are media, through
    :attr:`~.catalogue.MaterialTable.media`, instead of the fact living in a
    comment. :class:`FoliageTracer` is the estimator that already carries the
    volume, on analytic geometry.
    """
    from .catalogue import P833_CANOPY

    if spec.medium is None:
        return None
    if spec.medium != P833_CANOPY:
        raise ValueError(f"no participating medium model named {spec.medium!r}")
    return FoliageMedium.from_p833(
        frequency_hz,
        species=species,
        leaf_state=leaf_state,
        extinction_per_m=extinction_per_m,
    )


def slab_transmission(medium: FoliageMedium, depth_m: float) -> float:
    """Coherent through power of a slab, ``exp(-tau)``, the Beer-Lambert limit.

    This is the quantity the recommendation's ``exp(-tau)`` leading term in
    equation (12) carries, and the reference the Monte Carlo has to reproduce
    when the albedo is zero.
    """
    return float(np.exp(-medium.optical_depth(depth_m)))
