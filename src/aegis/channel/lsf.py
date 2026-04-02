"""Large-scale fading model with spatially correlated LSPs.

Implements QuaDRiGa Section 3.2: generates spatially consistent, cross-correlated
large-scale parameter (LSP) maps at arbitrary 3D positions.

The 8 LSPs are: DS, KF, SF, ASD, ASA, ESD, ESA, XPR.
"""

from __future__ import annotations

import math

import numpy as np

from aegis.channel.correlation import LSP_NAMES, build_correlation_matrix
from aegis.channel.presets import scale_param
from aegis.channel.sos import SumOfSinusoids

# Map LSP short name -> preset key for decorrelation distance
_LAMBDA_KEYS: dict[str, str] = {
    "DS": "DS_lambda",
    "KF": "KF_lambda",
    "SF": "SF_lambda",
    "ASD": "AS_D_lambda",
    "ASA": "AS_A_lambda",
    "ESD": "ES_D_lambda",
    "ESA": "ES_A_lambda",
    "XPR": "XPR_lambda",
}

_DEFAULT_LAMBDA = 40.0  # metres


class LSFModel:
    """Spatially consistent, cross-correlated large-scale fading model.

    Parameters
    ----------
    params:
        Flat dict of QuaDRiGa channel parameters (from parse_conf or a preset).
    freq_ghz:
        Carrier frequency in GHz for frequency-dependent mu/sigma scaling.
    seed:
        Base random seed. Each LSP uses seed + i * 1000.
    """

    def __init__(self, params: dict, freq_ghz: float, seed: int = 42) -> None:
        self._params = params
        self._freq_ghz = freq_ghz
        self._seed = seed

        # Build cross-correlation Cholesky factor (8x8)
        _, self._L = build_correlation_matrix(params)

        # Create one SOS generator per LSP
        self._sos: list[SumOfSinusoids] = []
        for i, lsp in enumerate(LSP_NAMES):
            d_lambda = float(params.get(_LAMBDA_KEYS[lsp], _DEFAULT_LAMBDA))
            self._sos.append(SumOfSinusoids(d_lambda=d_lambda, seed=seed + i * 1000))

        # Pre-compute frequency-scaled mu and sigma for each LSP
        self._mu, self._sigma = self._compute_mu_sigma(params, freq_ghz)

    def _compute_mu_sigma(self, p: dict, f: float) -> tuple[list[float], list[float]]:
        """Return (mu, sigma) lists indexed by LSP_NAMES order."""
        mu: list[float] = []
        sigma: list[float] = []

        # DS
        mu.append(
            scale_param(
                float(p.get("DS_mu", -7.5)),
                float(p.get("DS_omega", 1.0)),
                float(p.get("DS_gamma", 0.0)),
                f,
            )
        )
        ds_sigma = float(p.get("DS_sigma", 0.0))
        ds_delta = float(p.get("DS_delta", 0.0))
        ds_omega = float(p.get("DS_omega", 1.0))
        sigma.append(ds_sigma + ds_delta * math.log10(ds_omega + f))

        # KF
        mu.append(float(p.get("KF_mu", 0.0)))
        sigma.append(float(p.get("KF_sigma", 0.0)))

        # SF
        mu.append(0.0)
        sigma.append(float(p.get("SF_sigma", 0.0)))

        # ASD
        mu.append(
            scale_param(
                float(p.get("AS_D_mu", 0.0)),
                float(p.get("AS_D_omega", 1.0)),
                float(p.get("AS_D_gamma", 0.0)),
                f,
            )
        )
        asd_sigma = float(p.get("AS_D_sigma", 0.0))
        asd_delta = float(p.get("AS_D_delta", 0.0))
        asd_omega = float(p.get("AS_D_omega", 1.0))
        sigma.append(asd_sigma + asd_delta * math.log10(asd_omega + f))

        # ASA
        mu.append(
            scale_param(
                float(p.get("AS_A_mu", 0.0)),
                float(p.get("AS_A_omega", 1.0)),
                float(p.get("AS_A_gamma", 0.0)),
                f,
            )
        )
        asa_sigma = float(p.get("AS_A_sigma", 0.0))
        asa_delta = float(p.get("AS_A_delta", 0.0))
        asa_omega = float(p.get("AS_A_omega", 1.0))
        sigma.append(asa_sigma + asa_delta * math.log10(asa_omega + f))

        # ESD
        mu.append(
            scale_param(
                float(p.get("ES_D_mu", 0.0)),
                float(p.get("ES_D_omega", 1.0)),
                float(p.get("ES_D_gamma", 0.0)),
                f,
            )
        )
        esd_sigma = float(p.get("ES_D_sigma", 0.0))
        esd_delta = float(p.get("ES_D_delta", 0.0))
        esd_omega = float(p.get("ES_D_omega", 1.0))
        sigma.append(esd_sigma + esd_delta * math.log10(esd_omega + f))

        # ESA
        mu.append(
            scale_param(
                float(p.get("ES_A_mu", 0.0)),
                float(p.get("ES_A_omega", 1.0)),
                float(p.get("ES_A_gamma", 0.0)),
                f,
            )
        )
        esa_sigma = float(p.get("ES_A_sigma", 0.0))
        esa_delta = float(p.get("ES_A_delta", 0.0))
        esa_omega = float(p.get("ES_A_omega", 1.0))
        sigma.append(esa_sigma + esa_delta * math.log10(esa_omega + f))

        # XPR
        mu.append(float(p.get("XPR_mu", 0.0)))
        sigma.append(float(p.get("XPR_sigma", 0.0)))

        return mu, sigma

    def evaluate(self, positions: np.ndarray) -> dict[str, np.ndarray]:
        """Evaluate LSPs at (M, 3) positions.

        Returns a dict with keys DS, KF_dB, SF_dB, ASD_deg, ASA_deg,
        ESD_deg, ESA_deg, XPR_dB. Each value has shape (M,).
        """
        positions = np.asarray(positions, dtype=float)
        if positions.ndim != 2 or positions.shape[1] != 3:
            raise ValueError(f"positions must have shape (M, 3), got {positions.shape}")

        # Step 1: generate 8 uncorrelated N(0,1) SOS values -> (8, M)
        uncorrelated = np.stack([sos.evaluate(positions) for sos in self._sos], axis=0)

        # Step 2: apply cross-correlations via Cholesky factor (eq 50)
        # correlated shape: (8, M)
        correlated = self._L @ uncorrelated

        # Step 3: scale to physical values
        # LSP order matches LSP_NAMES: DS(0), KF(1), SF(2), ASD(3), ASA(4), ESD(5), ESA(6), XPR(7)
        mu = self._mu
        sigma = self._sigma

        def _lognormal(idx: int) -> np.ndarray:
            """10^(mu + sigma * X)"""
            return np.power(10.0, mu[idx] + sigma[idx] * correlated[idx])

        def _db(idx: int) -> np.ndarray:
            """mu + sigma * X (linear dB)"""
            return mu[idx] + sigma[idx] * correlated[idx]

        return {
            "DS": _lognormal(0),  # seconds, log-normal
            "KF_dB": _db(1),  # dB
            "SF_dB": _db(2),  # dB (mu=0)
            "ASD_deg": _lognormal(3),  # degrees, log-normal
            "ASA_deg": _lognormal(4),  # degrees, log-normal
            "ESD_deg": _lognormal(5),  # degrees, log-normal
            "ESA_deg": _lognormal(6),  # degrees, log-normal
            "XPR_dB": _db(7),  # dB
        }

    def generate_map(
        self,
        bounds: tuple[float, float, float, float],
        resolution: int,
        height: float,
        lsp_name: str,
    ) -> np.ndarray:
        """Generate a 2D LSP map on a horizontal plane.

        Parameters
        ----------
        bounds:
            (x_min, x_max, y_min, y_max) in metres.
        resolution:
            Number of grid points per axis (grid is resolution x resolution).
        height:
            Z coordinate of the horizontal plane.
        lsp_name:
            Key from evaluate() output, e.g. "SF_dB".

        Returns
        -------
        np.ndarray
            Array of shape (resolution, resolution).
        """
        x_min, x_max, y_min, y_max = bounds
        xs = np.linspace(x_min, x_max, resolution)
        ys = np.linspace(y_min, y_max, resolution)

        # Build (resolution*resolution, 3) positions
        xx, yy = np.meshgrid(xs, ys)  # each shape (resolution, resolution)
        flat_x = xx.ravel()
        flat_y = yy.ravel()
        flat_z = np.full_like(flat_x, height)

        positions = np.stack([flat_x, flat_y, flat_z], axis=1)

        result = self.evaluate(positions)
        return result[lsp_name].reshape(resolution, resolution)
