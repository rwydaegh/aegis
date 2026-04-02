"""Sum-of-sinusoids spatial correlation engine.

Implements QuaDRiGa v2.8.1 Section 3.1.1 (eq 26) for generating spatially
consistent N(0,1) random fields at arbitrary 3D positions.

The field is:

    k(x,y,z) = sqrt(2/N) * sum_{n=1}^{N} cos(2*pi*(f_x*x + f_y*y + f_z*z) + psi_n)

where the directional frequencies are derived from random spherical directions
and root frequencies proportional to 1/d_lambda.
"""

from __future__ import annotations

import numpy as np


class SumOfSinusoids:
    """Spatially correlated N(0,1) random field via sum of sinusoids.

    Parameters
    ----------
    d_lambda:
        Decorrelation distance in metres. Controls the spatial scale of
        the random field.
    n_sinusoids:
        Number of sinusoidal components. More sinusoids improve the
        approximation of the target ACF. Default: 20.
    seed:
        Random seed for reproducibility. Default: 42.
    """

    def __init__(self, d_lambda: float, n_sinusoids: int = 20, seed: int = 42) -> None:
        self.d_lambda = d_lambda
        self.n_sinusoids = n_sinusoids
        self.seed = seed
        self._init_parameters()

    def _init_parameters(self) -> None:
        rng = np.random.default_rng(self.seed)
        n = self.n_sinusoids
        d = self.d_lambda

        # Random azimuth and elevation for each sinusoid component
        phi = rng.uniform(-np.pi, np.pi, n)
        theta = rng.uniform(-np.pi / 2, np.pi / 2, n)

        # Root frequencies (spatial frequencies scaled by decorrelation distance)
        f_n = rng.uniform(-np.pi, np.pi, n) / (4.0 * d)

        # Directional frequency components
        cos_theta = np.cos(theta)
        self._f_x = f_n * np.cos(phi) * cos_theta
        self._f_y = f_n * np.sin(phi) * cos_theta
        self._f_z = f_n * np.sin(theta)

        # Random phases
        self._psi = rng.uniform(-np.pi, np.pi, n)

        # Amplitude normalisation: sqrt(2/N) ensures variance approx 1
        self._amplitude = np.sqrt(2.0 / n)

    def evaluate(self, positions: np.ndarray) -> np.ndarray:
        """Evaluate the random field at the given positions.

        Parameters
        ----------
        positions:
            Array of shape (M, 3) with (x, y, z) coordinates in metres.

        Returns
        -------
        np.ndarray
            Array of shape (M,) with N(0,1)-distributed field values.

        Raises
        ------
        ValueError
            If positions does not have shape (M, 3).
        """
        positions = np.asarray(positions, dtype=float)
        if positions.ndim != 2 or positions.shape[1] != 3:
            raise ValueError(f"positions must have shape (M, 3), got {positions.shape}")

        # positions: (M, 3), frequency components: (N,)
        # phase_arg[m, n] = 2*pi*(f_x*x_m + f_y*y_m + f_z*z_m) + psi_n
        x = positions[:, 0, np.newaxis]  # (M, 1)
        y = positions[:, 1, np.newaxis]  # (M, 1)
        z = positions[:, 2, np.newaxis]  # (M, 1)

        phase_arg = 2.0 * np.pi * (self._f_x * x + self._f_y * y + self._f_z * z) + self._psi  # (M, N)

        return self._amplitude * np.sum(np.cos(phase_arg), axis=1)  # (M,)
