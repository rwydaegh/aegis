"""Point-source near-field kernel for a hand-held device.

The source radiates a known free-space pattern from a point at ``position`` with
body-frame orientation ``rotation`` (a 3x3 rotation matrix mapping antenna-frame
vectors to world). Every body triangle sees a locally plane wave travelling along
the source -> centroid line of sight, with power density set by the inverse-square
spread and the sampled directivity.

The kernel reuses the AEGIS surface physics: the Fresnel power transmission
(``aegis.tissue.fresnel``) and the ReLU projection from the absorbed-power-density
law ``S_ab = S_inc * T_eff * ReLU(mu)``. It is written against the array backend,
so under JAX it is differentiable in ``position`` and ``rotation``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from aegis._array_backend import xp
from aegis.nearfield.patterns import AntennaPattern3D
from aegis.tissue.fresnel import _fresnel_core

if TYPE_CHECKING:
    from aegis.geometry.mesh import BodyMesh


@dataclass
class PhoneSource:
    """A hand-held radiating source.

    Parameters
    ----------
    position : (3,) source location in world coordinates [m]
    rotation : (3, 3) antenna-frame -> world rotation matrix
    pattern : AntennaPattern3D directivity pattern
    radiated_power_w : total radiated power P_rad [W]. The EIRP along a
        direction is ``P_rad * D(k)``. Default 1 W gives results normalised
        per watt of radiated power (W/m^2 per W). This is not the GOLIAT
        near-field normalization: that uses a band-specific CNR input power
        calibrated on a flat phantom. Conversion requires an explicit
        input-to-radiated power relationship or empirical calibration.
    """

    position: np.ndarray
    rotation: np.ndarray
    pattern: AntennaPattern3D
    radiated_power_w: float = 1.0

    @classmethod
    def from_euler(
        cls,
        position,
        pattern: AntennaPattern3D,
        yaw: float = 0.0,
        pitch: float = 0.0,
        roll: float = 0.0,
        radiated_power_w: float = 1.0,
    ) -> PhoneSource:
        """Build a source from intrinsic Z-Y-X Euler angles [rad]."""
        return cls(
            position=np.asarray(position, dtype=np.float64),
            rotation=euler_to_matrix(yaw, pitch, roll),
            pattern=pattern,
            radiated_power_w=radiated_power_w,
        )


def euler_to_matrix(yaw, pitch, roll):
    """Intrinsic Z-Y-X (yaw, pitch, roll) rotation matrix, backend-agnostic.

    Differentiable in the angles under the JAX backend.
    """
    cy, sy = xp.cos(yaw), xp.sin(yaw)
    cp, sp = xp.cos(pitch), xp.sin(pitch)
    cr, sr = xp.cos(roll), xp.sin(roll)
    rz = xp.stack(
        [
            xp.stack([cy, -sy, xp.zeros_like(cy)]),
            xp.stack([sy, cy, xp.zeros_like(cy)]),
            xp.stack([xp.zeros_like(cy), xp.zeros_like(cy), xp.ones_like(cy)]),
        ]
    )
    ry = xp.stack(
        [
            xp.stack([cp, xp.zeros_like(cp), sp]),
            xp.stack([xp.zeros_like(cp), xp.ones_like(cp), xp.zeros_like(cp)]),
            xp.stack([-sp, xp.zeros_like(cp), cp]),
        ]
    )
    rx = xp.stack(
        [
            xp.stack([xp.ones_like(cr), xp.zeros_like(cr), xp.zeros_like(cr)]),
            xp.stack([xp.zeros_like(cr), cr, -sr]),
            xp.stack([xp.zeros_like(cr), sr, cr]),
        ]
    )
    return rz @ ry @ rx


def incident_field(centroids, position, rotation, pattern: AntennaPattern3D, radiated_power_w):
    """Per-triangle incident power density and arrival direction.

    Returns
    -------
    s_inc : (M,) incident power density [W/m^2]
    k_hat : (M, 3) unit propagation direction (source -> centroid)
    dist : (M,) source -> centroid distance [m] (the near-field detour ``d1``)
    """
    pos = xp.asarray(position)
    rot = xp.asarray(rotation)
    rel = centroids - pos[None, :]  # (M, 3) source -> centroid
    dist = xp.sqrt(xp.sum(rel * rel, axis=-1))  # (M,)
    k_hat = rel / dist[:, None]

    # Express the line of sight in the antenna body frame: dir_ant = R^T k_hat.
    dir_ant = k_hat @ rot  # (M,3) @ (3,3) == (R^T k)^T rows
    directivity = pattern.sample(dir_ant)  # (M,)

    s_inc = radiated_power_w * directivity / (4.0 * np.pi * dist * dist)
    return s_inc, k_hat, dist


def _fock_radius_per_face(body: BodyMesh, k_hat: np.ndarray) -> np.ndarray:
    """In-incidence-plane Fock radius for per-face directions (NumPy only).

    ``k_hat`` is ``(M, 3)`` (single pose) or ``(B, M, 3)`` (a pose batch); each
    face carries its own source -> centroid direction, so unlike the engine's
    far-field ``fock_radius_per_path`` (one direction for all faces) the curvature
    is resolved per face. Returns ``(M,)`` or ``(B, M)``.
    """
    from aegis.geometry import curvature

    kh = np.asarray(k_hat, dtype=float)
    if kh.ndim == 2:
        return curvature.fock_radius(body, kh)
    return np.stack([curvature.fock_radius(body, kh[b]) for b in range(kh.shape[0])], axis=0)


def _local_gate(
    mu,
    k_hat,
    dist,
    *,
    body: BodyMesh | None,
    freq_hz: float,
    n_tilde: complex | None,
    diffraction_model: str,
    fock_R=None,
    q_F_h: complex | None = None,
):
    """Shadow-edge gate that replaces ``ReLU(mu)`` in the absorbed-power law.

    ``"none"`` returns the bare ``max(mu, 0)`` (back-compatible). ``"fock"``
    returns the near-field Fock local gate :func:`aegis.kernels.fock.fock_local`
    (GO obliquity * lit penumbra + creeping leakage), with the finite-distance
    wavefront taper ``w_nf`` set by ``d1 = dist`` and ``d2 = R |theta|``. In the
    GO / far-field limit the Fock gate reduces to ``max(mu, 0)``.

    The Fock gate needs the body curvature, so it is applied only when ``body`` is
    given; without it the call degrades to ``"none"``. ``fock_R`` and ``q_F_h`` may
    be precomputed (a NumPy radius array and the representative hard eigenvalue) to
    keep the gate differentiable under the JAX backend, where the curvature solve
    cannot trace a symbolic source position.
    """
    relu_mu = xp.maximum(mu, 0.0)
    if diffraction_model == "none" or body is None:
        return relu_mu
    if diffraction_model != "fock":
        raise ValueError(f"diffraction_model must be 'none' or 'fock', got {diffraction_model!r}")
    if n_tilde is None:
        raise ValueError("n_tilde required when diffraction_model='fock'")

    from aegis.geometry import fock_gate as _fg
    from aegis.kernels.fock import fock_local

    if fock_R is None:
        fock_R = _fock_radius_per_face(body, k_hat)
    if q_F_h is None:
        q_F_h = _fg.fock_q_hard(np.asarray(fock_R, dtype=float), freq_hz, n_tilde)
    # Incoherent, unpolarised: equal TE/TM split; soft keeps the PEC eigenvalue.
    return fock_local(mu, xp.asarray(fock_R), freq_hz, 0.5, 0.5, None, q_F_h, d1=dist, d2=None)


def _distal_factor(
    body: BodyMesh,
    k_hat,
    *,
    source_pos,
    freq_hz: float,
    n_tilde: complex | None,
    diffraction_model: str,
    resolution: int,
    lut=None,
):
    """Per-triangle distal self-shadow attenuation in ``[0, ~1]``.

    Bakes/loads the visibility LUT, queries the near-field clearance along the
    per-triangle source -> point direction, and evaluates
    :func:`aegis.kernels.fock.distal_gate`. Returns ``(M,)`` (the ``(M, 1)`` query
    is squeezed). Uses an equal soft/hard split (``w_s = w_p = 0.5``).

    ``q_F_h`` is the hard-boundary creeping eigenvalue keyed to the OCCLUDER
    radius ``R_occ`` (the part casting the shadow), self-consistent with
    :func:`distal_gate` which uses ``R_occ`` for its Fock curvature width. This
    deliberately differs from :func:`aegis.engine.compute`, which reuses its
    single body-surface-derived ``q_F_h`` for both the local and distal gates.

    A convex body short-circuits to an all-exposed LUT, so the gate is exactly
    1 everywhere (no-op). This is the NumPy path; it is not JAX-traced.

    ``source_pos`` should equal ``source.position``: ``k_hat`` is computed from
    ``source.position``, so passing a different ``source_pos`` mixes two source
    locations. The lab always passes them equal.

    ``lut`` may be supplied to reuse a pre-baked visibility LUT (the LUT is
    pose-independent, so the batch path bakes it once); ``None`` bakes/loads it.
    """
    if n_tilde is None:
        raise ValueError("n_tilde required when self_shadow=True")

    from aegis.geometry import fock_gate as _fg
    from aegis.geometry import visibility
    from aegis.kernels import fock

    if lut is None:
        lut = visibility.get_or_bake(body, resolution, "erf")
    # No active (shadowed) triangles -> fully exposed body. Mirror the engine's
    # short-circuit (engine._distal_kwargs returns None on lut.exposed_mask.all())
    # so a convex body is an exact no-op: the saturated-lit query would otherwise
    # drive distal_gate to ~0.96, not exactly 1, spuriously dimming lit faces.
    if bool(lut.exposed_mask.all()):
        return 1.0
    clearance, R_occ, d1, d2 = visibility.query_visibility(
        lut, np.asarray(k_hat), body.centroids, source_pos=np.asarray(source_pos)
    )
    # Hard creeping eigenvalue keyed to the occluder radius R_occ, self-consistent
    # with distal_gate (which uses R_occ for its Fock curvature width). This differs
    # from engine.compute, which reuses its single body-surface-derived q_F_h.
    q_F_h = _fg.fock_q_hard(np.asarray(R_occ, dtype=float), freq_hz, n_tilde)
    g = fock.distal_gate(
        clearance,
        R_occ,
        freq_hz,
        0.5,
        0.5,
        d1=d1,
        d2=d2,
        q_F_h=q_F_h,
        diffraction_model=diffraction_model,
    )
    return np.asarray(g).reshape(-1)


def compute_sab(
    centroids,
    normals,
    source: PhoneSource,
    t0: float,
    n_tilde: complex | None = None,
    fresnel: bool = True,
    body: BodyMesh | None = None,
    diffraction_model: str = "fock",
    fock_R=None,
    q_F_h: complex | None = None,
    self_shadow: bool = False,
    source_pos: np.ndarray | None = None,
    vis_resolution: int = 32,
):
    """Absorbed power density per triangle for a phone source.

    Parameters
    ----------
    centroids : (M, 3) triangle centroids [m]
    normals : (M, 3) unit outward normals
    source : PhoneSource
    t0 : float normal-incidence Fresnel power transmission (tissue.T0)
    n_tilde : complex refractive index; required when ``fresnel=True`` (the
        angle-dependent unpolarised transmission) or when the Fock gate is active.
    fresnel : if False use the constant ``t0`` (geometric level-2 style).
    body : BodyMesh providing the surface curvature for the Fock shadow gate.
        Required to apply ``diffraction_model="fock"``; without it the gate falls
        back to ``"none"``.
    diffraction_model : ``"fock"`` (default) applies the near-field Fock local
        gate (smooth penumbra + creeping leakage with the finite-distance
        wavefront taper), matching the engine default. ``"none"`` is the exact
        ``ReLU`` projection (back-compatible).
    fock_R, q_F_h : optionally precomputed Fock radius array and representative
        hard eigenvalue (see :func:`_local_gate`), to keep the gate differentiable
        in the source position under the JAX backend.
    self_shadow : if True, multiply in the distal self-shadowing gate (one body
        part shadowing another, e.g. an arm in front of the torso) via the baked
        visibility LUT. Requires ``body`` and ``n_tilde``. A convex body short-
        circuits to a no-op. Default False (back-compatible, leaves the Mie canary
        and existing callers unchanged). This is a NumPy-only path.
    source_pos : optional override for the near-field source position fed to the
        visibility query. Defaults to ``source.position``.
    vis_resolution : octahedral resolution of the baked visibility LUT.

    Returns
    -------
    sab : (M,) absorbed power density [W/m^2]
    """
    centroids = xp.asarray(centroids)
    normals = xp.asarray(normals)
    s_inc, k_hat, dist = incident_field(
        centroids, source.position, source.rotation, source.pattern, source.radiated_power_w
    )
    mu = xp.sum(normals * (-k_hat), axis=-1)  # incidence cosine
    relu_mu = xp.maximum(mu, 0.0)

    if fresnel:
        if n_tilde is None:
            raise ValueError("n_tilde required when fresnel=True")
        # _fresnel_core returns (r_s, r_p, T_s, T_p, t_s, t_p); we want the
        # power transmissions T_s, T_p and average them (unpolarised source).
        _, _, t_pow_s, t_pow_p, _, _ = _fresnel_core(relu_mu, n_tilde)
        t_eff = 0.5 * (t_pow_s + t_pow_p)
    else:
        t_eff = t0

    gate = _local_gate(
        mu,
        k_hat,
        dist,
        body=body,
        freq_hz=source.pattern.freq_hz,
        n_tilde=n_tilde,
        diffraction_model=diffraction_model,
        fock_R=fock_R,
        q_F_h=q_F_h,
    )
    sab = s_inc * t_eff * gate
    if self_shadow and body is not None:
        sab = sab * _distal_factor(
            body,
            k_hat,
            source_pos=source.position if source_pos is None else source_pos,
            freq_hz=source.pattern.freq_hz,
            n_tilde=n_tilde,
            diffraction_model=diffraction_model,
            resolution=vis_resolution,
        )
    return sab


def compute_sab_batch(
    centroids,
    normals,
    positions,
    rotations,
    pattern: AntennaPattern3D,
    t0: float,
    n_tilde: complex,
    radiated_power_w: float = 1.0,
    fresnel: bool = True,
    body: BodyMesh | None = None,
    diffraction_model: str = "fock",
    fock_R=None,
    q_F_h: complex | None = None,
    self_shadow: bool = False,
    vis_resolution: int = 32,
):
    """Vectorised absorbed power density for a batch of source poses.

    Evaluates ``B`` source configurations against one mesh in a single pass,
    which is the workhorse for the position/orientation sweep.

    Parameters
    ----------
    centroids : (M, 3)
    normals : (M, 3)
    positions : (B, 3) source positions [m]
    rotations : (B, 3, 3) antenna-frame -> world rotation matrices
    pattern, t0, n_tilde, radiated_power_w, fresnel : as in :func:`compute_sab`
    body, diffraction_model, fock_R, q_F_h : the Fock shadow gate, as in
        :func:`compute_sab`. With ``diffraction_model="fock"`` and a ``body`` the
        per-pose curvature radius is resolved face by face (shape ``(B, M)``).
    self_shadow, vis_resolution : distal self-shadowing gate, as in
        :func:`compute_sab`. The visibility LUT is pose-independent (baked once for
        ``body``); the per-pose distal factor is applied in a loop over poses,
        using that pose's source -> point direction and position.

    Returns
    -------
    sab : (B, M) absorbed power density [W/m^2]
    """
    centroids = xp.asarray(centroids)
    normals = xp.asarray(normals)
    positions = xp.asarray(positions)
    rotations = xp.asarray(rotations)

    rel = centroids[None, :, :] - positions[:, None, :]  # (B, M, 3)
    dist = xp.sqrt(xp.sum(rel * rel, axis=-1))  # (B, M)
    k_hat = rel / dist[..., None]

    # dir_ant[b, m] = R_b^T k_hat[b, m]
    dir_ant = xp.einsum("bmi,bij->bmj", k_hat, rotations)
    directivity = pattern.sample(dir_ant)  # (B, M)

    s_inc = radiated_power_w * directivity / (4.0 * np.pi * dist * dist)
    mu = xp.sum(normals[None, :, :] * (-k_hat), axis=-1)
    relu_mu = xp.maximum(mu, 0.0)

    if fresnel:
        _, _, t_pow_s, t_pow_p, _, _ = _fresnel_core(relu_mu, n_tilde)
        t_eff = 0.5 * (t_pow_s + t_pow_p)
    else:
        t_eff = t0

    gate = _local_gate(
        mu,
        k_hat,
        dist,
        body=body,
        freq_hz=pattern.freq_hz,
        n_tilde=n_tilde,
        diffraction_model=diffraction_model,
        fock_R=fock_R,
        q_F_h=q_F_h,
    )
    sab = s_inc * t_eff * gate
    if self_shadow and body is not None:
        # k_hat is (B, M, 3); apply the per-pose distal factor in a loop. The LUT
        # is pose-independent, so bake it ONCE here and reuse it across all poses
        # (only the source -> point direction and source position differ per pose).
        from aegis.geometry import visibility

        lut = visibility.get_or_bake(body, vis_resolution, "erf")
        sab_np = np.asarray(sab).copy()
        kh_np = np.asarray(k_hat)
        pos_np = np.asarray(positions)
        for b in range(sab_np.shape[0]):
            sab_np[b] = sab_np[b] * _distal_factor(
                body,
                kh_np[b],
                source_pos=pos_np[b],
                freq_hz=pattern.freq_hz,
                n_tilde=n_tilde,
                diffraction_model=diffraction_model,
                resolution=vis_resolution,
                lut=lut,
            )
        return xp.asarray(sab_np)
    return sab
