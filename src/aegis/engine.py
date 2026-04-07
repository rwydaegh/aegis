"""DosimetryEngine: main entry point for absorbed power density computation.

Dispatches to the appropriate kernel based on fidelity level (0-8).
Levels 0-6 are incoherent. Levels 7-8 are coherent MIMO.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import TYPE_CHECKING

import numpy as np

from aegis._array_backend import JAX_AVAILABLE
from aegis.constants import C_0, Z_0
from aegis.defaults import DEFAULT_P_ABS_MAX
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.result import DosimetryResult
from aegis.tissue.dielectric import TissueModel
from aegis.tissue.fresnel import T0 as fresnel_T0
from aegis.tissue.fresnel import n_complex as fresnel_n_complex

if TYPE_CHECKING:
    from aegis.precoder import Precoder

# Module-level timing dict, populated by compute() for viewer profiling.
# Protected by _timings_lock for thread safety under concurrent Flask requests.
_last_timings: dict[str, float] = {}
_timings_lock = threading.Lock()

_ERR_LEVEL_AND_MODE = "Cannot specify both level and mode"


def _to_numpy(arr):
    """Convert JAX arrays to NumPy. No-op for NumPy arrays."""
    if JAX_AVAILABLE:
        import numpy as _np

        return _np.asarray(arr)
    return arr


def coherent_sinc(centroids, k_hat, psi, element_index, x, freq_hz):
    """Coherent incident power density from a beamformed field.

    Computes |E(r)|^2 / (2*Z_0) where E = G(r) @ x is the coherent
    free-space field at each triangle centroid. For multi-stream W,
    sums power over streams (uncorrelated data symbols).

    Parameters
    ----------
    centroids : (M, 3)
    k_hat : (N, 3)
    psi : (N, 3) complex, with element gain and steering phase baked in
    element_index : (N,)
    x : (M_ant,) single precoder or (M_ant, K) multi-stream precoding matrix
    freq_hz : float

    Returns
    -------
    sinc : (M,) incident power density [W/m^2]
    """
    k0 = 2 * np.pi * freq_hz / C_0
    phase = np.exp(-1j * k0 * (centroids @ k_hat.T))  # (M, N)

    if x.ndim == 1:
        w_psi = psi * x[element_index][:, None]  # (N, 3)
        E = phase @ w_psi  # (M, 3)
        return np.sum(np.abs(E) ** 2, axis=1) / (2 * Z_0)

    # Multi-stream: sum power over K streams (uncorrelated symbols).
    # Vectorized: compute all K streams in one batched matmul instead of looping.
    w_psi_all = psi[:, :, None] * x[element_index, :][:, None, :]  # (N, 3, K)
    E_all = np.einsum("mn,npk->mpk", phase, w_psi_all)  # (M, 3, K)
    return np.sum(np.abs(E_all) ** 2, axis=(1, 2)) / (2 * Z_0)


class DosimetryEngine:
    """Compute absorbed power density on a body mesh from propagation paths.

    Parameters
    ----------
    tissue : TissueModel
        Tissue electromagnetic properties at the operating frequency.
    """

    # Class-level LRU cache for averaging matrices. Keyed by a content hash of
    # the body geometry (centroid checksum + n_triangles) and target area.
    # Shared across all engine instances so the expensive build persists across requests.
    # Bounded to _G_CACHE_MAX entries to prevent unbounded memory growth in
    # long-running viewer sessions with many body switches.
    # Protected by _G_lock for thread safety (Flask serves concurrent requests).
    _G_cache: OrderedDict = OrderedDict()
    _G_lock: threading.Lock = threading.Lock()
    _G_CACHE_MAX: int = 16

    def __init__(self, tissue: TissueModel) -> None:
        self.tissue = tissue
        self.T0 = tissue.T0
        self.n_tilde = tissue.n_complex
        self.freq_hz = tissue.freq_hz

    def _active_em_params(self, freq_hz: float | None) -> tuple[float, complex, float, float]:
        """Resolve per-call EM parameters, honoring an optional frequency override."""
        if freq_hz is None:
            return self.freq_hz, self.n_tilde, self.T0, self.tissue.sigma
        if freq_hz <= 0:
            raise ValueError(f"freq_hz must be positive, got {freq_hz}")

        active_n_tilde = fresnel_n_complex(self.tissue.eps_r, self.tissue.sigma, freq_hz)
        active_T0 = fresnel_T0(active_n_tilde)
        return float(freq_hz), active_n_tilde, active_T0, self.tissue.sigma

    @staticmethod
    def _body_cache_key(body: BodyMesh) -> int:
        """Content-based hash of body geometry for cache keying.

        Delegates to BodyMesh.geometry_hash which is computed once at
        construction time and cached, avoiding O(M) SHA256 on every call.
        """
        return body.geometry_hash

    def _get_G(self, body, target_area_m2):
        key = (self._body_cache_key(body), target_area_m2)
        with self._G_lock:
            if key in self._G_cache:
                self._G_cache.move_to_end(key)
                return self._G_cache[key]

        from aegis.geometry.averaging import precompute_averaging_matrix

        G = precompute_averaging_matrix(
            body.centroids,
            body.areas,
            target_area_m2,
        )

        with self._G_lock:
            # Evict least-recently-used entries if cache is full
            while len(self._G_cache) >= self._G_CACHE_MAX:
                self._G_cache.popitem(last=False)
            self._G_cache[key] = G

        return G

    def _build_result(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        sab: np.ndarray,
        fidelity_level: int,
        *,
        body_mass: float | None = None,
        freq_hz: float | None = None,
        mode: str | None = None,
        corrections: tuple[str, ...] = (),
        Q: np.ndarray | None = None,
        rho: float | None = None,
        eigenvalues: np.ndarray | None = None,
        x_star: np.ndarray | None = None,
        spatial_averaging: bool = True,
        _timings: dict | None = None,
        sinc: np.ndarray | None = None,
    ) -> DosimetryResult:
        """Build a DosimetryResult from raw sab with averaging and derived quantities."""
        if not np.all(np.isfinite(sab)):
            n_nan = int(np.sum(np.isnan(sab)))
            n_inf = int(np.sum(np.isinf(sab)))
            raise ValueError(
                f"Kernel produced non-finite sab values ({n_nan} NaN, {n_inf} Inf). "
                f"This indicates a numerical issue in the level {fidelity_level} kernel."
            )
        p_abs = float(np.sum(sab * body.areas))
        sar_wb = p_abs / body_mass if body_mass is not None else None
        effective_freq_hz = freq_hz if freq_hz is not None else self.freq_hz

        # Per-triangle incident power density.
        # For coherent levels the caller provides the coherent sinc directly;
        # for incoherent levels we compute the standard incoherent sum.
        if sinc is None:
            from aegis.kernels._base import incidence_geometry

            _, mu_plus = incidence_geometry(body.normals, _to_numpy(paths.k_hat))
            sinc = _to_numpy(mu_plus) @ _to_numpy(paths.power)

        sab_averaged = None
        sinc_averaged = None
        sab_1cm2_averaged = None
        avg_timings: dict[str, float] = {}

        if spatial_averaging:
            t0 = time.perf_counter()
            G_4cm2 = self._get_G(body, 4e-4)
            t_build = time.perf_counter() - t0
            t1 = time.perf_counter()
            sab_averaged = _to_numpy(G_4cm2 @ sab)
            sinc_averaged = _to_numpy(G_4cm2 @ sinc)
            t_matvec = time.perf_counter() - t1

            avg_timings = {
                "avg_build_G_4cm2_ms": t_build * 1e3,
                "avg_matvec_4cm2_ms": t_matvec * 1e3,
            }

            if effective_freq_hz is not None and effective_freq_hz > 30e9:
                t2 = time.perf_counter()
                G_1cm2 = self._get_G(body, 1e-4)
                avg_timings["avg_build_G_1cm2_ms"] = (time.perf_counter() - t2) * 1e3
                sab_1cm2_averaged = _to_numpy(G_1cm2 @ sab)

        # Propagate averaging timings to caller's dict if provided
        if _timings is not None:
            _timings.update(avg_timings)
        # Keep module-level dict updated for backward compatibility
        with _timings_lock:
            _last_timings.update(avg_timings)

        return DosimetryResult(
            sab=sab,
            p_abs=p_abs,
            fidelity_level=fidelity_level,
            sab_averaged=sab_averaged,
            sar_wb=sar_wb,
            sinc=sinc,
            sinc_averaged=sinc_averaged,
            sab_1cm2_averaged=sab_1cm2_averaged,
            freq_hz=effective_freq_hz,
            mode=mode,
            corrections=corrections,
            Q=Q,
            rho=rho,
            eigenvalues=eigenvalues,
            x_star=x_star,
        )

    def compute(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        level: int | None = None,
        body_mass: float | None = None,
        spatial_averaging: bool = True,
        # Level 0/1 precomputed geometry (optional)
        A_ab: float | None = None,
        D_max: float | None = None,
        sh_coeffs: np.ndarray | None = None,
        sh_L: int = 4,
        D_table: np.ndarray | None = None,
        D_dirs: np.ndarray | None = None,
        # Level 4 polarisation / mode-based corrections
        q: np.ndarray | float = 0.0,
        # Level 5/6 curvature
        curvature_H: np.ndarray | None = None,
        # Level 7-8 coherent MIMO
        precoder: Precoder | None = None,
        h: np.ndarray | None = None,
        P_abs_max: float = DEFAULT_P_ABS_MAX,
        # Mode-based API
        mode: str | None = None,
        fresnel: bool = True,
        polarisation: bool = False,
        diffraction: bool = False,
        curvature: bool = False,
        freq_hz: float | None = None,
        _timings: dict[str, float] | None = None,
    ) -> DosimetryResult:
        """Compute dosimetry at the specified fidelity level or mode.

        Parameters
        ----------
        body : BodyMesh
        paths : PropagationPaths
        level : fidelity level 0-8 (legacy API, mutually exclusive with mode)
        body_mass : body mass [kg] for SAR computation
        spatial_averaging : compute ICNIRP 4 cm^2 spatial averaging (default True)
        A_ab : absorption area [m^2] (required for levels 0-1)
        D_max : max directivity (required for level 0)
        sh_coeffs : SH coefficients for D(k_hat) (level 1)
        sh_L : SH degree (level 1)
        D_table : directivity LUT (level 1 alternative)
        D_dirs : directions for D_table (level 1 alternative)
        q : TM excess (level 4 or mode='spatial' with polarisation=True)
        curvature_H : (M,) twice mean curvature [1/m] (levels 5-6 or curvature/diffraction flags)
        precoder : Precoder with precoding vector x (required for level 7)
        h : (M_ant,) UE channel vector (required for level 8, optional for 7)
        P_abs_max : maximum absorbed power [W] (level 8)
        mode : one of 'bound', 'aggregate', 'spatial', 'coherent', 'ecbf'
        fresnel : use angle-dependent Fresnel (spatial mode, default True)
        polarisation : enable polarisation correction (spatial mode)
        diffraction : enable diffraction smoothing (spatial mode)
        curvature : enable curvature correction (spatial mode)
        _timings : if provided, fine-grained timing data is written into this dict

        Returns
        -------
        DosimetryResult
        """
        if level is not None and mode is not None:
            raise ValueError(_ERR_LEVEL_AND_MODE)

        # Default: neither given -> behave like old level=2
        if level is None and mode is None:
            level = 2

        if body_mass is not None and body_mass <= 0:
            raise ValueError("body_mass must be positive when provided")

        active_freq_hz, active_n_tilde, active_T0, active_sigma = self._active_em_params(freq_hz)

        # Mode-based path
        if mode is not None:
            return self._compute_mode(
                body,
                paths,
                mode=mode,
                fresnel=fresnel,
                polarisation=polarisation,
                diffraction=diffraction,
                curvature=curvature,
                q=q,
                curvature_H=curvature_H,
                body_mass=body_mass,
                spatial_averaging=spatial_averaging,
                A_ab=A_ab,
                D_max=D_max,
                sh_coeffs=sh_coeffs,
                sh_L=sh_L,
                D_table=D_table,
                D_dirs=D_dirs,
                precoder=precoder,
                h=h,
                P_abs_max=P_abs_max,
                freq_hz=active_freq_hz,
                n_tilde=active_n_tilde,
                T0=active_T0,
                sigma=active_sigma,
                _timings=_timings,
            )

        # Legacy level-based path
        if level < 0 or level > 8:
            raise ValueError(f"Fidelity level must be 0-8, got {level}")

        if level >= 7:
            return self._compute_coherent(
                body,
                paths,
                level,
                precoder=precoder,
                h=h,
                P_abs_max=P_abs_max,
                body_mass=body_mass,
                spatial_averaging=spatial_averaging,
                freq_hz=active_freq_hz,
                n_tilde=active_n_tilde,
                sigma=active_sigma,
            )

        sab = self._dispatch(
            body,
            paths,
            level,
            A_ab=A_ab,
            D_max=D_max,
            sh_coeffs=sh_coeffs,
            sh_L=sh_L,
            D_table=D_table,
            D_dirs=D_dirs,
            q=q,
            curvature_H=curvature_H,
            freq_hz=active_freq_hz,
            n_tilde=active_n_tilde,
            T0=active_T0,
        )
        sab = _to_numpy(sab)
        return self._build_result(
            body,
            paths,
            sab,
            level,
            body_mass=body_mass,
            freq_hz=active_freq_hz,
            spatial_averaging=spatial_averaging,
            _timings=_timings,
        )

    def compute_with_timings(self, *args, **kwargs) -> tuple[DosimetryResult, dict[str, float]]:
        """Like compute(), but returns a (DosimetryResult, timings) tuple.

        The timings dict is local to this call (thread-safe). Keys match those
        in _last_timings: kernel_ms, avg_build_G_4cm2_ms, avg_matvec_4cm2_ms,
        avg_build_G_1cm2_ms.

        Parameters mirror compute() exactly.
        """
        timings: dict[str, float] = {}
        result = self.compute(*args, _timings=timings, **kwargs)
        return result, timings

    def compute_sab(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        level: int | None = None,
        *,
        precoder_x=None,
        precoder: Precoder | None = None,
        h=None,
        P_abs_max: float = DEFAULT_P_ABS_MAX,
        A_ab: float | None = None,
        D_max: float | None = None,
        sh_coeffs=None,
        sh_L: int = 4,
        D_table=None,
        D_dirs=None,
        q: float = 0.0,
        curvature_H=None,
        # Mode-based API
        mode: str | None = None,
        fresnel: bool = True,
        polarisation: bool = False,
        diffraction: bool = False,
        curvature: bool = False,
        freq_hz: float | None = None,
    ):
        """Return per-triangle S_ab as a raw array (JAX or NumPy).

        Unlike compute(), this does not convert to NumPy or wrap in
        DosimetryResult. Use inside jax.grad boundaries for differentiable
        optimization.
        """
        if level is not None and mode is not None:
            raise ValueError(_ERR_LEVEL_AND_MODE)

        # Default: neither given -> behave like old level=2
        if level is None and mode is None:
            level = 2

        active_freq_hz, active_n_tilde, active_T0, active_sigma = self._active_em_params(freq_hz)

        # Mode-based path for spatial
        if mode is not None:
            if mode == "spatial":
                from aegis.kernels.spatial import spatial_kernel

                return spatial_kernel(
                    body.normals,
                    paths.k_hat,
                    paths.power,
                    active_n_tilde,
                    active_T0,
                    active_freq_hz,
                    fresnel=fresnel,
                    polarisation=polarisation,
                    q=q,
                    curvature=curvature,
                    diffraction=diffraction,
                    curvature_H=curvature_H,
                )
            # For non-spatial modes, map to the legacy dispatch
            mode_to_level = {
                "bound": 0,
                "aggregate": 1,
                "coherent": 7,
                "ecbf": 8,
            }
            if mode not in mode_to_level:
                raise ValueError(f"Unknown mode '{mode}'")
            level = mode_to_level[mode]

        if level < 0 or level > 8:
            raise ValueError(f"Fidelity level must be 0-8, got {level}")

        if level <= 6:
            return self._dispatch(
                body,
                paths,
                level,
                A_ab=A_ab,
                D_max=D_max,
                sh_coeffs=sh_coeffs,
                sh_L=sh_L,
                D_table=D_table,
                D_dirs=D_dirs,
                q=q,
                curvature_H=curvature_H,
                freq_hz=active_freq_hz,
                n_tilde=active_n_tilde,
                T0=active_T0,
            )

        # Coherent levels 7-8
        x = precoder_x
        if x is None and precoder is not None:
            x = precoder.x

        n_elements = paths.n_elements

        if level == 7:
            if x is None:
                raise ValueError("Level 7 requires precoder or precoder_x")
            from aegis.kernels.level7_coherent import level7_coherent

            sab, _, _, _ = level7_coherent(
                body.normals,
                body.centroids,
                body.areas,
                paths.k_hat,
                paths.psi,
                paths.element_index,
                x,
                active_n_tilde,
                active_sigma,
                active_freq_hz,
                n_elements,
                h=h,
            )
            return sab

        if level == 8:
            if h is None:
                raise ValueError("Level 8 requires h")
            from aegis.kernels.level8_ecbf import level8_ecbf

            P = float(precoder.power) if precoder is not None else 1.0
            sab, _, _, _, _ = level8_ecbf(
                body.normals,
                body.centroids,
                body.areas,
                paths.k_hat,
                paths.psi,
                paths.element_index,
                h,
                active_n_tilde,
                active_sigma,
                active_freq_hz,
                n_elements,
                P=P,
                P_abs_max=P_abs_max,
            )
            return sab

        raise ValueError(f"Unknown level {level}")

    def _compute_mode(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        *,
        mode: str,
        fresnel: bool = True,
        polarisation: bool = False,
        diffraction: bool = False,
        curvature: bool = False,
        q: np.ndarray | float = 0.0,
        curvature_H: np.ndarray | None = None,
        body_mass: float | None = None,
        spatial_averaging: bool = True,
        A_ab: float | None = None,
        D_max: float | None = None,
        sh_coeffs: np.ndarray | None = None,
        sh_L: int = 4,
        D_table: np.ndarray | None = None,
        D_dirs: np.ndarray | None = None,
        precoder: Precoder | None = None,
        h: np.ndarray | None = None,
        P_abs_max: float = DEFAULT_P_ABS_MAX,
        freq_hz: float | None = None,
        n_tilde: complex | None = None,
        T0: float | None = None,
        sigma: float | None = None,
        _timings: dict | None = None,
    ) -> DosimetryResult:
        """Dispatch based on mode string with composable correction flags."""
        _valid_modes = ("bound", "aggregate", "spatial", "coherent", "ecbf")
        if mode not in _valid_modes:
            raise ValueError(f"Unknown mode '{mode}', expected one of {_valid_modes}")

        # Build corrections tuple for result metadata
        corrections: list[str] = []
        if mode == "spatial":
            if fresnel:
                corrections.append("fresnel")
            if polarisation:
                corrections.append("polarisation")
            if curvature:
                corrections.append("curvature")
            if diffraction:
                corrections.append("diffraction")

        # Map mode to level for fidelity_level field
        if mode == "spatial":
            fidelity_level = 2  # base spatial (geometric ReLU, no Fresnel)
            if fresnel:
                fidelity_level = 3
            if polarisation:
                fidelity_level = max(fidelity_level, 4)
            if curvature:
                fidelity_level = max(fidelity_level, 5)
            if diffraction:
                fidelity_level = max(fidelity_level, 6)
        else:
            mode_to_level = {
                "bound": 0,
                "aggregate": 1,
                "coherent": 7,
                "ecbf": 8,
            }
            fidelity_level = mode_to_level[mode]

        if mode == "spatial":
            from aegis.kernels.spatial import spatial_kernel

            t_kernel = time.perf_counter()
            sab = spatial_kernel(
                body.normals,
                paths.k_hat,
                paths.power,
                n_tilde if n_tilde is not None else self.n_tilde,
                T0 if T0 is not None else self.T0,
                freq_hz if freq_hz is not None else self.freq_hz,
                fresnel=fresnel,
                polarisation=polarisation,
                q=q,
                curvature=curvature,
                diffraction=diffraction,
                curvature_H=curvature_H,
            )
            sab = _to_numpy(sab)
            kernel_ms = (time.perf_counter() - t_kernel) * 1e3
            if _timings is not None:
                _timings["kernel_ms"] = kernel_ms
            with _timings_lock:
                _last_timings["kernel_ms"] = kernel_ms
        elif mode in ("coherent", "ecbf"):
            return self._compute_coherent(
                body,
                paths,
                fidelity_level,
                precoder=precoder,
                h=h,
                P_abs_max=P_abs_max,
                body_mass=body_mass,
                spatial_averaging=spatial_averaging,
                freq_hz=freq_hz,
                n_tilde=n_tilde,
                sigma=sigma,
                mode=mode,
                corrections=tuple(corrections),
            )
        else:
            # bound or aggregate: use legacy dispatch
            sab = self._dispatch(
                body,
                paths,
                fidelity_level,
                A_ab=A_ab,
                D_max=D_max,
                sh_coeffs=sh_coeffs,
                sh_L=sh_L,
                D_table=D_table,
                D_dirs=D_dirs,
                q=q,
                curvature_H=curvature_H,
                freq_hz=freq_hz,
                n_tilde=n_tilde,
                T0=T0,
            )
            sab = _to_numpy(sab)

        return self._build_result(
            body,
            paths,
            sab,
            fidelity_level,
            body_mass=body_mass,
            freq_hz=freq_hz,
            mode=mode,
            corrections=tuple(corrections),
            spatial_averaging=spatial_averaging,
            _timings=_timings,
        )

    def _compute_coherent(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        level: int,
        precoder: Precoder | None = None,
        h: np.ndarray | None = None,
        P_abs_max: float = DEFAULT_P_ABS_MAX,
        body_mass: float | None = None,
        spatial_averaging: bool = True,
        freq_hz: float | None = None,
        n_tilde: complex | None = None,
        sigma: float | None = None,
        mode: str | None = None,
        corrections: tuple[str, ...] = (),
    ) -> DosimetryResult:
        """Dispatch coherent levels 7-8."""
        n_elements = paths.n_elements
        x_star = None
        active_freq_hz = freq_hz if freq_hz is not None else self.freq_hz
        active_n_tilde = n_tilde if n_tilde is not None else self.n_tilde
        active_sigma = sigma if sigma is not None else self.tissue.sigma

        if level == 7:
            if precoder is None:
                raise ValueError("Level 7 requires a precoder")
            from aegis.kernels.level7_coherent import level7_coherent

            sab, Q, eigenvalues, rho = level7_coherent(
                body.normals,
                body.centroids,
                body.areas,
                paths.k_hat,
                paths.psi,
                paths.element_index,
                precoder.x,
                active_n_tilde,
                active_sigma,
                active_freq_hz,
                n_elements,
                h=h,
            )
        elif level == 8:
            if h is None:
                raise ValueError("Level 8 requires UE channel vector h")
            from aegis.kernels.level8_ecbf import level8_ecbf

            P = precoder.power if precoder is not None else 1.0
            sab, Q, eigenvalues, x_star, rho = level8_ecbf(
                body.normals,
                body.centroids,
                body.areas,
                paths.k_hat,
                paths.psi,
                paths.element_index,
                h,
                active_n_tilde,
                active_sigma,
                active_freq_hz,
                n_elements,
                P=P,
                P_abs_max=P_abs_max,
            )
        else:
            raise ValueError(f"Unknown coherent level {level}")

        sab = _to_numpy(sab)
        Q = _to_numpy(Q)
        eigenvalues = _to_numpy(eigenvalues)
        if x_star is not None:
            x_star = _to_numpy(x_star)

        # Coherent incident power density: use the actual precoder that
        # produced sab, not the incoherent per-path power sum.
        x_for_sinc = _to_numpy(x_star if x_star is not None else precoder.x)
        sinc_coherent = coherent_sinc(
            _to_numpy(body.centroids),
            _to_numpy(paths.k_hat),
            _to_numpy(paths.psi),
            np.asarray(paths.element_index),
            x_for_sinc,
            active_freq_hz,
        )

        return self._build_result(
            body,
            paths,
            sab,
            level,
            body_mass=body_mass,
            freq_hz=active_freq_hz,
            mode=mode,
            corrections=corrections,
            Q=Q,
            rho=rho,
            eigenvalues=eigenvalues,
            x_star=x_star,
            spatial_averaging=spatial_averaging,
            sinc=sinc_coherent,
        )

    def _dispatch(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        level: int,
        **kwargs,
    ) -> np.ndarray:
        """Dispatch to the appropriate kernel."""
        if level == 0:
            return self._level0(body, paths, **kwargs)
        elif level == 1:
            return self._level1(body, paths, **kwargs)
        elif level == 2:
            return self._level2(body, paths, **kwargs)
        elif level == 3:
            return self._level3(body, paths, **kwargs)
        elif level == 4:
            return self._level4(body, paths, **kwargs)
        elif level == 5:
            return self._level5(body, paths, **kwargs)
        elif level == 6:
            return self._level6(body, paths, **kwargs)
        raise ValueError(f"Unknown level {level}")

    def _level0(self, body: BodyMesh, paths: PropagationPaths, **kwargs) -> np.ndarray:
        from aegis.kernels.level0_bound import level0_bound

        A_ab = kwargs.get("A_ab")
        D_max = kwargs.get("D_max")
        T0 = kwargs.get("T0", self.T0)
        if A_ab is None or D_max is None:
            raise ValueError("Level 0 requires A_ab and D_max")
        sab, _ = level0_bound(
            body.total_area,
            A_ab,
            D_max,
            paths.power,
            T0,
            body.n_triangles,
        )
        return sab

    def _level1(self, body: BodyMesh, paths: PropagationPaths, **kwargs) -> np.ndarray:
        from aegis.kernels.level1_aggregate import level1_aggregate

        A_ab = kwargs.get("A_ab")
        T0 = kwargs.get("T0", self.T0)
        if A_ab is None:
            raise ValueError("Level 1 requires A_ab")
        sab, _ = level1_aggregate(
            body.total_area,
            A_ab,
            paths.k_hat,
            paths.power,
            T0,
            body.n_triangles,
            sh_coeffs=kwargs.get("sh_coeffs"),
            sh_L=kwargs.get("sh_L", 4),
            D_table=kwargs.get("D_table"),
            D_dirs=kwargs.get("D_dirs"),
        )
        return sab

    def _level2(self, body: BodyMesh, paths: PropagationPaths, **kwargs) -> np.ndarray:
        from aegis.kernels.level2_geometric import level2_geometric

        return level2_geometric(body.normals, paths.k_hat, paths.power, kwargs.get("T0", self.T0))

    def _level3(self, body: BodyMesh, paths: PropagationPaths, **kwargs) -> np.ndarray:
        from aegis.kernels.level3_fresnel import level3_fresnel

        return level3_fresnel(body.normals, paths.k_hat, paths.power, kwargs.get("n_tilde", self.n_tilde))

    def _level4(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        q: np.ndarray | float = 0.0,
        **kwargs,
    ) -> np.ndarray:
        from aegis.kernels.level4_polarisation import level4_polarisation

        return level4_polarisation(
            body.normals,
            paths.k_hat,
            paths.power,
            kwargs.get("n_tilde", self.n_tilde),
            q=q,
        )

    def _level5(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        curvature_H: np.ndarray | None = None,
        **kwargs,
    ) -> np.ndarray:
        from aegis.kernels.level5_curvature import level5_curvature

        if curvature_H is None:
            curvature_H = np.zeros(body.n_triangles)
        return level5_curvature(
            body.normals,
            paths.k_hat,
            paths.power,
            kwargs.get("n_tilde", self.n_tilde),
            kwargs.get("T0", self.T0),
            curvature_H,
            kwargs.get("freq_hz", self.freq_hz),
        )

    def _level6(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        curvature_H: np.ndarray | None = None,
        **kwargs,
    ) -> np.ndarray:
        from aegis.kernels.level6_diffraction import level6_diffraction

        if curvature_H is None:
            curvature_H = np.zeros(body.n_triangles)
        return level6_diffraction(
            body.normals,
            paths.k_hat,
            paths.power,
            kwargs.get("n_tilde", self.n_tilde),
            kwargs.get("T0", self.T0),
            curvature_H,
            kwargs.get("freq_hz", self.freq_hz),
        )

    def sweep_levels(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        levels: list[int] | None = None,
        *,
        body_mass: float | None = None,
        spatial_averaging: bool = True,
        A_ab: float | None = None,
        D_max: float | None = None,
        q: np.ndarray | float = 0.0,
        curvature_H: np.ndarray | None = None,
        freq_hz: float | None = None,
    ) -> dict[int, DosimetryResult]:
        """Compute dosimetry at multiple fidelity levels for convergence analysis.

        Runs each requested level and returns a dict mapping level -> result.
        Levels that require unavailable parameters are silently skipped.

        Parameters
        ----------
        body : BodyMesh
        paths : PropagationPaths
        levels : list of ints, or None for all feasible incoherent levels
        body_mass : body mass [kg] for SAR (optional)
        A_ab : absorption area for levels 0-1
        D_max : max directivity for level 0
        q : TM excess for level 4
        curvature_H : mean curvature for levels 5-6
        freq_hz : frequency override

        Returns
        -------
        dict mapping int level -> DosimetryResult
        """
        if levels is None:
            levels = list(range(7))  # 0-6, skip coherent

        # Determine which levels are feasible given the available parameters
        _requires = {
            0: ("A_ab", "D_max"),
            1: ("A_ab",),
        }

        params = {"A_ab": A_ab, "D_max": D_max}

        results: dict[int, DosimetryResult] = {}
        for level in levels:
            # Skip levels whose required params are missing
            missing = [p for p in _requires.get(level, ()) if params.get(p) is None]
            if missing:
                continue

            result = self.compute(
                body,
                paths,
                level=level,
                body_mass=body_mass,
                spatial_averaging=spatial_averaging,
                A_ab=A_ab,
                D_max=D_max,
                q=q,
                curvature_H=curvature_H,
                freq_hz=freq_hz,
            )
            results[level] = result

        return results
