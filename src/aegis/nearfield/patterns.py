"""Free-space far-field antenna patterns for the hand-held source.

Loads the rigorously re-evaluated 1-degree directivity grids produced by the
Sim4Life near-to-far transform (``goliat_farfield_results/<band>/.../
far_field_1deg_pattern.npz``) and samples them along an arbitrary line of sight.

The sampler is a backend-agnostic bilinear interpolation written against
``aegis._array_backend.xp``, so under the JAX backend it is differentiable in the
query direction (hence in the phone orientation). The grid data themselves are
fixed constants, captured at load time.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aegis._array_backend import xp


@dataclass(frozen=True)
class AntennaPattern3D:
    """A directivity pattern D(theta, phi) on a regular spherical grid.

    Convention matches Sim4Life / the .npz files: ``theta`` is the polar angle
    from +z in [0, pi]; ``phi`` is the azimuth in [-pi, pi] measured from +x in
    the xy-plane. ``directivity`` is linear (dimensionless, sphere-average 1).

    Attributes
    ----------
    theta_rad : (n_theta,) increasing grid of polar angles
    phi_rad : (n_phi,) increasing grid of azimuth angles
    directivity : (n_phi, n_theta) linear directivity
    freq_hz : float
    peak_directivity : float
    radiation_efficiency : float in [0, 1] (peak gain / peak directivity proxy)
    """

    theta_rad: np.ndarray
    phi_rad: np.ndarray
    directivity: np.ndarray
    freq_hz: float
    peak_directivity: float = 0.0
    radiation_efficiency: float = 1.0
    name: str = "pattern"

    @classmethod
    def from_npz(
        cls,
        npz_path: str | Path,
        freq_hz: float | None = None,
        summary_path: str | Path | None = None,
    ) -> AntennaPattern3D:
        """Load a pattern from a ``far_field_1deg_pattern.npz`` file.

        ``summary_path`` (the sibling ``*_summary.json``) is read when present to
        recover peak directivity and radiation efficiency. ``freq_hz`` overrides
        the value inferred from the summary or the parent directory name.
        """
        npz_path = Path(npz_path)
        data = np.load(npz_path)
        theta = np.asarray(data["theta_rad"], dtype=np.float64)
        phi = np.asarray(data["phi_rad"], dtype=np.float64)
        directivity = np.asarray(data["directivity"], dtype=np.float64)
        # The .npz stores (n_phi, n_theta); confirm and keep that orientation.
        if directivity.shape != (phi.size, theta.size):
            if directivity.shape == (theta.size, phi.size):
                directivity = directivity.T
            else:
                raise ValueError(
                    f"directivity shape {directivity.shape} matches neither (n_phi, n_theta)=({phi.size},{theta.size})"
                )

        eff = 1.0
        peak = float(directivity.max())
        if summary_path is None:
            cand = npz_path.with_name(npz_path.name.replace("pattern.npz", "summary.json"))
            summary_path = cand if cand.exists() else None
        if summary_path is not None and Path(summary_path).exists():
            summary = json.loads(Path(summary_path).read_text())
            eff = float(summary.get("radiation_efficiency", 1.0))
            if summary.get("peak_directivity_dBi") is not None:
                peak = float(10 ** (summary["peak_directivity_dBi"] / 10))
            if freq_hz is None and "frequency_mhz" in summary:
                freq_hz = float(summary["frequency_mhz"]) * 1e6

        if freq_hz is None:
            raise ValueError("freq_hz could not be inferred; pass it explicitly")

        return cls(
            theta_rad=theta,
            phi_rad=phi,
            directivity=directivity,
            freq_hz=float(freq_hz),
            peak_directivity=peak,
            radiation_efficiency=eff,
            name=npz_path.parent.parent.name or npz_path.stem,
        )

    @classmethod
    def isotropic(cls, freq_hz: float) -> AntennaPattern3D:
        """A unit-directivity isotropic reference pattern (for sanity checks)."""
        theta = np.linspace(0.0, np.pi, 181)
        phi = np.linspace(-np.pi, np.pi, 361)
        return cls(
            theta_rad=theta,
            phi_rad=phi,
            directivity=np.ones((phi.size, theta.size)),
            freq_hz=float(freq_hz),
            peak_directivity=1.0,
            radiation_efficiency=1.0,
            name="isotropic",
        )

    # -- sampling -----------------------------------------------------------

    def sample(self, directions_ant) -> xp.ndarray:
        """Sample linear directivity along unit ``directions_ant`` (..., 3).

        ``directions_ant`` are unit vectors expressed in the antenna body frame
        (the source -> field-point line of sight already rotated into that
        frame). Returns directivity of shape ``directions_ant.shape[:-1]``.

        Bilinear in (theta, phi) with azimuth wrap-around. Differentiable in the
        direction components under the JAX backend.
        """
        d = directions_ant
        x = d[..., 0]
        y = d[..., 1]
        z = d[..., 2]
        # Clamp z so arccos has a bounded (finite) derivative at the poles.
        z = xp.clip(z, -1.0 + 1e-7, 1.0 - 1e-7)
        theta = xp.arccos(z)
        # arctan2(y, x) has a 0/0 gradient when x = y = 0 (line of sight along
        # the antenna axis). Azimuth is irrelevant there, so swap in safe
        # constant inputs for those points: this zeroes the gradient locally
        # instead of poisoning it with NaN (the standard double-where trick).
        rho2 = x * x + y * y
        tiny = rho2 < 1e-12
        safe_x = xp.where(tiny, 1.0, x)
        safe_y = xp.where(tiny, 0.0, y)
        phi = xp.arctan2(safe_y, safe_x)

        th0 = float(self.theta_rad[0])
        dth = float(self.theta_rad[1] - self.theta_rad[0])
        ph0 = float(self.phi_rad[0])
        dph = float(self.phi_rad[1] - self.phi_rad[0])
        n_th = self.theta_rad.size
        n_ph = self.phi_rad.size

        grid = xp.asarray(self.directivity)  # (n_phi, n_theta)

        # Fractional indices.
        ft = (theta - th0) / dth
        fp = (phi - ph0) / dph

        it0 = xp.clip(xp.floor(ft), 0, n_th - 2).astype("int32")
        it1 = it0 + 1
        wt = ft - it0.astype(ft.dtype)
        wt = xp.clip(wt, 0.0, 1.0)

        # Azimuth wraps periodically (phi grid spans the full circle).
        ip0 = xp.floor(fp).astype("int32")
        wp = fp - ip0.astype(fp.dtype)
        ip0 = xp.mod(ip0, n_ph)
        ip1 = xp.mod(ip0 + 1, n_ph)

        g00 = grid[ip0, it0]
        g01 = grid[ip0, it1]
        g10 = grid[ip1, it0]
        g11 = grid[ip1, it1]

        g0 = g00 * (1 - wt) + g01 * wt
        g1 = g10 * (1 - wt) + g11 * wt
        out = g0 * (1 - wp) + g1 * wp
        # Directivity is non-negative; guard tiny interpolation undershoot.
        return xp.maximum(out, 0.0)


def load_band_patterns(
    results_dir: str | Path,
) -> dict[int, AntennaPattern3D]:
    """Load every band under a ``goliat_farfield_results``-style directory.

    Returns a mapping ``freq_mhz -> AntennaPattern3D``. Each band directory is
    named ``<MHz>MHz`` and contains exactly one scenario subdirectory holding the
    ``far_field_1deg_pattern.npz`` and ``far_field_1deg_summary.json``.
    """
    results_dir = Path(results_dir)
    out: dict[int, AntennaPattern3D] = {}
    for band_dir in sorted(results_dir.glob("*MHz")):
        try:
            freq_mhz = int(band_dir.name.replace("MHz", ""))
        except ValueError:
            continue
        npzs = list(band_dir.glob("**/far_field_1deg_pattern.npz"))
        if not npzs:
            continue
        out[freq_mhz] = AntennaPattern3D.from_npz(npzs[0], freq_hz=freq_mhz * 1e6)
    return out
