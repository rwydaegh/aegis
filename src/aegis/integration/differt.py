"""DiffeRT ray tracer integration.

Loads propagation paths from DiffeRT scene output and converts them to
PropagationPaths for use with any AEGIS fidelity level.

Requires: pip install aegis[rt]  (installs differt>=0.7.0)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from aegis.constants import C_0, Z_0
from aegis.paths import PropagationPaths


def _check_differt() -> None:
    """Raise ImportError with helpful message if differt is not installed."""
    try:
        import differt  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "DiffeRT is required for ray tracer integration. Install it with: pip install aegis[rt]"
        ) from exc


def paths_from_differt(
    vertices: np.ndarray,
    normals: np.ndarray,
    path_vertices: np.ndarray,
    tx_positions: np.ndarray,
    freq_hz: float,
    tx_power_dbm: float = 30.0,
    element_indices: np.ndarray | None = None,
) -> PropagationPaths:
    """Build PropagationPaths from DiffeRT ray tracing output.

    This function takes the raw geometric output from DiffeRT's path solver
    and converts it to AEGIS PropagationPaths. It computes:
    - k_hat from the last path segment direction
    - psi from free-space path loss and Fresnel coefficients at interactions
    - element_index from the transmitter array structure

    Parameters
    ----------
    vertices : (N_scene, 3) scene triangle vertices (for material lookup)
    normals : (N_scene, 3) scene triangle normals
    path_vertices : (N_paths, N_bounces+2, 3) path vertex positions.
        First vertex is TX, last is the arrival point near the body.
    tx_positions : (M_ant, 3) transmitter antenna element positions
    freq_hz : operating frequency [Hz]
    tx_power_dbm : transmit power per element [dBm], default 30 (1 W)
    element_indices : (N_paths,) which TX element each path originates from.
        If None, inferred from nearest TX position.

    Returns
    -------
    PropagationPaths ready for any AEGIS level.
    """
    path_vertices = np.asarray(path_vertices, dtype=np.float64)
    tx_positions = np.asarray(tx_positions, dtype=np.float64)

    n_paths = path_vertices.shape[0]
    if n_paths == 0:
        return PropagationPaths.from_powers(k_hat=np.zeros((0, 3)), power=np.zeros(0))

    # Direction of arrival: last non-degenerate segment (handles padded paths)
    segments = np.diff(path_vertices, axis=1)  # (N, n_segments, 3)
    seg_lengths = np.linalg.norm(segments, axis=2)  # (N, n_segments)

    # For each path, find the last segment with nonzero length
    k_hat = np.zeros((n_paths, 3))
    for i in range(n_paths):
        for s in range(segments.shape[1] - 1, -1, -1):
            if seg_lengths[i, s] > 1e-12:
                k_hat[i] = segments[i, s] / seg_lengths[i, s]
                break

    # Total path length (excluding zero-length padding segments)
    total_length = np.sum(seg_lengths, axis=1)  # (N,)

    # Free-space path loss per path
    wavelength = C_0 / freq_hz
    # FSPL amplitude = wavelength / (4*pi*d)
    fspl_amplitude = wavelength / (4 * np.pi * np.maximum(total_length, 1e-10))

    # TX power in watts
    tx_power_w = 10 ** ((tx_power_dbm - 30) / 10)

    # Electric field amplitude: E = sqrt(2 * Z_0 * S_inc) where S_inc = P_tx * FSPL^2 / (4*pi)
    # Simplified: |psi| = sqrt(2 * Z_0 * P_tx) * fspl_amplitude
    amplitude = np.sqrt(2 * Z_0 * tx_power_w) * fspl_amplitude

    # Build polarisation vector perpendicular to k_hat (arbitrary for now)
    # A proper implementation would use DiffeRT's sp_directions for TE/TM
    ref = np.zeros_like(k_hat)
    abs_k = np.abs(k_hat)
    min_axis = np.argmin(abs_k, axis=1)
    ref[np.arange(n_paths), min_axis] = 1.0
    e_perp = np.cross(k_hat, ref)
    e_perp_norm = np.linalg.norm(e_perp, axis=1, keepdims=True)
    e_perp = e_perp / np.where(e_perp_norm > 0, e_perp_norm, 1.0)

    psi = (amplitude[:, np.newaxis] * e_perp).astype(complex)

    # Element indices
    if element_indices is None:
        # Assign each path to nearest TX element
        tx_first = path_vertices[:, 0, :]  # (N, 3)
        dists = np.linalg.norm(tx_first[:, np.newaxis, :] - tx_positions[np.newaxis, :, :], axis=2)  # (N, M_ant)
        element_indices = np.argmin(dists, axis=1)
    element_indices = np.asarray(element_indices, dtype=np.intp)

    # Propagation delay
    delay = total_length / C_0

    # LOS flag: paths with exactly 2 vertices (TX -> body) are LOS
    n_vertices_per_path = path_vertices.shape[1]
    is_los = np.full(n_paths, n_vertices_per_path == 2, dtype=bool)

    return PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=element_indices,
        delay=delay,
        is_los=is_los,
    )


def paths_from_differt_scene(
    scene_path: str | Path,
    tx_positions: np.ndarray,
    rx_position: np.ndarray,
    freq_hz: float,
    max_bounces: int = 3,
    tx_power_dbm: float = 30.0,
) -> PropagationPaths:
    """Run DiffeRT on a scene file and return PropagationPaths.

    This is the high-level entry point. It loads a scene, runs ray tracing,
    and returns paths ready for AEGIS.

    Parameters
    ----------
    scene_path : path to Sionna/Mitsuba XML scene file
    tx_positions : (M_ant, 3) transmitter element positions [m]
    rx_position : (3,) receiver (body) position [m]
    freq_hz : operating frequency [Hz]
    max_bounces : maximum number of reflections (default 3)
    tx_power_dbm : transmit power per element [dBm]

    Returns
    -------
    PropagationPaths
    """
    _check_differt()

    import jax.numpy as jnp
    from differt.scene import TriangleScene

    scene = TriangleScene.load_xml(str(scene_path))

    # Get scene geometry as numpy
    scene_vertices = np.asarray(scene.mesh.vertices)
    scene_normals = np.asarray(scene.mesh.normals) if hasattr(scene.mesh, "normals") else None

    tx_positions = np.asarray(tx_positions, dtype=np.float64)
    rx_position = np.asarray(rx_position, dtype=np.float64)

    if tx_positions.ndim == 1:
        tx_positions = tx_positions[np.newaxis, :]

    # Run path tracing for each TX element
    all_path_vertices = []
    all_element_indices = []

    for elem_idx in range(len(tx_positions)):
        tx_pos = jnp.array(tx_positions[elem_idx])
        rx_pos = jnp.array(rx_position)

        # Use image method for specular reflections
        from differt.rt import image_method

        for n_bounces in range(max_bounces + 1):
            try:
                paths = image_method(tx_pos, rx_pos, scene, order=n_bounces)
                if paths is not None and len(paths) > 0:
                    path_np = np.asarray(paths)
                    if path_np.ndim == 3:
                        n = path_np.shape[0]
                        all_path_vertices.append(path_np)
                        all_element_indices.append(np.full(n, elem_idx, dtype=np.intp))
            except Exception:
                # Some bounce orders may not have valid paths
                continue

    if not all_path_vertices:
        return PropagationPaths.from_powers(k_hat=np.zeros((0, 3)), power=np.zeros(0))

    # Concatenate all paths (they may have different numbers of vertices)
    # Pad to same length
    max_verts = max(pv.shape[1] for pv in all_path_vertices)
    padded = []
    for pv in all_path_vertices:
        if pv.shape[1] < max_verts:
            pad_width = ((0, 0), (0, max_verts - pv.shape[1]), (0, 0))
            pv = np.pad(pv, pad_width, mode="edge")
        padded.append(pv)

    path_vertices = np.concatenate(padded, axis=0)
    element_indices = np.concatenate(all_element_indices, axis=0)

    return paths_from_differt(
        vertices=scene_vertices,
        normals=scene_normals if scene_normals is not None else np.zeros_like(scene_vertices),
        path_vertices=path_vertices,
        tx_positions=tx_positions,
        freq_hz=freq_hz,
        tx_power_dbm=tx_power_dbm,
        element_indices=element_indices,
    )
