"""Sionna RT ray tracer integration.

Converts Sionna RT channel coefficients to AEGIS PropagationPaths.
Uses a dual-polarized isotropic RX probe to capture the full E-field
polarisation state, then scales to absolute V/m using:

    psi = sqrt(8*pi*Z_0*P_T) / lambda * (a_theta * e_theta + a_phi * e_phi)

Requires: pip install aegis[sionna]  (installs sionna-rt>=1.0)
"""

from __future__ import annotations

import numpy as np

from aegis.constants import C_0, Z_0
from aegis.paths import PropagationPaths


def _check_sionna() -> None:
    """Raise ImportError with helpful message if sionna-rt is not installed."""
    try:
        import sionna.rt  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Sionna RT is required for this integration. Install with: pip install aegis[sionna]"
        ) from exc


def _spherical_basis(theta: np.ndarray, phi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Spherical basis vectors e_theta, e_phi at given angles.

    Parameters
    ----------
    theta : (N,) zenith angles in radians
    phi : (N,) azimuth angles in radians

    Returns
    -------
    e_theta : (N, 3) theta basis vectors
    e_phi : (N, 3) phi basis vectors
    """
    ct, st = np.cos(theta), np.sin(theta)
    cp, sp = np.cos(phi), np.sin(phi)
    e_theta = np.column_stack([ct * cp, ct * sp, -st])
    e_phi = np.column_stack([-sp, cp, np.zeros_like(theta)])
    return e_theta, e_phi


def _convert_a_to_psi(
    a_theta: np.ndarray,
    a_phi: np.ndarray,
    theta_r: np.ndarray,
    phi_r: np.ndarray,
    freq_hz: float,
    tx_power_w: float,
) -> np.ndarray:
    """Convert Sionna channel coefficients to AEGIS psi vectors.

    Parameters
    ----------
    a_theta : (N,) complex theta-component of Sionna's channel coefficient
    a_phi : (N,) complex phi-component
    theta_r : (N,) zenith angle of arrival in radians
    phi_r : (N,) azimuth angle of arrival in radians
    freq_hz : carrier frequency in Hz
    tx_power_w : total TX power in watts

    Returns
    -------
    psi : (N, 3) complex polarisation-amplitude vectors in V/m
    """
    lambda_ = C_0 / freq_hz
    scale = np.sqrt(8 * np.pi * Z_0 * tx_power_w) / lambda_

    e_theta, e_phi = _spherical_basis(theta_r, phi_r)

    psi = scale * (a_theta[:, np.newaxis] * e_theta + a_phi[:, np.newaxis] * e_phi)
    return psi.astype(complex)


def _extract_path_viz(paths, valid: np.ndarray) -> list[dict]:
    """Extract path visualization data from Sionna Paths object.

    Parameters
    ----------
    paths : sionna.rt Paths object with vertices, sources, targets, interactions
    valid : (num_rx, num_tx, num_paths) boolean mask

    Returns
    -------
    List of dicts with keys 'vertices' (list of [x,y,z]), 'order' (int), 'length' (float)
    """
    try:
        verts = np.array(paths.vertices)  # (max_depth, num_rx, num_tx, num_paths, 3)
        interactions = np.array(paths.interactions)  # (max_depth, num_rx, num_tx, num_paths)
        # mi.Point3f stores as (3, N), transpose to (N, 3)
        sources = np.array(paths.sources).T  # (num_tx, 3)
        targets = np.array(paths.targets).T  # (num_rx, 3)
    except (AttributeError, TypeError, ValueError, IndexError):
        return []

    max_depth = verts.shape[0]
    path_viz = []

    rx_idx, tx_idx = 0, 0
    src = sources[tx_idx]
    tgt = targets[rx_idx]
    n_paths = valid.shape[-1]

    for p in range(n_paths):
        if not valid[rx_idx, tx_idx, p]:
            continue

        # Build waypoints: TX -> interaction vertices -> RX
        waypoints = [src.tolist()]
        order = 0
        for d in range(max_depth):
            if interactions[d, rx_idx, tx_idx, p] == 0:  # NONE
                break
            waypoints.append(verts[d, rx_idx, tx_idx, p].tolist())
            order += 1
        waypoints.append(tgt.tolist())

        # Compute total path length
        pts = np.array(waypoints)
        segments = np.diff(pts, axis=0)
        length = float(np.sum(np.linalg.norm(segments, axis=1)))

        if length < 1e-6:
            continue

        path_viz.append({"vertices": waypoints, "order": order, "length": length})

    return path_viz


def paths_from_sionna_scene(
    scene,
    tx_positions: np.ndarray,
    rx_position: np.ndarray,
    freq_hz: float,
    max_bounces: int = 5,
    tx_power_dbm: float = 60.0,
    tx_pattern: str = "isotropic",
    return_viz: bool = False,
    los: bool = True,
    specular_reflection: bool = True,
    diffuse_reflection: bool = False,
    refraction: bool = True,
    diffraction: bool = False,
    edge_diffraction: bool = False,
    diffraction_lit_region: bool = True,
    samples_per_src: int = 1_000_000,
    max_num_paths_per_src: int = 1_000_000,
    synthetic_array: bool = True,
    seed: int = 42,
) -> PropagationPaths | tuple[PropagationPaths, list[dict]]:
    """Run Sionna RT and convert results to PropagationPaths.

    Parameters
    ----------
    scene : sionna.rt Scene object (loaded externally)
    tx_positions : (M_ant, 3) transmitter element positions
    rx_position : (3,) body centroid position
    freq_hz : carrier frequency in Hz
    max_bounces : maximum number of ray interactions
    tx_power_dbm : transmit power per element [dBm]
    tx_pattern : TX antenna pattern name
    return_viz : if True, also return path visualization data

    Returns
    -------
    PropagationPaths with k_hat, psi, element_index, delay, is_los.
    If return_viz is True, returns (PropagationPaths, path_viz_list).
    """
    _check_sionna()
    from sionna.rt import PathSolver, PlanarArray

    tx_positions = np.asarray(tx_positions, dtype=np.float64)
    rx_position = np.asarray(rx_position, dtype=np.float64)
    if tx_positions.ndim == 1:
        tx_positions = tx_positions[np.newaxis, :]

    tx_power_w = 10 ** ((tx_power_dbm - 30) / 10)
    n_elements = tx_positions.shape[0]

    # Map common pattern names to Sionna v2 registry names
    _pattern_map = {"isotropic": "iso", "half_wave_dipole": "hw_dipole"}
    sionna_tx_pattern = _pattern_map.get(tx_pattern, tx_pattern)

    # Configure dual-polarized isotropic RX to capture theta/phi field components
    scene.rx_array = PlanarArray(
        num_rows=1,
        num_cols=1,
        pattern="iso",
        polarization="cross",
    )

    # Configure TX array
    scene.tx_array = PlanarArray(
        num_rows=1,
        num_cols=n_elements,
        pattern=sionna_tx_pattern,
        polarization="V",
    )

    # Set TX and RX positions (Sionna v2 API)
    # Remove stale TX/RX from cached scenes before adding new ones
    import contextlib

    from sionna.rt import Receiver, Transmitter

    for name in ("tx", "rx"):
        with contextlib.suppress(ValueError, KeyError):
            scene.remove(name)
    scene.add(Transmitter("tx", position=tx_positions[0].tolist()))
    scene.add(Receiver("rx", position=rx_position.tolist()))

    # Compute paths
    solver = PathSolver()
    paths = solver(
        scene=scene,
        max_depth=max_bounces,
        los=los,
        specular_reflection=specular_reflection,
        diffuse_reflection=diffuse_reflection,
        refraction=refraction,
        diffraction=diffraction,
        edge_diffraction=edge_diffraction,
        diffraction_lit_region=diffraction_lit_region,
        samples_per_src=samples_per_src,
        max_num_paths_per_src=max_num_paths_per_src,
        synthetic_array=synthetic_array,
        seed=seed,
    )

    # Extract path visualization before CIR (vertices are lazily computed)
    valid_raw = np.array(paths.valid)  # (num_rx, num_tx, num_paths)
    path_viz = _extract_path_viz(paths, valid_raw) if return_viz else []

    # Extract data as numpy
    # Sionna v2 cir() shape: a[num_rx, num_rx_ant, num_tx, num_tx_ant, num_paths, num_time_steps]
    # With cross-pol RX: num_rx_ant=2 (pol 0=theta, pol 1=phi)
    # tau shape: (num_rx, num_tx, num_paths)
    a_raw, tau_raw = paths.cir(out_type="numpy")
    a_raw = a_raw[..., 0]  # drop time_steps dim -> (num_rx, num_rx_ant, num_tx, num_tx_ant, num_paths)

    theta_r_raw = np.array(paths.theta_r)  # (num_rx, num_tx, num_paths)
    phi_r_raw = np.array(paths.phi_r)
    valid = valid_raw

    all_k_hat = []
    all_psi = []
    all_element_index = []
    all_delay = []
    all_is_los = []

    rx_idx = 0  # single RX (body centroid)
    tx_idx = 0  # single TX device
    for elem in range(n_elements):
        # Extract per-element data. rx_ant=0 is theta, rx_ant=1 is phi.
        a_theta = a_raw[rx_idx, 0, tx_idx, elem, :]  # (n_paths,) complex
        a_phi = a_raw[rx_idx, 1, tx_idx, elem, :]
        theta_r = theta_r_raw[rx_idx, tx_idx, :]
        phi_r = phi_r_raw[rx_idx, tx_idx, :]
        tau = tau_raw[rx_idx, tx_idx, :]
        mask = valid[rx_idx, tx_idx, :]

        # Filter valid paths
        idx = np.where(mask)[0]
        if len(idx) == 0:
            continue

        a_theta = a_theta[idx]
        a_phi = a_phi[idx]
        theta_r = theta_r[idx]
        phi_r = phi_r[idx]
        tau = tau[idx]

        # Convert to AEGIS psi
        psi = _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, tx_power_w)

        # k_hat from arrival angles (direction of propagation, toward the body)
        # Sionna's (theta_r, phi_r) gives the direction FROM the body TO the source.
        # AEGIS k_hat is the propagation direction (toward the body), so negate.
        k_hat = -np.column_stack(
            [
                np.sin(theta_r) * np.cos(phi_r),
                np.sin(theta_r) * np.sin(phi_r),
                np.cos(theta_r),
            ]
        )

        # Detect LOS paths (first path in each element is typically LOS)
        is_los = np.zeros(len(idx), dtype=bool)
        if len(idx) > 0:
            is_los[0] = True  # Conservative: mark shortest-delay path as LOS

        all_k_hat.append(k_hat)
        all_psi.append(psi)
        all_element_index.append(np.full(len(idx), elem, dtype=np.intp))
        all_delay.append(tau)
        all_is_los.append(is_los)

    if not all_k_hat:
        empty = PropagationPaths.from_powers(k_hat=np.zeros((0, 3)), power=np.zeros(0))
        return (empty, []) if return_viz else empty

    result = PropagationPaths(
        k_hat=np.vstack(all_k_hat),
        psi=np.vstack(all_psi),
        element_index=np.concatenate(all_element_index),
        delay=np.concatenate(all_delay),
        is_los=np.concatenate(all_is_los),
    )
    return (result, path_viz) if return_viz else result
