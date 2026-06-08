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
from aegis.geometry import fock_gate
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

# Engine-layer diffraction-gate selector. The kernel maps the legacy bool
# True->"gelu" for back-compat; the engine maps it True->"fock" (the user-facing
# default, D7) and always supplies the in-plane radius (DECISIONS.md L8).
# The Fock-parameter helpers and their guards live in geometry.fock_gate so the
# MIMO compute path (mimo/compute.py) shares one source of truth.
_ENGINE_DIFFRACTION_MODELS = fock_gate.DIFFRACTION_MODELS


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
    _G_computing: dict[tuple, threading.Event] = {}
    _G_CACHE_MAX: int = 16

    # Per-body visibility LUT cache (the self-shadowing bake), same in-flight
    # dedup pattern as the averaging matrix. Keyed by the pose-dependent
    # vertex_hash, so a yawed body misses (visibility is direction-dependent).
    _vis_lut_cache: OrderedDict = OrderedDict()
    _vis_lock: threading.Lock = threading.Lock()
    _vis_computing: dict[tuple, threading.Event] = {}
    _VIS_CACHE_MAX: int = 8

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
            raise ValueError(f"freq_hz must be positive (in Hz), got {freq_hz}")
        if 0 < freq_hz < 1e3:
            import warnings

            warnings.warn(
                f"freq_hz={freq_hz} looks like GHz or MHz, not Hz. "
                f"Did you mean {freq_hz * 1e9:.0f} Hz ({freq_hz} GHz)?",
                stacklevel=3,
            )

        active_n_tilde = fresnel_n_complex(self.tissue.eps_r, self.tissue.sigma, freq_hz)
        active_T0 = fresnel_T0(active_n_tilde)
        return float(freq_hz), active_n_tilde, active_T0, self.tissue.sigma

    @staticmethod
    def _resolve_diffraction_model(diffraction_model: str | None, diffraction: bool | None) -> str:
        """Resolve the engine-layer gate selector.

        An explicit ``diffraction_model`` always wins. Otherwise the legacy
        ``diffraction`` bool maps ``True -> "fock"`` (the new default, D7) and
        ``False -> "none"``; when neither is given (``diffraction is None``) the
        default is ``"fock"``. This differs from the kernel's own bool mapping
        (``True -> "gelu"``) on purpose: the engine always supplies ``fock_R``,
        direct kernel callers do not (DECISIONS.md L8).
        """
        if diffraction_model is not None:
            if diffraction_model not in _ENGINE_DIFFRACTION_MODELS:
                raise ValueError(
                    f"diffraction_model must be one of {_ENGINE_DIFFRACTION_MODELS}, got {diffraction_model!r}"
                )
            return diffraction_model
        if diffraction is None:
            return "fock"
        return "fock" if diffraction else "none"

    @staticmethod
    def _validate_inter_body(inter_body: str) -> None:
        """Validate the inter-body backend selector.

        ``"off"`` (default) and ``"specular1"`` (single specular recapture
        bounce) are the implemented options; anything else is a ValueError.
        """
        if inter_body not in ("off", "specular1"):
            raise ValueError(f"inter_body must be 'off' or 'specular1', got {inter_body!r}")

    def _fock_params(
        self,
        body: BodyMesh,
        k_hat: np.ndarray,
        model: str,
        freq_hz: float,
        n_tilde: complex,
    ) -> tuple[np.ndarray | None, complex | None, complex | None]:
        """Fock radius and the representative impedance-corrected eigenvalues.

        Thin wrapper over :func:`aegis.geometry.fock_gate.fock_params`, the
        shared source of truth used by the MIMO compute path too.
        """
        return fock_gate.fock_params(body, k_hat, model, freq_hz, n_tilde)

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
            # Another thread is already computing this matrix, wait for it
            if key in self._G_computing:
                event = self._G_computing[key]
                self._G_lock.release()
                event.wait()
                self._G_lock.acquire()
                if key in self._G_cache:
                    self._G_cache.move_to_end(key)
                    return self._G_cache[key]
            # Mark this key as being computed
            event = threading.Event()
            self._G_computing[key] = event

        from aegis.geometry.averaging import precompute_averaging_matrix

        try:
            G = precompute_averaging_matrix(
                body.centroids,
                body.areas,
                target_area_m2,
            )
        finally:
            with self._G_lock:
                self._G_computing.pop(key, None)
                event.set()

        with self._G_lock:
            # Evict least-recently-used entries if cache is full
            while len(self._G_cache) >= self._G_CACHE_MAX:
                self._G_cache.popitem(last=False)
            self._G_cache[key] = G

        return G

    def _get_vis_lut(self, body: BodyMesh, resolution: int, gate: str):
        """Cached per-body visibility LUT (double-checked in-flight dedup).

        Mirrors :meth:`_get_G`; the worker calls ``visibility.get_or_bake`` which
        checks the disk cache before baking. Keyed by the pose-dependent
        ``vertex_hash`` so a yawed body misses.
        """
        key = (body.vertex_hash, resolution, gate)
        with self._vis_lock:
            if key in self._vis_lut_cache:
                self._vis_lut_cache.move_to_end(key)
                return self._vis_lut_cache[key]
            if key in self._vis_computing:
                event = self._vis_computing[key]
                self._vis_lock.release()
                event.wait()
                self._vis_lock.acquire()
                if key in self._vis_lut_cache:
                    self._vis_lut_cache.move_to_end(key)
                    return self._vis_lut_cache[key]
            event = threading.Event()
            self._vis_computing[key] = event

        from aegis.geometry import visibility as _vis

        try:
            lut = _vis.get_or_bake(body, resolution, gate)
        finally:
            with self._vis_lock:
                self._vis_computing.pop(key, None)
                event.set()

        with self._vis_lock:
            while len(self._vis_lut_cache) >= self._VIS_CACHE_MAX:
                self._vis_lut_cache.popitem(last=False)
            self._vis_lut_cache[key] = lut

        return lut

    def _distal_inputs(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        *,
        self_shadow: bool,
        source_pos: np.ndarray | None,
        vis_resolution: int,
        occlusion: np.ndarray | None,
    ) -> dict[str, np.ndarray] | None:
        """Build the distal-gate kwargs ``{clearance, R_occ, distal_d1, distal_d2}``.

        Returns ``None`` (gate is a no-op) when self-shadowing is off, when an
        explicit ``occlusion`` override is supplied (it bypasses the LUT), or when
        the body is convex (the LUT short-circuits to all-exposed). Far field uses
        ``paths.k_hat``; near field (``source_pos`` given) uses the per-triangle
        source->point direction.
        """
        if not self_shadow or occlusion is not None:
            return None
        from aegis.geometry import visibility as _vis

        lut = self._get_vis_lut(body, vis_resolution, "erf")
        if bool(lut.exposed_mask.all()):
            return None
        centroids = _to_numpy(body.centroids)
        if source_pos is not None:
            src = np.asarray(source_pos, dtype=float)
            k = centroids - src
            k = k / np.linalg.norm(k, axis=1, keepdims=True)
            clr, R_occ, d1, d2 = _vis.query_visibility(lut, k, centroids, source_pos=src)
        else:
            clr, R_occ, d1, d2 = _vis.query_visibility(lut, _to_numpy(paths.k_hat), centroids, source_pos=None)
        return {"clearance": clr, "R_occ": R_occ, "distal_d1": d1, "distal_d2": d2}

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
            pct = 100 * (n_nan + n_inf) / sab.size
            raise ValueError(
                f"Kernel produced non-finite sab values "
                f"({n_nan} NaN, {n_inf} Inf out of {sab.size} triangles, {pct:.1f}%). "
                f"Level {fidelity_level} kernel. "
                f"Common causes: degenerate mesh triangles with zero area, "
                f"paths with invalid k_hat directions, or extreme tissue parameters."
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
        # Per-direction visibility (paper eq. 3.1: S_ab(r) = S_inc T_0 ReLU(mu) O(r, k_hat))
        # Shape: (M_tri,) for single path, or (M_tri, N_paths) for multi-path.
        # Values in [0, 1]. None => O = 1 everywhere (assume convex body).
        occlusion: np.ndarray | None = None,
        # Level 7-8 coherent MIMO
        precoder: Precoder | None = None,
        h: np.ndarray | None = None,
        P_abs_max: float = DEFAULT_P_ABS_MAX,
        # Mode-based API
        mode: str | None = None,
        fresnel: bool = True,
        polarisation: bool = False,
        diffraction: bool | None = None,
        diffraction_model: str | None = None,
        inter_body: str = "off",
        curvature: bool = False,
        self_shadow: bool = False,
        source_pos: np.ndarray | None = None,
        vis_resolution: int = 32,
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
        diffraction : legacy bool. At the engine layer True -> "fock", False ->
            "none". An explicit ``diffraction_model`` always wins. ``None``
            (the default) leaves the model at its "fock" default.
        diffraction_model : shadow-edge gate "none" | "gelu" | "fock". Default
            "fock". Levels 0-5 have no shadow gate and ignore diffraction_model;
            it applies to spatial mode, level 6, and coherent levels 7-8.
        inter_body : "off" (default) or "specular1". "specular1" adds one
            specular recapture bounce (off-by-default, single bounce): each lit
            triangle's Fresnel-reflected ray is cast through the visibility BVH
            and, when it strikes another body triangle, the recaptured power is
            deposited there. Applies to spatial mode and legacy levels >= 2.
        curvature : enable curvature correction (spatial mode)
        self_shadow : enable distal self-shadowing (one body part shadowing
            another) via the baked per-body visibility LUT and the distal Fock
            gate. Default False (opt-in): turning it on changes the dose for
            non-convex bodies and breaks the spatial==level-N composability
            invariant, so it is off until explicitly requested. Convex bodies
            short-circuit to a no-op. Applies to spatial mode, level 6, and
            coherent levels 7-8; ignored when an explicit ``occlusion`` override
            is supplied.
        source_pos : (3,) point-source position for near-field self-shadowing.
            None (default) uses the far-field path directions in ``paths.k_hat``.
        vis_resolution : octahedral LUT resolution for the self-shadow bake.
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

        if body_mass is not None and (not np.isfinite(body_mass) or body_mass <= 0):
            raise ValueError("body_mass must be positive (and finite) when provided")

        active_freq_hz, active_n_tilde, active_T0, active_sigma = self._active_em_params(freq_hz)

        effective_model = self._resolve_diffraction_model(diffraction_model, diffraction)
        self._validate_inter_body(inter_body)

        # Distal self-shadowing gate inputs (spatial + coherent modes; the gate
        # is built inside the kernel from these per-(M, N) arrays). A convex body
        # or an explicit occlusion override returns None (no-op).
        distal = None
        if mode in ("spatial", "coherent", "ecbf"):
            distal = self._distal_inputs(
                body,
                paths,
                self_shadow=self_shadow,
                source_pos=source_pos,
                vis_resolution=vis_resolution,
                occlusion=occlusion,
            )

        # Mode-based path
        if mode is not None:
            result = self._compute_mode(
                body,
                paths,
                mode=mode,
                fresnel=fresnel,
                polarisation=polarisation,
                diffraction_model=effective_model,
                curvature=curvature,
                distal=distal,
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
            if mode == "spatial" and (occlusion is not None or inter_body == "specular1"):
                # Re-build the result with the occlusion-multiplied direct sab
                # plus the optional specular recapture. Occlusion post-multiplies
                # the per-triangle Sab (paper eq. 3.1's O(r, k_hat) factor);
                # specular1 adds a single recapture bounce on top.
                new_sab = result.sab
                if occlusion is not None:
                    occ = np.asarray(occlusion, dtype=result.sab.dtype)
                    if occ.ndim == 2:
                        pw = np.asarray(paths.power, dtype=result.sab.dtype)
                        occ = (occ * pw[None, :]).sum(axis=1) / max(pw.sum(), 1e-30)
                    new_sab = new_sab * occ
                if inter_body == "specular1":
                    from aegis.geometry.inter_body import specular1_sab

                    new_sab = new_sab + specular1_sab(body, paths, active_n_tilde)
                result = self._build_result(
                    body,
                    paths,
                    new_sab,
                    result.fidelity_level,
                    body_mass=body_mass,
                    freq_hz=active_freq_hz,
                    spatial_averaging=spatial_averaging,
                    _timings=_timings,
                )
            return result

        # Legacy level-based path
        if level < 0 or level > 8:
            raise ValueError(f"Fidelity level must be 0-8, got {level}")

        if level >= 7:
            fock_R, q_F_s, q_F_h = self._fock_params(body, paths.k_hat, effective_model, active_freq_hz, active_n_tilde)
            distal = self._distal_inputs(
                body,
                paths,
                self_shadow=self_shadow,
                source_pos=source_pos,
                vis_resolution=vis_resolution,
                occlusion=occlusion,
            )
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
                fock_R=fock_R,
                q_F_s=q_F_s,
                q_F_h=q_F_h,
                distal=distal,
            )

        # Only level 6 consumes the gate on the legacy level path; levels 2-5
        # have no shadow gate, so the Fock radius is computed only when needed.
        fock_R = q_F_s = q_F_h = None
        distal = None
        if level == 6:
            fock_R, q_F_s, q_F_h = self._fock_params(body, paths.k_hat, effective_model, active_freq_hz, active_n_tilde)
            distal = self._distal_inputs(
                body,
                paths,
                self_shadow=self_shadow,
                source_pos=source_pos,
                vis_resolution=vis_resolution,
                occlusion=occlusion,
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
            diffraction_model=effective_model,
            fock_R=fock_R,
            q_F_s=q_F_s,
            q_F_h=q_F_h,
            **(distal or {}),
        )
        sab = _to_numpy(sab)
        if occlusion is not None and level is not None and level >= 2:
            occ = np.asarray(occlusion, dtype=sab.dtype)
            if occ.ndim == 2:
                # paths combine inside the kernel via @ power, so occ must already
                # be reduced to (M,) before reaching here. Reduce by power-weighted
                # mean if a (M, N) array was passed.
                pw = np.asarray(paths.power, dtype=sab.dtype)
                occ = (occ * pw[None, :]).sum(axis=1) / max(pw.sum(), 1e-30)
            sab = sab * occ
        if inter_body == "specular1" and level is not None and level >= 2:
            from aegis.geometry.inter_body import specular1_sab

            sab = sab + specular1_sab(body, paths, active_n_tilde)
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
        diffraction: bool | None = None,
        diffraction_model: str | None = None,
        inter_body: str = "off",
        curvature: bool = False,
        freq_hz: float | None = None,
    ):
        """Return per-triangle S_ab as a raw array (JAX or NumPy).

        Unlike compute(), this does not convert to NumPy or wrap in
        DosimetryResult. Use inside jax.grad boundaries for differentiable
        optimization. The diffraction-model resolution mirrors compute(), so
        compute_sab stays numerically consistent with compute().sab (default
        "fock"). The Fock radius is a geometry constant, so threading it does not
        break autodiff w.r.t. the precoder or source. ``inter_body`` mirrors
        compute()'s validation contract but is otherwise ignored here: the
        single specular recapture is a ray-cast pass that is not differentiable,
        so it does not apply to the autodiff path.
        """
        if level is not None and mode is not None:
            raise ValueError(_ERR_LEVEL_AND_MODE)

        # Default: neither given -> behave like old level=2
        if level is None and mode is None:
            level = 2

        active_freq_hz, active_n_tilde, active_T0, active_sigma = self._active_em_params(freq_hz)
        effective_model = self._resolve_diffraction_model(diffraction_model, diffraction)
        # The single specular recapture is a non-differentiable ray-cast pass;
        # validate-and-ignore here to mirror compute()'s error contract.
        self._validate_inter_body(inter_body)

        # Mode-based path for spatial
        if mode is not None:
            if mode == "spatial":
                from aegis.kernels.spatial import spatial_kernel

                fock_R, q_F_s, q_F_h = self._fock_params(
                    body, paths.k_hat, effective_model, active_freq_hz, active_n_tilde
                )
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
                    diffraction_model=effective_model,
                    curvature_H=curvature_H,
                    fock_R=fock_R,
                    q_F_s=q_F_s,
                    q_F_h=q_F_h,
                )
            # For non-spatial modes, map to the legacy dispatch
            mode_to_level = {
                "bound": 0,
                "aggregate": 1,
                "coherent": 7,
                "ecbf": 8,
            }
            if mode not in mode_to_level:
                _all = ("spatial",) + tuple(mode_to_level)
                raise ValueError(f"Unknown mode '{mode}', expected one of {_all}")
            level = mode_to_level[mode]

        if level < 0 or level > 8:
            raise ValueError(f"Fidelity level must be 0-8, got {level}")

        if level <= 6:
            fock_R = q_F_s = q_F_h = None
            if level == 6:
                fock_R, q_F_s, q_F_h = self._fock_params(
                    body, paths.k_hat, effective_model, active_freq_hz, active_n_tilde
                )
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
                diffraction_model=effective_model,
                fock_R=fock_R,
                q_F_s=q_F_s,
                q_F_h=q_F_h,
            )

        # Coherent levels 7-8
        x = precoder_x
        if x is None and precoder is not None:
            x = precoder.x

        n_elements = paths.n_elements
        fock_R, q_F_s, q_F_h = self._fock_params(body, paths.k_hat, effective_model, active_freq_hz, active_n_tilde)

        if level == 7:
            if x is None:
                raise ValueError(
                    "Level 7 (coherent MIMO) requires a precoding vector. "
                    "Pass precoder=Precoder(x=...) or precoder_x=np.array(...)."
                )
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
                fock_R=fock_R,
                q_F_s=q_F_s,
                q_F_h=q_F_h,
            )
            return sab

        if level == 8:
            if h is None:
                raise ValueError(
                    "Level 8 (ECBF) requires channel vector h of shape (M_ant,). "
                    "Use level 7 if you only have a precoder without a channel estimate."
                )
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
                fock_R=fock_R,
                q_F_s=q_F_s,
                q_F_h=q_F_h,
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
        diffraction_model: str = "none",
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
        distal: dict[str, np.ndarray] | None = None,
        _timings: dict | None = None,
    ) -> DosimetryResult:
        """Dispatch based on mode string with composable correction flags."""
        _valid_modes = ("bound", "aggregate", "spatial", "coherent", "ecbf")
        if mode not in _valid_modes:
            raise ValueError(f"Unknown mode '{mode}', expected one of {_valid_modes}")

        diffraction_active = diffraction_model != "none"

        # Build corrections tuple for result metadata
        corrections: list[str] = []
        if mode == "spatial":
            if fresnel:
                corrections.append("fresnel")
            if polarisation:
                corrections.append("polarisation")
            if curvature:
                corrections.append("curvature")
            if diffraction_active:
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
            if diffraction_active:
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
            # Use the physical polarisation from psi only when the paths carry a
            # real one; otherwise fall back to the legacy scalar q knob.
            psi_arg = paths.psi if (polarisation and paths.polarised) else None
            kernel_freq = freq_hz if freq_hz is not None else self.freq_hz
            kernel_n_tilde = n_tilde if n_tilde is not None else self.n_tilde
            fock_R, q_F_s, q_F_h = self._fock_params(body, paths.k_hat, diffraction_model, kernel_freq, kernel_n_tilde)
            sab = spatial_kernel(
                body.normals,
                paths.k_hat,
                paths.power,
                kernel_n_tilde,
                T0 if T0 is not None else self.T0,
                kernel_freq,
                fresnel=fresnel,
                polarisation=polarisation,
                q=q,
                psi=psi_arg,
                curvature=curvature,
                diffraction_model=diffraction_model,
                curvature_H=curvature_H,
                fock_R=fock_R,
                q_F_s=q_F_s,
                q_F_h=q_F_h,
                **(distal or {}),
            )
            sab = _to_numpy(sab)
            kernel_ms = (time.perf_counter() - t_kernel) * 1e3
            if _timings is not None:
                _timings["kernel_ms"] = kernel_ms
            with _timings_lock:
                _last_timings["kernel_ms"] = kernel_ms
        elif mode in ("coherent", "ecbf"):
            coh_freq = freq_hz if freq_hz is not None else self.freq_hz
            coh_n_tilde = n_tilde if n_tilde is not None else self.n_tilde
            fock_R, q_F_s, q_F_h = self._fock_params(body, paths.k_hat, diffraction_model, coh_freq, coh_n_tilde)
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
                fock_R=fock_R,
                q_F_s=q_F_s,
                q_F_h=q_F_h,
                distal=distal,
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
        fock_R: np.ndarray | None = None,
        q_F_s: complex | None = None,
        q_F_h: complex | None = None,
        distal: dict[str, np.ndarray] | None = None,
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
                fock_R=fock_R,
                q_F_s=q_F_s,
                q_F_h=q_F_h,
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
                fock_R=fock_R,
                q_F_s=q_F_s,
                q_F_h=q_F_h,
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
            psi=paths.psi if paths.polarised else None,
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
            diffraction_model=kwargs.get("diffraction_model"),
            fock_R=kwargs.get("fock_R"),
            q_F_s=kwargs.get("q_F_s"),
            q_F_h=kwargs.get("q_F_h"),
            clearance=kwargs.get("clearance"),
            R_occ=kwargs.get("R_occ"),
            distal_d1=kwargs.get("distal_d1"),
            distal_d2=kwargs.get("distal_d2"),
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
