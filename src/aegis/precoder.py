"""Precoder dataclass for MIMO beamforming.

Wraps the complex precoding vector x with constructors for MRT and ECBF.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from aegis.defaults import NUMERICAL_FLOOR


@dataclass(frozen=True)
class Precoder:
    """Precoding vector for coherent MIMO transmission.

    Attributes
    ----------
    x : (M_ant,) complex precoding vector. ||x||^2 = total transmit power P.
    """

    x: np.ndarray = field(repr=False)

    def __post_init__(self) -> None:
        if self.x.ndim != 1:
            raise ValueError(f"x must be 1D, got shape {self.x.shape}")

    @property
    def n_elements(self) -> int:
        return self.x.shape[0]

    @property
    def power(self) -> float:
        """Total transmit power ||x||^2 [W]."""
        return float(np.real(np.vdot(self.x, self.x)))

    @classmethod
    def mrt(cls, h: np.ndarray, P: float = 1.0) -> Precoder:
        """Maximum ratio transmission: x = sqrt(P) * h* / ||h||.

        Parameters
        ----------
        h : (M_ant,)
            UE channel vector.
        P : float
            Total transmit power [W].
        """
        h = np.asarray(h, dtype=complex)
        h_conj = h.conj()
        norm = np.sqrt(float(np.real(np.vdot(h_conj, h_conj))))
        if norm < NUMERICAL_FLOOR:
            x = np.zeros(h.shape, dtype=h.dtype)
            x[0] = np.sqrt(P)
            return cls(x=x)
        return cls(x=np.sqrt(P) * h_conj / norm)

    @classmethod
    def ecbf(
        cls,
        h: np.ndarray,
        Q: np.ndarray,
        P_abs_max: float,
        P: float = 1.0,
    ) -> Precoder:
        """Exposure-constrained beamforming via QCQP.

        Parameters
        ----------
        h : (M_ant,)
            UE channel vector.
        Q : (M_ant, M_ant)
            Exposure operator.
        P_abs_max : float
            Maximum allowed absorbed power [W].
        P : float
            Total transmit power [W].
        """
        from aegis.coherent.ecbf import solve_ecbf

        x = solve_ecbf(h, Q, P_abs_max, P)
        return cls(x=x)

    def __repr__(self) -> str:
        return f"Precoder(M={self.n_elements}, P={self.power:.4g} W)"
