"""Body side: hand the angular power spectrum to AEGIS and read back dosimetry.

MONOSTATIC_SBR.md section 2.6 says the environment side and the body side are
computed independently and composed by a dot product of two spherical
functions. That is exactly what happens here. The tracer produces
`rho(k_hat)`, AEGIS owns `Sab(r) = Sinc * T0 * ReLU[n_hat(r) . (-k_hat)]`, and
this module is only the adapter between them. No dosimetry is reimplemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class BodyExposure:
    """Per location dosimetry, reduced to scalars."""

    #: `S0`, the free space incident power density the network would deliver
    #: here with no local scene. The scale factor the caller owns.
    reference_s0_w_m2: float
    #: The power density actually arriving at the point once the scene has had
    #: its say, that is the integral of `rho` over the sphere times `S0`.
    arriving_power_density_w_m2: float
    #: Their ratio, which is the susceptibility. Independent of network power,
    #: so this is the number that transfers between sites.
    susceptibility: float
    peak_sab_w_m2: float
    mean_sab_w_m2: float
    absorbed_power_w: float
    sar_wb_w_kg: float

    def as_dict(self) -> dict[str, float]:
        return dict(self.__dict__)


class BodyCoupler:
    """Wraps one AEGIS phantom and one tissue model."""

    def __init__(
        self,
        phantom_path: str,
        frequency_hz: float,
        *,
        level: int = 2,
        body_mass_kg: float | None = None,
    ) -> None:
        from aegis.engine import DosimetryEngine
        from aegis.geometry.mesh import BodyMesh
        from aegis.tissue import TissueModel

        self.body = BodyMesh.load(phantom_path)
        self.tissue = TissueModel.from_database("Skin", frequency_hz)
        self.engine = DosimetryEngine(self.tissue)
        self.level = int(level)
        self.body_mass_kg = body_mass_kg
        self.frequency_hz = float(frequency_hz)

    def couple(
        self,
        local_grid: np.ndarray,
        rho: np.ndarray,
        solid_angle: float,
        reference_s0_w_m2: float,
    ) -> BodyExposure:
        """Compose the traced angular spectrum with the body's absorption.

        ``rho`` is in sr^-1 and normalised so that its integral over the sphere
        is the susceptibility. ``reference_s0_w_m2`` is the free space incident
        power density `S0` that the network would deliver at this point in the
        absence of the local scene, so the absolute scale sits in one explicit
        factor and every result is linear in it.
        """
        from aegis.paths import PropagationPaths

        power = rho * solid_angle * reference_s0_w_m2
        keep = power > 0.0
        if not np.any(keep):
            return BodyExposure(reference_s0_w_m2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        # Reciprocity dictionary of section 2.3: k_hat = -u_0.
        paths = PropagationPaths.from_powers(-local_grid[keep], power[keep])
        result = self.engine.compute(self.body, paths, level=self.level, body_mass=self.body_mass_kg)
        sab = np.asarray(result.sab, dtype=np.float64)
        arriving = float(power.sum())
        return BodyExposure(
            reference_s0_w_m2=float(reference_s0_w_m2),
            arriving_power_density_w_m2=arriving,
            susceptibility=arriving / reference_s0_w_m2 if reference_s0_w_m2 > 0.0 else 0.0,
            peak_sab_w_m2=float(np.max(sab)),
            mean_sab_w_m2=float(np.mean(sab)),
            absorbed_power_w=float(result.p_abs),
            sar_wb_w_kg=float(result.sar_wb) if result.sar_wb is not None else float("nan"),
        )

    def couple_many(
        self,
        local_grid: np.ndarray,
        rho: np.ndarray,
        solid_angle: float,
        reference_s0_w_m2: float,
        *,
        chunk_cells: int = 512,
    ) -> tuple[BodyExposure, ...]:
        """Couple several level-2 spectra without a body-by-grid allocation.

        The ordinary AEGIS level-2 kernel forms one ``body triangles x angular
        cells`` incidence matrix. That is reasonable for the study's original
        512-cell grid. It becomes several gigabytes when several 4096-cell
        spectra are evaluated together. This method evaluates the same
        geometric ReLU law in angular chunks and retains only one accumulated
        ``spectra x body triangles`` array.

        At 512 cells or fewer it calls :meth:`couple` directly. This keeps the
        established result bit for bit, including AEGIS's path construction and
        reduction order. Larger grids use the chunked float64 path.
        """
        grid = np.asarray(local_grid, dtype=np.float64)
        spectra = np.asarray(rho, dtype=np.float64)
        if grid.ndim != 2 or grid.shape[1] != 3:
            raise ValueError(f"local_grid must have shape (cells, 3), got {grid.shape}")
        if spectra.ndim != 2 or spectra.shape[1] != grid.shape[0]:
            raise ValueError(f"rho must have shape (spectra, {grid.shape[0]}), got {spectra.shape}")
        if chunk_cells < 1:
            raise ValueError("chunk_cells must be positive")
        if not np.all(np.isfinite(grid)) or not np.all(np.isfinite(spectra)):
            raise ValueError("local_grid and rho must be finite")
        if not np.isfinite(solid_angle) or solid_angle <= 0.0:
            raise ValueError("solid_angle must be positive and finite")
        if not np.isfinite(reference_s0_w_m2) or reference_s0_w_m2 < 0.0:
            raise ValueError("reference_s0_w_m2 must be nonnegative and finite")
        if grid.shape[0] <= chunk_cells:
            return tuple(self.couple(grid, spectrum, solid_angle, reference_s0_w_m2) for spectrum in spectra)
        exposures, _sab = self.couple_many_with_sab(
            grid,
            spectra,
            solid_angle,
            reference_s0_w_m2,
            chunk_cells=chunk_cells,
        )
        return exposures

    def couple_many_with_sab(
        self,
        local_grid: np.ndarray,
        rho: np.ndarray,
        solid_angle: float,
        reference_s0_w_m2: float,
        *,
        chunk_cells: int = 512,
    ) -> tuple[tuple[BodyExposure, ...], np.ndarray]:
        """Return level-2 exposures and their complete surface fields.

        The retained surface fields are linear in the angular spectra. This
        permits an exact cluster bootstrap of the peak of an ensemble-mean
        spectrum without repeating the body-to-grid incidence calculation.
        """
        grid = np.asarray(local_grid, dtype=np.float64)
        spectra = np.asarray(rho, dtype=np.float64)
        if grid.ndim != 2 or grid.shape[1] != 3:
            raise ValueError(f"local_grid must have shape (cells, 3), got {grid.shape}")
        if spectra.ndim != 2 or spectra.shape[1] != grid.shape[0]:
            raise ValueError(f"rho must have shape (spectra, {grid.shape[0]}), got {spectra.shape}")
        if chunk_cells < 1:
            raise ValueError("chunk_cells must be positive")
        if not np.all(np.isfinite(grid)) or not np.all(np.isfinite(spectra)):
            raise ValueError("local_grid and rho must be finite")
        if not np.isfinite(solid_angle) or solid_angle <= 0.0:
            raise ValueError("solid_angle must be positive and finite")
        if not np.isfinite(reference_s0_w_m2) or reference_s0_w_m2 < 0.0:
            raise ValueError("reference_s0_w_m2 must be nonnegative and finite")
        if self.level != 2:
            raise ValueError("surface-field body coupling currently implements AEGIS level 2 only")

        norms = np.linalg.norm(grid, axis=1)
        if np.any(norms <= 0.0):
            raise ValueError("local_grid rows must be nonzero directions")
        directions = grid / norms[:, None]
        powers = np.maximum(spectra * solid_angle * reference_s0_w_m2, 0.0)
        normals = np.asarray(self.body.normals, dtype=np.float64)
        sab = np.zeros((spectra.shape[0], normals.shape[0]), dtype=np.float64)
        for start in range(0, grid.shape[0], chunk_cells):
            stop = min(start + chunk_cells, grid.shape[0])
            incidence = np.maximum(normals @ directions[start:stop].T, 0.0)
            sab += powers[:, start:stop] @ incidence.T
        sab *= float(self.engine.T0)

        arriving = np.sum(powers, axis=1, dtype=np.float64)
        areas = np.asarray(self.body.areas, dtype=np.float64)
        out: list[BodyExposure] = []
        for index, spectrum_sab in enumerate(sab):
            p_abs = float(np.sum(spectrum_sab * areas, dtype=np.float64))
            out.append(
                BodyExposure(
                    reference_s0_w_m2=float(reference_s0_w_m2),
                    arriving_power_density_w_m2=float(arriving[index]),
                    susceptibility=(float(arriving[index] / reference_s0_w_m2) if reference_s0_w_m2 > 0.0 else 0.0),
                    peak_sab_w_m2=float(np.max(spectrum_sab)),
                    mean_sab_w_m2=float(np.mean(spectrum_sab)),
                    absorbed_power_w=p_abs,
                    sar_wb_w_kg=(p_abs / self.body_mass_kg if self.body_mass_kg is not None else float("nan")),
                )
            )
        return tuple(out), sab


def describe(coupler: BodyCoupler) -> dict[str, Any]:
    return {
        "phantom": coupler.body.name,
        "triangles": int(coupler.body.n_triangles),
        "frequency_hz": coupler.frequency_hz,
        "level": coupler.level,
        "T0": float(coupler.engine.T0),
    }
