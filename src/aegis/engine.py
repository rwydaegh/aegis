"""DosimetryEngine: main entry point for absorbed power density computation.

Dispatches to the appropriate kernel based on fidelity level (0-8).
Levels 0-6 are incoherent. Levels 7-8 are coherent MIMO.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from aegis._array_backend import JAX_AVAILABLE
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.result import DosimetryResult
from aegis.tissue.dielectric import TissueModel

if TYPE_CHECKING:
    from aegis.precoder import Precoder


def _to_numpy(arr):
    """Convert JAX arrays to NumPy. No-op for NumPy arrays."""
    if JAX_AVAILABLE:
        import numpy as _np

        return _np.asarray(arr)
    return arr


class DosimetryEngine:
    """Compute absorbed power density on a body mesh from propagation paths.

    Parameters
    ----------
    tissue : TissueModel
        Tissue electromagnetic properties at the operating frequency.
    """

    def __init__(self, tissue: TissueModel) -> None:
        self.tissue = tissue
        self.T0 = tissue.T0
        self.n_tilde = tissue.n_complex
        self.freq_hz = tissue.freq_hz

    def compute(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        level: int = 2,
        body_mass: float | None = None,
        spatial_averaging: bool = False,
        # Level 0/1 precomputed geometry (optional)
        A_ab: float | None = None,
        D_max: float | None = None,
        sh_coeffs: np.ndarray | None = None,
        sh_L: int = 4,
        D_table: np.ndarray | None = None,
        D_dirs: np.ndarray | None = None,
        # Level 4 polarisation
        q: np.ndarray | float = 0.0,
        # Level 5/6 curvature
        curvature_H: np.ndarray | None = None,
        # Level 7-8 coherent MIMO
        precoder: Precoder | None = None,
        h: np.ndarray | None = None,
        P_abs_max: float = 0.1,
    ) -> DosimetryResult:
        """Compute dosimetry at the specified fidelity level.

        Parameters
        ----------
        body : BodyMesh
        paths : PropagationPaths
        level : fidelity level 0-8
        body_mass : body mass [kg] for SAR computation
        spatial_averaging : apply ICNIRP 4 cm^2 averaging
        A_ab : absorption area [m^2] (required for levels 0-1)
        D_max : max directivity (required for level 0)
        sh_coeffs : SH coefficients for D(k_hat) (level 1)
        sh_L : SH degree (level 1)
        D_table : directivity LUT (level 1 alternative)
        D_dirs : directions for D_table (level 1 alternative)
        q : TM excess (level 4)
        curvature_H : (M,) twice mean curvature [1/m] (levels 5-6)
        precoder : Precoder with precoding vector x (required for level 7)
        h : (M_ant,) UE channel vector (required for level 8, optional for 7)
        P_abs_max : maximum absorbed power [W] (level 8)

        Returns
        -------
        DosimetryResult
        """
        if level < 0 or level > 8:
            raise ValueError(f"Fidelity level must be 0-8, got {level}")
        if body_mass is not None and body_mass <= 0:
            raise ValueError("body_mass must be positive when provided")

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
        )
        sab = _to_numpy(sab)

        # Total absorbed power: integrate S_ab over surface
        p_abs = float(np.sum(sab * body.areas))

        # Whole-body SAR
        sar_wb = p_abs / body_mass if body_mass is not None else None

        # Spatial averaging
        sab_averaged = None
        if spatial_averaging:
            from aegis.geometry.averaging import apply_spatial_averaging

            sab_averaged = apply_spatial_averaging(sab, body.centroids, body.areas)

        return DosimetryResult(
            sab=sab,
            p_abs=p_abs,
            fidelity_level=level,
            sab_averaged=sab_averaged,
            sar_wb=sar_wb,
        )

    def compute_sab(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        level: int = 2,
        *,
        precoder_x=None,
        precoder: Precoder | None = None,
        h=None,
        P_abs_max: float = 0.1,
        A_ab: float | None = None,
        D_max: float | None = None,
        sh_coeffs=None,
        sh_L: int = 4,
        D_table=None,
        D_dirs=None,
        q: float = 0.0,
        curvature_H=None,
    ):
        """Return per-triangle S_ab as a raw array (JAX or NumPy).

        Unlike compute(), this does not convert to NumPy or wrap in
        DosimetryResult. Use inside jax.grad boundaries for differentiable
        optimization.
        """
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
            )

        # Coherent levels 7-8
        x = precoder_x
        if x is None and precoder is not None:
            x = precoder.x

        sigma = self.tissue.sigma
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
                self.n_tilde,
                sigma,
                self.freq_hz,
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
                self.n_tilde,
                sigma,
                self.freq_hz,
                n_elements,
                P=P,
                P_abs_max=P_abs_max,
            )
            return sab

        raise ValueError(f"Unknown level {level}")

    def _compute_coherent(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        level: int,
        precoder: Precoder | None = None,
        h: np.ndarray | None = None,
        P_abs_max: float = 0.1,
        body_mass: float | None = None,
        spatial_averaging: bool = False,
    ) -> DosimetryResult:
        """Dispatch coherent levels 7-8."""
        sigma = self.tissue.sigma
        n_elements = paths.n_elements
        x_star = None

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
                self.n_tilde,
                sigma,
                self.freq_hz,
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
                self.n_tilde,
                sigma,
                self.freq_hz,
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

        p_abs = float(np.sum(sab * body.areas))
        sar_wb = p_abs / body_mass if body_mass is not None else None

        sab_averaged = None
        if spatial_averaging:
            from aegis.geometry.averaging import apply_spatial_averaging

            sab_averaged = apply_spatial_averaging(sab, body.centroids, body.areas)

        return DosimetryResult(
            sab=sab,
            p_abs=p_abs,
            fidelity_level=level,
            sab_averaged=sab_averaged,
            sar_wb=sar_wb,
            Q=Q,
            rho=rho,
            eigenvalues=eigenvalues,
            x_star=x_star,
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
            return self._level2(body, paths)
        elif level == 3:
            return self._level3(body, paths)
        elif level == 4:
            return self._level4(body, paths, q=kwargs.get("q", 0.0))
        elif level == 5:
            return self._level5(body, paths, curvature_H=kwargs.get("curvature_H"))
        elif level == 6:
            return self._level6(body, paths, curvature_H=kwargs.get("curvature_H"))
        raise ValueError(f"Unknown level {level}")

    def _level0(self, body: BodyMesh, paths: PropagationPaths, **kwargs) -> np.ndarray:
        from aegis.kernels.level0_bound import level0_bound

        A_ab = kwargs.get("A_ab")
        D_max = kwargs.get("D_max")
        if A_ab is None or D_max is None:
            raise ValueError("Level 0 requires A_ab and D_max")
        sab, _ = level0_bound(
            body.total_area,
            A_ab,
            D_max,
            paths.power,
            self.T0,
            body.n_triangles,
        )
        return sab

    def _level1(self, body: BodyMesh, paths: PropagationPaths, **kwargs) -> np.ndarray:
        from aegis.kernels.level1_aggregate import level1_aggregate

        A_ab = kwargs.get("A_ab")
        if A_ab is None:
            raise ValueError("Level 1 requires A_ab")
        sab, _ = level1_aggregate(
            body.total_area,
            A_ab,
            paths.k_hat,
            paths.power,
            self.T0,
            body.n_triangles,
            sh_coeffs=kwargs.get("sh_coeffs"),
            sh_L=kwargs.get("sh_L", 4),
            D_table=kwargs.get("D_table"),
            D_dirs=kwargs.get("D_dirs"),
        )
        return sab

    def _level2(self, body: BodyMesh, paths: PropagationPaths) -> np.ndarray:
        from aegis.kernels.level2_geometric import level2_geometric

        return level2_geometric(body.normals, paths.k_hat, paths.power, self.T0)

    def _level3(self, body: BodyMesh, paths: PropagationPaths) -> np.ndarray:
        from aegis.kernels.level3_fresnel import level3_fresnel

        return level3_fresnel(body.normals, paths.k_hat, paths.power, self.n_tilde)

    def _level4(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        q: np.ndarray | float = 0.0,
    ) -> np.ndarray:
        from aegis.kernels.level4_polarisation import level4_polarisation

        return level4_polarisation(
            body.normals,
            paths.k_hat,
            paths.power,
            self.n_tilde,
            q=q,
        )

    def _level5(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        curvature_H: np.ndarray | None = None,
    ) -> np.ndarray:
        from aegis.kernels.level5_curvature import level5_curvature

        if curvature_H is None:
            curvature_H = np.zeros(body.n_triangles)
        return level5_curvature(
            body.normals,
            paths.k_hat,
            paths.power,
            self.n_tilde,
            self.T0,
            curvature_H,
            self.freq_hz,
        )

    def _level6(
        self,
        body: BodyMesh,
        paths: PropagationPaths,
        curvature_H: np.ndarray | None = None,
    ) -> np.ndarray:
        from aegis.kernels.level6_diffraction import level6_diffraction

        if curvature_H is None:
            curvature_H = np.zeros(body.n_triangles)
        return level6_diffraction(
            body.normals,
            paths.k_hat,
            paths.power,
            self.n_tilde,
            self.T0,
            curvature_H,
            self.freq_hz,
        )
