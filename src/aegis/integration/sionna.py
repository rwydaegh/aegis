"""Sionna RT ray tracer integration.

Converts Sionna RT channel coefficients to AEGIS PropagationPaths.
Uses a dual-polarized isotropic RX probe to capture the full E-field
polarisation state, then scales to absolute V/m using:

    psi = sqrt(8*pi*Z_0*P_T) / lambda * (a_theta * e_theta + a_phi * e_phi)

Requires: pip install aegis[sionna]  (installs sionna-rt>=1.0)
"""

from __future__ import annotations

import logging

import numpy as np

from aegis._array_backend import JAX_AVAILABLE
from aegis.constants import C_0, Z_0
from aegis.defaults import DEFAULT_POWER_DBM, DEFAULT_SEED
from aegis.paths import PropagationPaths

logger = logging.getLogger(__name__)


def _is_jax_array(arr) -> bool:
    """Return True if *arr* is a JAX array."""
    if not JAX_AVAILABLE:
        return False
    import jax

    return isinstance(arr, jax.Array)


def _check_sionna() -> None:
    """Raise ImportError with helpful message if sionna-rt is not installed."""
    try:
        import sionna.rt  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "Sionna RT is required for this integration. Install with: pip install aegis[sionna]"
        ) from exc


def _spherical_basis(theta, phi):
    """Spherical basis vectors e_theta, e_phi at given angles.

    Works with both NumPy and JAX arrays. Detects backend from input type.

    Parameters
    ----------
    theta : (N,) zenith angles in radians
    phi : (N,) azimuth angles in radians

    Returns
    -------
    e_theta : (N, 3) theta basis vectors
    e_phi : (N, 3) phi basis vectors
    """
    if _is_jax_array(theta):
        import jax.numpy as jnp

        _xp = jnp
    else:
        _xp = np

    ct, st = _xp.cos(theta), _xp.sin(theta)
    cp, sp = _xp.cos(phi), _xp.sin(phi)
    e_theta = _xp.column_stack([ct * cp, ct * sp, -st])
    e_phi = _xp.column_stack([-sp, cp, _xp.zeros_like(theta)])
    return e_theta, e_phi


def _convert_a_to_psi(a_theta, a_phi, theta_r, phi_r, freq_hz, tx_power_w):
    """Convert Sionna channel coefficients to AEGIS psi vectors.

    Works with both NumPy and JAX arrays.

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
    if _is_jax_array(a_theta):
        import jax.numpy as jnp

        _xp = jnp
    else:
        _xp = np

    lambda_ = C_0 / freq_hz
    scale = _xp.sqrt(8 * _xp.pi * Z_0 * tx_power_w) / lambda_

    e_theta, e_phi = _spherical_basis(theta_r, phi_r)

    psi = scale * (a_theta[:, None] * e_theta + a_phi[:, None] * e_phi)
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


def _paths_from_sionna_jax(paths, valid_np, n_elements, freq_hz, tx_power_w):
    """JAX-preserving extraction from Sionna Paths object.

    Uses ``paths.cir(out_type="jax")`` to get JAX arrays with Dr.Jit
    gradient tracking via ``dr.wrap()``.  Invalid paths are masked to
    zero (static shapes) rather than filtered.

    Parameters
    ----------
    paths : sionna.rt Paths object (from PathSolver)
    valid_np : (num_rx, num_tx, num_paths) bool mask (NumPy)
    n_elements : number of TX antenna elements
    freq_hz : carrier frequency [Hz]
    tx_power_w : TX power per element [W]

    Returns
    -------
    PropagationPaths with JAX arrays
    """
    import jax.numpy as jnp

    # Get CIR as JAX arrays (gradient-tracked via dr.wrap)
    a_raw, tau_raw = paths.cir(out_type="jax")
    a_raw = a_raw[..., 0]  # drop time_steps -> (num_rx, num_rx_ant, num_tx, num_tx_ant, num_paths)

    # Angles as JAX arrays
    theta_r_raw = jnp.asarray(paths.theta_r)  # (num_rx, num_tx, num_paths)
    phi_r_raw = jnp.asarray(paths.phi_r)

    rx_idx, tx_idx = 0, 0
    n_paths_per_elem = a_raw.shape[-1]

    # Flatten across all elements: (n_elements * n_paths_per_elem,)
    a_theta_all = a_raw[rx_idx, 0, tx_idx, :, :].reshape(-1)  # (M*N,)
    a_phi_all = a_raw[rx_idx, 1, tx_idx, :, :].reshape(-1)  # (M*N,)

    # Angles are shared across elements (synthetic array), tile them
    theta_r = jnp.tile(theta_r_raw[rx_idx, tx_idx, :], n_elements)  # (M*N,)
    phi_r = jnp.tile(phi_r_raw[rx_idx, tx_idx, :], n_elements)

    # Delays (metadata, not gradient-tracked)
    tau_all = jnp.tile(jnp.asarray(tau_raw[rx_idx, tx_idx, :]), n_elements)

    # Valid mask: tile across elements
    valid_elem = jnp.asarray(valid_np[rx_idx, tx_idx, :])  # (N,)
    valid_all = jnp.tile(valid_elem, n_elements)  # (M*N,)
    valid_f = valid_all.astype(jnp.float64)  # 1.0 or 0.0

    # Convert to psi (JAX path, gradient flows through)
    psi = _convert_a_to_psi(a_theta_all, a_phi_all, theta_r, phi_r, freq_hz, tx_power_w)
    psi = psi * valid_f[:, None]  # zero invalid paths

    # k_hat from arrival angles (negate: Sionna body->source, AEGIS source->body)
    st, ct = jnp.sin(theta_r), jnp.cos(theta_r)
    sp, cp = jnp.sin(phi_r), jnp.cos(phi_r)
    k_hat_raw = -jnp.column_stack([st * cp, st * sp, ct])
    # Safe default for invalid paths: [0, 0, -1] instead of zero vector
    default_k = jnp.array([0.0, 0.0, -1.0])
    k_hat = jnp.where(valid_all[:, None], k_hat_raw, default_k[None, :])

    # Element indices: [0,0,...,0, 1,1,...,1, ..., M-1,...,M-1]
    element_index = jnp.repeat(jnp.arange(n_elements, dtype=jnp.int32), n_paths_per_elem)

    # LOS: shortest delay per element (metadata, not in gradient path)
    tau_per_elem = tau_all.reshape(n_elements, n_paths_per_elem)
    # Set invalid paths to large tau so they never win argmin
    large_tau = jnp.finfo(jnp.float64).max
    valid_2d = jnp.broadcast_to(valid_elem[None, :], tau_per_elem.shape)
    tau_masked = jnp.where(valid_2d, tau_per_elem, large_tau)
    min_idx = jnp.argmin(tau_masked, axis=1)  # (M,)
    is_los_2d = jnp.zeros((n_elements, n_paths_per_elem), dtype=bool)
    is_los_2d = is_los_2d.at[jnp.arange(n_elements), min_idx].set(True)
    # Only mark as LOS if the element has any valid paths
    has_valid = jnp.any(valid_elem)  # shared across elements for synthetic array
    is_los = (is_los_2d & has_valid).reshape(-1)

    return PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=element_index,
        delay=tau_all,
        is_los=is_los,
        polarised=True,
    )


def paths_from_sionna_scene(
    scene,
    tx_positions: np.ndarray,
    rx_position: np.ndarray,
    freq_hz: float,
    max_bounces: int = 5,
    tx_power_dbm: float = DEFAULT_POWER_DBM,
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
    seed: int = DEFAULT_SEED,
    differentiable: bool = False,
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
    differentiable : if True, return JAX arrays with Dr.Jit gradient
        tracking via ``paths.cir(out_type="jax")``. Requires JAX.
        Invalid paths are masked to zero (static shapes) instead of
        filtered, enabling ``jax.grad`` through the conversion.

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

    # Set the carrier on the scene before building arrays or solving. Sionna
    # defaults a loaded scene to 3.5 GHz, and the frequency drives the radio
    # material coefficients, the synthetic-array element spacing (lambda/2), and
    # the path-loss wavelength. Leaving the default silently traces the wrong
    # band (at 28 GHz the field power is ~5000x lower than at 3.5 GHz).
    scene.frequency = float(freq_hz)

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

    # Validate synthetic_array assumption: both the JAX and NumPy paths
    # index angles/delays as (num_rx, 1, num_paths) and CIR coefficients
    # as (num_rx, 2, 1, n_elements, num_paths, 1). With synthetic_array=False,
    # Sionna moves elements into the num_tx axis instead of num_tx_ant,
    # producing (num_rx, n_elements, num_paths) angles and
    # (num_rx, 2, n_elements, 1, num_paths, 1) CIR, which silently gives
    # wrong results or crashes on multi-element arrays.
    if not synthetic_array and n_elements > 1:
        raise NotImplementedError(
            "synthetic_array=False with multiple TX elements is not supported. "
            "The AEGIS Sionna bridge assumes synthetic_array=True for "
            "multi-element arrays (shared angles/delays across elements). "
            "Use synthetic_array=True (default) or a single TX element."
        )

    # --- Differentiable JAX path ---
    if differentiable:
        if not JAX_AVAILABLE:
            raise RuntimeError("differentiable=True requires JAX. Install with: pip install jax")
        result = _paths_from_sionna_jax(paths, valid_raw, n_elements, freq_hz, tx_power_w)
        return (result, path_viz) if return_viz else result

    # --- Original NumPy path (unchanged) ---
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

        # Detect LOS: shortest-delay path per element (lowest tau = closest to LOS)
        is_los = np.zeros(len(idx), dtype=bool)
        if len(idx) > 0:
            is_los[np.argmin(tau)] = True

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
        polarised=True,
    )
    return (result, path_viz) if return_viz else result
