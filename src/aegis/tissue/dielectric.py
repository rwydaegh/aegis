"""Tissue electromagnetic model.

TissueModel is the primary data type for tissue properties in AEGIS.
It wraps permittivity, conductivity, and frequency into a frozen dataclass
with derived EM quantities (refractive index, Fresnel transmission) as properties.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aegis.tissue.fresnel import T0 as _T0_from_n
from aegis.tissue.fresnel import n_complex as _n_complex


@dataclass(frozen=True)
class TissueModel:
    """Tissue electromagnetic properties at a specific frequency.

    Parameters
    ----------
    name
        Human-readable label (e.g. "Skin 28 GHz").
    eps_r
        Relative permittivity.
    sigma
        Conductivity (S/m).
    freq_hz
        Frequency (Hz).
    """

    name: str
    eps_r: float
    sigma: float
    freq_hz: float

    @property
    def n_complex(self) -> complex:
        """Complex refractive index."""
        return _n_complex(self.eps_r, self.sigma, self.freq_hz)

    @property
    def T0(self) -> float:
        """Normal-incidence power transmission coefficient."""
        return _T0_from_n(self.n_complex)

    @classmethod
    def from_params(cls, name: str, eps_r: float, sigma: float, freq_hz: float) -> TissueModel:
        """Construct from explicit electromagnetic parameters."""
        return cls(name=name, eps_r=eps_r, sigma=sigma, freq_hz=freq_hz)

    @classmethod
    def from_database(cls, tissue_name: str, freq_hz: float, db_path: Path | None = None) -> TissueModel:
        """Construct from the IT'IS v5.0 database using the Cole-Cole model.

        Parameters
        ----------
        tissue_name
            Tissue name in the database (e.g. "Skin", "Muscle").
        freq_hz
            Frequency (Hz).
        db_path
            Explicit path to itis_v5.db. Auto-detected if None.
        """
        from aegis.tissue.database import get_tissue_properties

        props = get_tissue_properties(tissue_name, freq_hz, db_path=db_path)
        return cls(
            name=f"{tissue_name} {freq_hz / 1e9:.0f} GHz",
            eps_r=props["eps_r"],
            sigma=props["sigma"],
            freq_hz=freq_hz,
        )


# Predefined tissue instances (hardcoded from literature, matching oracle scripts)
SKIN_28GHZ = TissueModel("Skin 28 GHz", eps_r=17.0, sigma=25.0, freq_hz=28e9)
SKIN_60GHZ = TissueModel("Skin 60 GHz", eps_r=7.9, sigma=36.4, freq_hz=60e9)
MUSCLE_28GHZ = TissueModel("Muscle 28 GHz", eps_r=25.0, sigma=30.0, freq_hz=28e9)
FAT_28GHZ = TissueModel("Fat 28 GHz", eps_r=4.0, sigma=2.0, freq_hz=28e9)
