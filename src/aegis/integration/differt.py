"""DiffeRT ray tracer integration.

Loads propagation paths from DiffeRT scene output and converts them to
PropagationPaths for use with any AEGIS fidelity level.

Requires: pip install aegis[rt]  (installs differt>=0.7.0)
"""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

from aegis.constants import C_0, Z_0
from aegis.paths import PropagationPaths
from aegis.tissue.fresnel import fresnel_reflection, n_complex


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
        # Initial propagation direction: TX -> first interaction (or RX for LOS)
        seg = path_vertices[i, 1] - path_vertices[i, 0]
        seg_len = np.linalg.norm(seg)
        if seg_len < 1e-12:
            continue
        k = seg / seg_len

        # Initial polarisation
        if initial_polarisation == "horizontal":
            # Horizontal: perpendicular to k and z, in the horizontal plane
            e_pol = np.cross(k, np.array([0.0, 0.0, 1.0]))
            e_pol_norm = np.linalg.norm(e_pol)
            e_pol = np.array([1.0, 0.0, 0.0]) if e_pol_norm < 1e-12 else e_pol / e_pol_norm
        else:
            # Vertical: z-axis projected perpendicular to k
            z = np.array([0.0, 0.0, 1.0])
            e_pol = z - np.dot(z, k) * k
            e_pol_norm = np.linalg.norm(e_pol)
            e_pol = np.array([1.0, 0.0, 0.0]) if e_pol_norm < 1e-12 else e_pol / e_pol_norm

        psi_vec = amplitude[i] * e_pol.astype(complex)

        # Walk through intermediate vertices (reflections)
        for b in range(1, path_length - 1):
            tri_idx = int(object_indices[i, b])
            if tri_idx < 0:
                # Padding or TX/RX placeholder, skip
                continue

            # Check for degenerate segment (padded path)
            seg_next = path_vertices[i, b + 1] - path_vertices[i, b]
            seg_next_len = np.linalg.norm(seg_next)
            if seg_next_len < 1e-12:
                break

            # Incident and reflected directions
            k_i = k  # current propagation direction
            k_r = seg_next / seg_next_len

            # Surface normal
            normal = scene_normals[tri_idx]
            # Ensure normal points toward the incident ray
            if np.dot(normal, -k_i) < 0:
                normal = -normal

            # TE basis: e_s = normalize(k_i x normal)
            e_s = np.cross(k_i, normal)
            e_s_norm = np.linalg.norm(e_s)
            if e_s_norm < 1e-12:
                # Normal incidence: k parallel to normal
                # TE/TM decomposition is degenerate, pick arbitrary basis
                e_s = _arbitrary_perpendicular(k_i[np.newaxis, :])[0]
                e_s_norm = 1.0
            else:
                e_s = e_s / e_s_norm

            # TM basis (incident): e_p_i = e_s x k_i
            e_p_i = np.cross(e_s, k_i)
            e_p_i_norm = np.linalg.norm(e_p_i)
            if e_p_i_norm > 1e-12:
                e_p_i = e_p_i / e_p_i_norm

            # Decompose psi into TE/TM
            psi_s = np.dot(psi_vec, e_s)
            psi_p = np.dot(psi_vec, e_p_i)

            # Material refractive index
            if material_indices is not None and tri_idx < len(material_indices):
                mat_idx = int(material_indices[tri_idx])
                n_t = material_n_tilde[mat_idx] if 0 <= mat_idx < len(material_n_tilde) else material_n_tilde[0]
            else:
                n_t = material_n_tilde[0] if material_n_tilde else 1.5 + 0j

            # Fresnel reflection coefficients
            cos_theta = abs(np.dot(normal, -k_i))
            r_s, r_p = fresnel_reflection(cos_theta, n_t)

            # Reflected TE basis is the same (e_r_s = e_s)
            # Reflected TM basis: e_p_r = e_s x k_r
            e_p_r = np.cross(e_s, k_r)
            e_p_r_norm = np.linalg.norm(e_p_r)
            if e_p_r_norm > 1e-12:
                e_p_r = e_p_r / e_p_r_norm

            # Reconstruct reflected psi
            psi_vec = r_s * psi_s * e_s + r_p * psi_p * e_p_r

            # Update propagation direction
            k = k_r

        psi[i] = psi_vec

    return psi


def paths_from_differt(
    vertices: np.ndarray,
    normals: np.ndarray,
    path_vertices: np.ndarray,
    tx_positions: np.ndarray,
    freq_hz: float,
    tx_power_dbm: float = 30.0,
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
    tx_power_dbm : transmit power per element [dBm], default 30 (1 W)
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

    # For each path, find the last segment with nonzero length
    k_hat = np.zeros((n_paths, 3))
    for i in range(n_paths):
        for s in range(segments.shape[1] - 1, -1, -1):
            if seg_lengths[i, s] > 1e-12:
                k_hat[i] = segments[i, s] / seg_lengths[i, s]
                break

    # Total path length (excluding zero-length padding segments)
    total_length = np.sum(seg_lengths, axis=1)  # (N,)

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
    else:
        # Fallback: arbitrary perpendicular (sufficient for incoherent levels)
        e_perp = _arbitrary_perpendicular(k_hat)
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

    import equinox as eqx
    import jax.numpy as jnp
    from differt.scene import TriangleScene

    scene = TriangleScene.load_xml(str(scene_path))

    # Get scene geometry as numpy
    scene_vertices = np.asarray(scene.mesh.vertices)
    scene_normals = np.asarray(scene.mesh.normals)

    # Extract material EM properties at operating frequency
    material_n_tilde = _extract_material_properties(scene, freq_hz)

    # Per-triangle material index
    face_materials = None
    if scene.mesh.face_materials is not None:
        face_materials = np.asarray(scene.mesh.face_materials, dtype=np.intp)

    tx_positions = np.asarray(tx_positions, dtype=np.float64)
    rx_position = np.asarray(rx_position, dtype=np.float64)

    if tx_positions.ndim == 1:
        tx_positions = tx_positions[np.newaxis, :]

    # Run path tracing for each TX element using compute_paths
    all_path_vertices = []
    all_element_indices = []
    all_object_indices = []

    for elem_idx in range(len(tx_positions)):
        tx_pos = jnp.array(tx_positions[elem_idx])
        rx_pos = jnp.array(rx_position)

        # Set TX/RX on the scene
        scene_elem = eqx.tree_at(
            lambda s: s.transmitters,
            scene,
            tx_pos[np.newaxis, :],
        )
        scene_elem = eqx.tree_at(
            lambda s: s.receivers,
            scene_elem,
            rx_pos[np.newaxis, :],
        )

        for n_bounces in range(max_bounces + 1):
            try:
                paths = scene_elem.compute_paths(order=n_bounces)

                # paths is a Paths object or an iterator
                # For non-chunked: Paths with .vertices and .objects
                if hasattr(paths, "vertices"):
                    verts = np.asarray(paths.vertices)
                    objs = np.asarray(paths.objects)
                    mask = np.asarray(paths.mask) if paths.mask is not None else None

                    # Flatten batch dimensions: (tx, rx, candidates, path_len, 3)
                    # -> (candidates, path_len, 3)
                    orig_shape = verts.shape
                    path_len = orig_shape[-2]
                    verts = verts.reshape(-1, path_len, 3)
                    objs = objs.reshape(-1, path_len)
                    if mask is not None:
                        mask = mask.reshape(-1)

                    # Filter valid paths (mask True and no NaN)
                    valid = np.all(np.isfinite(verts), axis=(1, 2))
                    if mask is not None:
                        valid = valid & mask.astype(bool)

                    if np.any(valid):
                        verts = verts[valid]
                        objs = objs[valid]
                        n = verts.shape[0]
                        all_path_vertices.append(verts)
                        all_object_indices.append(objs)
                        all_element_indices.append(np.full(n, elem_idx, dtype=np.intp))

            except Exception:
                # Some bounce orders may not have valid paths
                continue

    if not all_path_vertices:
        return PropagationPaths.from_powers(k_hat=np.zeros((0, 3)), power=np.zeros(0))

    # Concatenate all paths (they may have different numbers of vertices)
    # Pad to same length
    max_verts = max(pv.shape[1] for pv in all_path_vertices)
    padded_verts = []
    padded_objs = []
    for pv, po in zip(all_path_vertices, all_object_indices, strict=True):
        if pv.shape[1] < max_verts:
            pad_width_v = ((0, 0), (0, max_verts - pv.shape[1]), (0, 0))
            pv = np.pad(pv, pad_width_v, mode="edge")
            pad_width_o = ((0, 0), (0, max_verts - po.shape[1]))
            po = np.pad(po, pad_width_o, constant_values=-1)
        padded_verts.append(pv)
        padded_objs.append(po)

    path_vertices = np.concatenate(padded_verts, axis=0)
    object_indices = np.concatenate(padded_objs, axis=0)
    element_indices = np.concatenate(all_element_indices, axis=0)

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
        return [n_complex(5.31, 0.0326, freq_hz)]

    try:
        from differt.em import materials as differt_materials
    except ImportError:
        # Older DiffeRT without material database
        return [n_complex(5.31, 0.0326, freq_hz) for _ in material_names]

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
            result.append(n_complex(5.31, 0.0326, freq_hz))

    return result
