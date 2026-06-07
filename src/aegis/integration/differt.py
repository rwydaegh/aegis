"""DiffeRT ray tracer integration.

Loads propagation paths from DiffeRT scene output and converts them to
PropagationPaths for use with any AEGIS fidelity level.

Requires: pip install aegis[rt]  (installs differt>=0.7.0)
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path

import numpy as np

from aegis.constants import C_0, Z_0
from aegis.defaults import CONCRETE_EPS_R, CONCRETE_SIGMA, DEFAULT_POWER_DBM
from aegis.paths import PropagationPaths
from aegis.tissue.fresnel import fresnel_reflection, n_complex

logger = logging.getLogger(__name__)


def _check_differt() -> None:
    """Raise ImportError with helpful message if differt is not installed."""
    try:
        import differt  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "DiffeRT is required for ray tracer integration. Install it with: pip install aegis[rt]"
        ) from exc


def _arbitrary_perpendicular(k_hat: np.ndarray) -> np.ndarray:
    """Build an arbitrary unit vector perpendicular to each k_hat row.

    Parameters
    ----------
    k_hat : (N, 3) unit direction vectors

    Returns
    -------
    e_perp : (N, 3) perpendicular unit vectors
    """
    n_paths = k_hat.shape[0]
    ref = np.zeros_like(k_hat)
    abs_k = np.abs(k_hat)
    min_axis = np.argmin(abs_k, axis=1)
    ref[np.arange(n_paths), min_axis] = 1.0
    e_perp = np.cross(k_hat, ref)
    e_perp_norm = np.linalg.norm(e_perp, axis=1, keepdims=True)
    e_perp = e_perp / np.where(e_perp_norm > 0, e_perp_norm, 1.0)
    return e_perp


def _initial_polarisation_vector(k_hat: np.ndarray, pol_type: str) -> np.ndarray:
    """Compute initial polarisation unit vector from propagation direction.

    Parameters
    ----------
    k_hat : (3,) unit propagation direction
    pol_type : "vertical" or "horizontal"

    Returns
    -------
    e_pol : (3,) real unit vector perpendicular to k_hat
    """
    if pol_type == "horizontal":
        e_pol = np.cross(k_hat, np.array([0.0, 0.0, 1.0]))
        e_pol_norm = np.linalg.norm(e_pol)
        if e_pol_norm < 1e-12:
            return np.array([1.0, 0.0, 0.0])
        return e_pol / e_pol_norm

    # Vertical: z-axis projected perpendicular to k
    z = np.array([0.0, 0.0, 1.0])
    e_pol = z - np.dot(z, k_hat) * k_hat
    e_pol_norm = np.linalg.norm(e_pol)
    if e_pol_norm < 1e-12:
        return np.array([1.0, 0.0, 0.0])
    return e_pol / e_pol_norm


def _decompose_te_tm(k_hat: np.ndarray, normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute TE (s) and TM (p) basis vectors for incident field.

    Parameters
    ----------
    k_hat : (3,) unit propagation direction
    normal : (3,) unit surface normal (must face the incident ray)

    Returns
    -------
    e_s : (3,) TE basis vector
    e_p : (3,) TM basis vector (incident side)
    """
    e_s = np.cross(k_hat, normal)
    e_s_norm = np.linalg.norm(e_s)
    # Normal incidence: pick arbitrary perpendicular
    e_s = _arbitrary_perpendicular(k_hat[np.newaxis, :])[0] if e_s_norm < 1e-12 else e_s / e_s_norm

    e_p = np.cross(e_s, k_hat)
    e_p_norm = np.linalg.norm(e_p)
    if e_p_norm > 1e-12:
        e_p = e_p / e_p_norm

    return e_s, e_p


def _reflect_at_surface(
    psi: np.ndarray,
    k_in: np.ndarray,
    k_out: np.ndarray,
    normal: np.ndarray,
    n_tilde: complex,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply Fresnel reflection to polarisation vector at a surface.

    Parameters
    ----------
    psi : (3,) complex polarisation-amplitude vector
    k_in : (3,) unit incident direction
    k_out : (3,) unit reflected direction
    normal : (3,) unit surface normal (orientation-agnostic, flipped internally)
    n_tilde : complex refractive index of the reflecting material

    Returns
    -------
    psi_out : (3,) complex reflected polarisation-amplitude vector
    k_out : (3,) the reflected propagation direction (passed through)
    """
    # Flip normal to face incident ray
    if np.dot(normal, -k_in) < 0:
        normal = -normal

    e_s, e_p_i = _decompose_te_tm(k_in, normal)

    # Decompose psi into TE/TM components
    psi_s = np.dot(psi, e_s)
    psi_p = np.dot(psi, e_p_i)

    # Fresnel reflection coefficients
    cos_theta = abs(np.dot(normal, -k_in))
    r_s, r_p = fresnel_reflection(cos_theta, n_tilde)

    # Reflected TM basis uses shared e_s with reflected direction
    e_p_r = np.cross(e_s, k_out)
    e_p_r_norm = np.linalg.norm(e_p_r)
    if e_p_r_norm > 1e-12:
        e_p_r = e_p_r / e_p_r_norm

    psi_out = r_s * psi_s * e_s + r_p * psi_p * e_p_r
    return psi_out, k_out


def _track_polarisation(
    path_vertices: np.ndarray,
    scene_normals: np.ndarray,
    object_indices: np.ndarray,
    material_indices: np.ndarray | None,
    material_n_tilde: list[complex],
    amplitude: np.ndarray,
    initial_polarisation: str = "vertical",
) -> np.ndarray:
    """Track polarisation state through reflections along each path.

    Decomposes the electric field into TE/TM at each reflection surface,
    applies Fresnel reflection coefficients, and reconstructs the field.

    Parameters
    ----------
    path_vertices : (N_paths, path_length, 3)
        Full path including TX (index 0) and RX (index -1).
    scene_normals : (N_triangles, 3)
        Per-triangle unit normals from the scene mesh.
    object_indices : (N_paths, path_length)
        Triangle index at each path vertex. -1 for TX/RX placeholders.
    material_indices : (N_triangles,) or None
        Per-triangle material index. If None, all surfaces use material 0.
    material_n_tilde : list of complex
        Complex refractive index per material at the operating frequency.
    amplitude : (N_paths,)
        Scalar E-field amplitude from FSPL for each path.
    initial_polarisation : "vertical" or "horizontal"
        TX antenna polarisation. Vertical = z-axis projected perpendicular
        to the initial propagation direction.

    Returns
    -------
    psi : (N_paths, 3) complex
        Polarisation-amplitude vector at arrival to the body.
    """
    n_paths, path_length, _ = path_vertices.shape
    psi = np.zeros((n_paths, 3), dtype=complex)

    for i in range(n_paths):
        seg = path_vertices[i, 1] - path_vertices[i, 0]
        seg_len = np.linalg.norm(seg)
        if seg_len < 1e-12:
            continue
        k = seg / seg_len

        e_pol = _initial_polarisation_vector(k, initial_polarisation)
        psi_vec = amplitude[i] * e_pol.astype(complex)

        for b in range(1, path_length - 1):
            tri_idx = int(object_indices[i, b])
            if tri_idx < 0:
                continue

            seg_next = path_vertices[i, b + 1] - path_vertices[i, b]
            seg_next_len = np.linalg.norm(seg_next)
            if seg_next_len < 1e-12:
                break

            k_out = seg_next / seg_next_len

            # Look up material refractive index
            if material_indices is not None and tri_idx < len(material_indices):
                mat_idx = int(material_indices[tri_idx])
                n_t = material_n_tilde[mat_idx] if 0 <= mat_idx < len(material_n_tilde) else material_n_tilde[0]
            else:
                n_t = material_n_tilde[0] if material_n_tilde else 1.5 + 0j

            psi_vec, k = _reflect_at_surface(psi_vec, k, k_out, scene_normals[tri_idx], n_t)

        psi[i] = psi_vec

    return psi


def paths_from_differt(
    vertices: np.ndarray,
    normals: np.ndarray,
    path_vertices: np.ndarray,
    tx_positions: np.ndarray,
    freq_hz: float,
    tx_power_dbm: float = DEFAULT_POWER_DBM,
    element_indices: np.ndarray | None = None,
    object_indices: np.ndarray | None = None,
    material_indices: np.ndarray | None = None,
    material_n_tilde: list[complex] | None = None,
    initial_polarisation: str = "vertical",
) -> PropagationPaths:
    """Build PropagationPaths from DiffeRT ray tracing output.

    This function takes the raw geometric output from DiffeRT's path solver
    and converts it to AEGIS PropagationPaths. It computes:
    - k_hat from the last path segment direction
    - psi from free-space path loss and Fresnel reflection at interactions
    - element_index from the transmitter array structure

    When object_indices and material_n_tilde are provided, polarisation is
    tracked through each reflection using TE/TM decomposition and Fresnel
    coefficients. Otherwise, an arbitrary perpendicular is used (sufficient
    for incoherent levels 0-6 where only |psi|^2 matters).

    Parameters
    ----------
    vertices : (N_scene, 3) scene triangle vertices (for material lookup)
    normals : (N_scene, 3) scene triangle normals
    path_vertices : (N_paths, N_bounces+2, 3) path vertex positions.
        First vertex is TX, last is the arrival point near the body.
    tx_positions : (M_ant, 3) transmitter antenna element positions
    freq_hz : operating frequency [Hz]
    tx_power_dbm : transmit power per element [dBm], default 43 (20 W)
    element_indices : (N_paths,) which TX element each path originates from.
        If None, inferred from nearest TX position.
    object_indices : (N_paths, path_length) triangle index at each path
        vertex from DiffeRT Paths.objects. -1 for TX/RX placeholders.
    material_indices : (N_triangles,) per-triangle material index from
        DiffeRT mesh.face_materials.
    material_n_tilde : list of complex refractive indices per material at
        the operating frequency. Use fresnel.n_complex() to compute.
    initial_polarisation : "vertical" or "horizontal" TX antenna polarisation.

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

    # For each path, find the last segment with nonzero length (vectorized)
    nonzero_mask = seg_lengths > 1e-12  # (N, n_segments) bool
    # Multiply column index by mask, take argmax to get last nonzero segment
    col_indices = np.arange(segments.shape[1])[np.newaxis, :]  # (1, n_segments)
    # Where no nonzero segment exists, masked_cols stays 0
    masked_cols = np.where(nonzero_mask, col_indices, -1)
    last_seg_idx = np.argmax(masked_cols, axis=1)  # (N,)
    row_idx = np.arange(n_paths)
    last_seg = segments[row_idx, last_seg_idx]  # (N, 3)
    last_len = seg_lengths[row_idx, last_seg_idx]  # (N,)
    safe_len = np.where(last_len > 1e-12, last_len, 1.0)
    k_hat = last_seg / safe_len[:, np.newaxis]
    # Zero out paths with no valid segments
    k_hat[last_len <= 1e-12] = 0.0

    # Total path length (excluding zero-length padding segments)
    total_length = np.sum(seg_lengths, axis=1)  # (N,)

    # Filter out degenerate paths (zero total length means TX=RX coincidence
    # or fully padded geometry). These produce undefined k_hat and spurious
    # amplitude from division by ~0 distance.
    valid = total_length > 1e-10
    if not np.all(valid):
        keep = np.where(valid)[0]
        if len(keep) == 0:
            return PropagationPaths.from_powers(k_hat=np.zeros((0, 3)), power=np.zeros(0))
        path_vertices = path_vertices[keep]
        segments = segments[keep]
        seg_lengths = seg_lengths[keep]
        k_hat = k_hat[keep]
        total_length = total_length[keep]
        n_paths = len(keep)
        row_idx = np.arange(n_paths)
        if object_indices is not None:
            object_indices = np.asarray(object_indices, dtype=np.intp)[keep]
        # NOTE: material_indices and normals are per-scene-triangle, not per-path.
        # They must NOT be filtered by path index -- they are used for lookup
        # by triangle index inside _track_polarisation.
        if element_indices is not None:
            element_indices = np.asarray(element_indices, dtype=np.intp)[keep]

    # TX power in watts
    tx_power_w = 10 ** ((tx_power_dbm - 30) / 10)

    # E-field amplitude at distance d from isotropic radiator:
    # S_inc = P_tx / (4*pi*d^2),  |E| = sqrt(2*Z_0*S_inc)
    # So |E| = sqrt(2*Z_0*P_tx / (4*pi)) / d
    d_safe = np.maximum(total_length, 1e-10)
    amplitude = np.sqrt(2 * Z_0 * tx_power_w / (4 * np.pi)) / d_safe

    # Build polarisation vector
    if object_indices is not None and material_n_tilde is not None:
        # Track polarisation through reflections using TE/TM decomposition
        normals = np.asarray(normals, dtype=np.float64)
        object_indices = np.asarray(object_indices, dtype=np.intp)
        mat_idx = np.asarray(material_indices, dtype=np.intp) if material_indices is not None else None
        psi = _track_polarisation(
            path_vertices,
            normals,
            object_indices,
            mat_idx,
            material_n_tilde,
            amplitude,
            initial_polarisation,
        )
        polarised = True
    else:
        # Fallback: arbitrary perpendicular (sufficient for incoherent levels)
        e_perp = _arbitrary_perpendicular(k_hat)
        psi = (amplitude[:, np.newaxis] * e_perp).astype(complex)
        polarised = False

    # Element indices
    if element_indices is None:
        # Assign each path to nearest TX element
        tx_first = path_vertices[:, 0, :]  # (N, 3)
        dists = np.linalg.norm(tx_first[:, np.newaxis, :] - tx_positions[np.newaxis, :, :], axis=2)  # (N, M_ant)
        element_indices = np.argmin(dists, axis=1)
    element_indices = np.asarray(element_indices, dtype=np.intp)

    # Propagation delay and phase
    delay = total_length / C_0

    # Apply propagation phase exp(-j*k*d) for coherent levels (7-8).
    # For incoherent levels only |psi|^2 is used, so phase does not matter,
    # but coherent combination requires correct path-length-dependent phase.
    k0 = 2 * np.pi * freq_hz / C_0
    psi = psi * np.exp(-1j * k0 * total_length)[:, np.newaxis]

    # LOS: one non-degenerate segment (handles max-length padding / repeated RX verts)
    n_nonzero_segs = np.sum(seg_lengths > 1e-12, axis=1)
    is_los = n_nonzero_segs == 1

    return PropagationPaths(
        k_hat=k_hat,
        psi=psi,
        element_index=element_indices,
        delay=delay,
        is_los=is_los,
        polarised=polarised,
    )


def _compute_element_paths(
    scene,
    tx_element_idx: int,
    tx_positions: np.ndarray,
    rx_pos,
    max_bounces: int,
) -> tuple[list[np.ndarray], list[np.ndarray], list[np.ndarray]]:
    """Compute paths for a single TX element across all bounce orders.

    Returns lists of (path_vertices, object_indices, element_indices) arrays
    that can be concatenated later.
    """
    import equinox as eqx
    import jax.numpy as jnp

    tx_pos = jnp.array(tx_positions[tx_element_idx])
    rx_jnp = jnp.array(rx_pos)

    scene_elem = eqx.tree_at(lambda s: s.transmitters, scene, tx_pos[np.newaxis, :])
    scene_elem = eqx.tree_at(lambda s: s.receivers, scene_elem, rx_jnp[np.newaxis, :])

    path_verts_list: list[np.ndarray] = []
    obj_idx_list: list[np.ndarray] = []
    elem_idx_list: list[np.ndarray] = []

    for n_bounces in range(max_bounces + 1):
        try:
            paths = scene_elem.compute_paths(order=n_bounces)

            if not hasattr(paths, "vertices"):
                continue

            verts = np.asarray(paths.vertices)
            objs = np.asarray(paths.objects)
            mask = np.asarray(paths.mask) if paths.mask is not None else None

            # Flatten batch dimensions -> (candidates, path_len, 3)
            path_len = verts.shape[-2]
            verts = verts.reshape(-1, path_len, 3)
            objs = objs.reshape(-1, path_len)
            if mask is not None:
                mask = mask.reshape(-1)

            valid = np.all(np.isfinite(verts), axis=(1, 2))
            if mask is not None:
                valid = valid & mask.astype(bool)

            if np.any(valid):
                verts = verts[valid]
                objs = objs[valid]
                n = verts.shape[0]
                path_verts_list.append(verts)
                obj_idx_list.append(objs)
                elem_idx_list.append(np.full(n, tx_element_idx, dtype=np.intp))

        except Exception as e:
            logger.warning("Bounce order %d failed, skipping: %s", n_bounces, e)
            continue

    return path_verts_list, obj_idx_list, elem_idx_list


def _pad_and_concatenate(
    path_arrays: list[np.ndarray],
    obj_arrays: list[np.ndarray],
    elem_arrays: list[np.ndarray],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Pad variable-length path arrays to the same length and concatenate.

    Parameters
    ----------
    path_arrays : list of (N_i, L_i, 3) path vertex arrays
    obj_arrays : list of (N_i, L_i) object index arrays
    elem_arrays : list of (N_i,) element index arrays

    Returns
    -------
    path_vertices : (N_total, L_max, 3)
    object_indices : (N_total, L_max)
    element_indices : (N_total,)
    """
    max_verts = max(pv.shape[1] for pv in path_arrays)
    padded_verts = []
    padded_objs = []
    for pv, po in zip(path_arrays, obj_arrays, strict=True):
        if pv.shape[1] < max_verts:
            pad_v = ((0, 0), (0, max_verts - pv.shape[1]), (0, 0))
            pv = np.pad(pv, pad_v, mode="edge")
            pad_o = ((0, 0), (0, max_verts - po.shape[1]))
            po = np.pad(po, pad_o, constant_values=-1)
        padded_verts.append(pv)
        padded_objs.append(po)

    return (
        np.concatenate(padded_verts, axis=0),
        np.concatenate(padded_objs, axis=0),
        np.concatenate(elem_arrays, axis=0),
    )


def paths_from_differt_scene(
    scene_path: str | Path,
    tx_positions: np.ndarray,
    rx_position: np.ndarray,
    freq_hz: float,
    max_bounces: int = 3,
    tx_power_dbm: float = DEFAULT_POWER_DBM,
    initial_polarisation: str = "vertical",
) -> PropagationPaths:
    """Run DiffeRT on a scene file and return PropagationPaths.

    This is the high-level entry point. It loads a scene, runs ray tracing
    via scene.compute_paths(), and returns paths with proper TE/TM
    polarisation tracking through reflections.

    Parameters
    ----------
    scene_path : path to Sionna/Mitsuba XML scene file
    tx_positions : (M_ant, 3) transmitter element positions [m]
    rx_position : (3,) receiver (body) position [m]
    freq_hz : operating frequency [Hz]
    max_bounces : maximum number of reflections (default 3)
    tx_power_dbm : transmit power per element [dBm]
    initial_polarisation : "vertical" or "horizontal" TX antenna polarisation

    Returns
    -------
    PropagationPaths
    """
    _check_differt()
    from differt.scene import TriangleScene

    scene = TriangleScene.load_xml(str(scene_path))
    return paths_from_differt_scene_obj(
        scene,
        tx_positions=tx_positions,
        rx_position=rx_position,
        freq_hz=freq_hz,
        max_bounces=max_bounces,
        tx_power_dbm=tx_power_dbm,
        initial_polarisation=initial_polarisation,
    )


def paths_from_differt_scene_obj(
    scene,
    tx_positions: np.ndarray,
    rx_position: np.ndarray,
    freq_hz: float,
    max_bounces: int = 3,
    tx_power_dbm: float = DEFAULT_POWER_DBM,
    initial_polarisation: str = "vertical",
) -> PropagationPaths:
    """Ray trace an in-memory DiffeRT ``TriangleScene`` and return PropagationPaths.

    Same as :func:`paths_from_differt_scene` but takes an already-loaded scene
    object instead of an XML path. Use this for AEGIS-native meshes via
    ``EnvironmentMesh.to_differt_scene()``: the ``to_sionna_xml`` export targets
    Sionna's lenient Mitsuba loader and is not accepted by ``differt_core``'s
    stricter parser, and building the scene once avoids re-parsing per call.

    Parameters
    ----------
    scene : differt.scene.TriangleScene with face_materials and material_names
    tx_positions : (M_ant, 3) transmitter element positions [m]
    rx_position : (3,) receiver (body) position [m]
    freq_hz : operating frequency [Hz]
    max_bounces : maximum number of reflections (default 3)
    tx_power_dbm : transmit power per element [dBm]
    initial_polarisation : "vertical" or "horizontal" TX antenna polarisation

    Returns
    -------
    PropagationPaths
    """
    _check_differt()

    scene_vertices = np.asarray(scene.mesh.vertices)
    scene_normals = np.asarray(scene.mesh.normals)
    material_n_tilde = _extract_material_properties(scene, freq_hz)

    face_materials = None
    if scene.mesh.face_materials is not None:
        face_materials = np.asarray(scene.mesh.face_materials, dtype=np.intp)

    tx_positions = np.asarray(tx_positions, dtype=np.float64)
    rx_position = np.asarray(rx_position, dtype=np.float64)
    if tx_positions.ndim == 1:
        tx_positions = tx_positions[np.newaxis, :]

    all_pv: list[np.ndarray] = []
    all_oi: list[np.ndarray] = []
    all_ei: list[np.ndarray] = []

    for elem_idx in range(len(tx_positions)):
        pv, oi, ei = _compute_element_paths(scene, elem_idx, tx_positions, rx_position, max_bounces)
        all_pv.extend(pv)
        all_oi.extend(oi)
        all_ei.extend(ei)

    if not all_pv:
        return PropagationPaths.from_powers(k_hat=np.zeros((0, 3)), power=np.zeros(0))

    path_vertices, object_indices, element_indices = _pad_and_concatenate(all_pv, all_oi, all_ei)

    return paths_from_differt(
        vertices=scene_vertices,
        normals=scene_normals,
        path_vertices=path_vertices,
        tx_positions=tx_positions,
        freq_hz=freq_hz,
        tx_power_dbm=tx_power_dbm,
        element_indices=element_indices,
        object_indices=object_indices,
        material_indices=face_materials,
        material_n_tilde=material_n_tilde,
        initial_polarisation=initial_polarisation,
    )


def _extract_material_properties(scene, freq_hz: float) -> list[complex]:
    """Extract complex refractive index per material from a DiffeRT scene.

    Falls back to concrete (eps_r=5.31, sigma=0.0326 at 28 GHz) if
    material lookup fails.
    """
    material_names = scene.mesh.material_names if hasattr(scene.mesh, "material_names") else ()

    if not material_names:
        # No materials defined, use concrete as default
        return [n_complex(CONCRETE_EPS_R, CONCRETE_SIGMA, freq_hz)]

    try:
        from differt.em import materials as differt_materials
    except ImportError:
        # Older DiffeRT without material database
        return [n_complex(CONCRETE_EPS_R, CONCRETE_SIGMA, freq_hz) for _ in material_names]

    result = []
    for name in material_names:
        try:
            mat = differt_materials[name]
            eps_r = float(mat.relative_permittivity(freq_hz))
            sigma = float(mat.conductivity(freq_hz))
            result.append(n_complex(eps_r, sigma, freq_hz))
        except (KeyError, AttributeError):
            warnings.warn(
                f"Material '{name}' not found in DiffeRT database, using concrete",
                stacklevel=2,
            )
            result.append(n_complex(CONCRETE_EPS_R, CONCRETE_SIGMA, freq_hz))

    return result
