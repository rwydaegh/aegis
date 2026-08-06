"""Escape estimation of one angular illumination law."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import numpy as np

from ..illumination.model import AngularIllumination
from .model import Surplus, require_credit
from .tracer import PointResult, SbrTracer


@dataclass(frozen=True)
class EscapeEstimator:
    """Score one angular law with the tracer's escape deposit."""

    tracer: SbrTracer
    model: AngularIllumination

    name: ClassVar[str] = "escape"

    def __post_init__(self) -> None:
        require_credit(self.name, self.model)

    def illumination(self) -> AngularIllumination:
        return self.model

    def trace(
        self,
        origin: np.ndarray,
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
    ) -> PointResult:
        """Return the angular result used by the dosimetry arm."""
        return self.tracer.trace(
            origin,
            {self.model.name: self.model},
            ground_z_m=ground_z_m,
            seed=seed,
        )

    def estimate(
        self,
        origin: np.ndarray,
        *,
        ground_z_m: float = 0.0,
        seed: int | None = None,
    ) -> Surplus:
        point = self.trace(origin, ground_z_m=ground_z_m, seed=seed)
        direct = point.susceptibility_direct[self.model.name]
        total = point.susceptibility[self.model.name]
        return Surplus(
            estimator=self.name,
            law=self.model.law,
            direct=direct,
            total=total,
            detail={
                "sky_fraction": point.sky_fraction,
                "mean_bounces": point.mean_bounces,
                "escaped_fraction": point.escaped_fraction,
            },
        )
