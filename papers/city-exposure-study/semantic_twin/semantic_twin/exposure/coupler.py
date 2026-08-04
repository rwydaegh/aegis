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


def describe(coupler: BodyCoupler) -> dict[str, Any]:
    return {
        "phantom": coupler.body.name,
        "triangles": int(coupler.body.n_triangles),
        "frequency_hz": coupler.frequency_hz,
        "level": coupler.level,
        "T0": float(coupler.engine.T0),
    }
