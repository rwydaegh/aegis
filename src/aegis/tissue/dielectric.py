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

_tissue_db_props_cache: dict[tuple[str, float], dict[str, float]] = {}


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

    def __post_init__(self) -> None:
        if self.freq_hz <= 0:
            raise ValueError(f"Frequency must be positive, got {self.freq_hz} Hz")

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

    def plot_spectrum(
        self,
        freq_min_hz: float = 1e9,
        freq_max_hz: float = 100e9,
        *,
        n_points: int = 200,
    ):
        """Plot permittivity and conductivity vs frequency for this tissue.

        Uses the IT'IS Cole-Cole database. The tissue name (first word of
        ``self.name``) is used as the database lookup key.

        Requires ``aegis[viz]`` (matplotlib).

        Parameters
        ----------
        freq_min_hz : float
            Lower frequency bound [Hz].
        freq_max_hz : float
            Upper frequency bound [Hz].
        n_points : int
            Number of frequency samples.
        """
        from aegis.viz import plot_tissue_spectrum

        tissue_name = self.name.split()[0]
        return plot_tissue_spectrum(tissue_name, freq_min_hz, freq_max_hz, n_points=n_points)

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

        key = (tissue_name, float(freq_hz))
        if key not in _tissue_db_props_cache:
            _tissue_db_props_cache[key] = get_tissue_properties(tissue_name, freq_hz, db_path=db_path)
        props = _tissue_db_props_cache[key]
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
