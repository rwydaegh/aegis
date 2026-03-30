"""Public API: skeletonize and polygonize."""

from __future__ import annotations

from collections import Counter
from itertools import chain

import numpy as np

from aegis.environment.skeleton.events import Subtree, _DormerEvent, _EdgeEvent, _EventQueue, _SplitEvent
from aegis.environment.skeleton.geometry import (
    EPSILON,
    PARALLEL,
    Edge2,
    _cross2,
    _dot,
    _iter_circular_prev_next,
    _iter_circular_prev_this_next,
    _magnitude,
    _vec2,
    _vec_eq,
)
from aegis.environment.skeleton.graph import _Poly2FacesGraph
from aegis.environment.skeleton.postprocess import (
    _detect_dormers,
    _merge_node_clusters,
    _process_dormers,
    _remove_ghosts,
)
from aegis.environment.skeleton.slav import _SLAV


def skeletonize(edge_contours: list[np.ndarray]) -> list[Subtree]:
    """Compute the straight skeleton of a polygon.

    Args:
        edge_contours: list of contour arrays, each (N, 2) float64 vertices.
            First is outer polygon (CCW), rest are holes (CW).

    Returns:
        list of Subtree namedtuples where source/sinks are numpy arrays.
    """
    # Convert vertex arrays to Edge2 contours
    edge2_contours = []
    for contour in edge_contours:
        contour = np.asarray(contour, dtype=np.float64)
        edges = []
        n = len(contour)
        for i in range(n):
            p1 = _vec2(contour[i][0], contour[i][1])
            p2 = _vec2(contour[(i + 1) % n][0], contour[(i + 1) % n][1])
            edges.append(Edge2(p1, p2))
        edge2_contours.append(edges)

    return _skeletonize_edges(edge2_contours)


def _skeletonize_edges(edge_contours):
    """Core skeleton computation on Edge2 contours."""
    slav = _SLAV(edge_contours)

    dormers = _detect_dormers(slav, edge_contours)

    initial_events = []
    for lav in slav:
        for vertex in lav:
            initial_events.append(vertex.next_event())

    if dormers:
        _process_dormers(dormers, initial_events)

    output = []
    prioque = _EventQueue()
    for ev in initial_events:
        if ev:
            prioque.put(ev)

    while not (prioque.empty() or slav.empty()):
        top_event_list = prioque.get_all_equal_distance()
        for i in top_event_list:
            if isinstance(i, _EdgeEvent):
                if not i.vertex_a.is_valid or not i.vertex_b.is_valid:
                    continue
                (arc, events) = slav.handle_edge_event(i)
            elif isinstance(i, _SplitEvent):
                if not i.vertex.is_valid:
                    continue
                (arc, events) = slav.handle_split_event(i)
            elif isinstance(i, _DormerEvent):
                if not i.eventList[0].vertex.is_valid or not i.eventList[1].vertex.is_valid:
                    continue
                (arc, events) = slav.handle_dormer_event(i)
            else:
                continue
            prioque.put_all(events)

            if arc is not None:
                if isinstance(arc, list):
                    output.extend(arc)
                else:
                    output.append(arc)

    # Convert Subtree sinks from tuples/lists to mutable lists for post-processing
    output = [Subtree(arc.source, arc.height, list(arc.sinks)) for arc in output]

    output = _merge_node_clusters(output, edge_contours)
    _remove_ghosts(output)

    return output


# ---------------------------------------------------------------------------
# Polygonize helpers
# ---------------------------------------------------------------------------


def _build_edge2_contours(fp2d, center, num_poly_verts, first_vert_index):
    """Build centered Edge2 contours from 2D footprint vertices."""
    edges2d = []
    for i in range(num_poly_verts):
        p1 = fp2d[i] - center
        p2 = fp2d[(i + 1) % num_poly_verts] - center
        e = Edge2(p1, p2)
        e.i1 = first_vert_index + i
        e.i2 = first_vert_index + (i + 1) % num_poly_verts
        edges2d.append(e)
    return edges2d


def _build_hole_contours(holes, center, verts_out, z_base, edges2d):
    """Build Edge2 contours for holes, appending hole verts to verts_out."""
    hole_contours = []
    hole_infos = []
    for hole in holes:
        hole = np.asarray(hole, dtype=np.float64)
        h2d = hole[:, :2] if hole.shape[1] >= 3 else hole
        n_hole = len(h2d)
        hole_start = len(verts_out)
        for v in h2d:
            verts_out.append(np.array([v[0], v[1], z_base]))
        hole_edges = []
        for i in range(n_hole):
            p1 = h2d[i] - center
            p2 = h2d[(i + 1) % n_hole] - center
            e = Edge2(p1, p2)
            e.i1 = hole_start + i
            e.i2 = hole_start + (i + 1) % n_hole
            hole_edges.append(e)
        edges2d.extend(hole_edges)
        hole_contours.append(hole_edges)
        hole_infos.append((hole_start, n_hole))
    return hole_contours, hole_infos


def _build_skeleton_graph(
    skeleton, edges2d, verts_out, center, z_base, tan_alpha, first_vert_index, num_poly_verts, hole_infos
):
    """Build the face-extraction graph from skeleton arcs."""
    first_skel_index = len(verts_out)
    for arc in skeleton:
        node = np.array([arc.source[0] + center[0], arc.source[1] + center[1], arc.height * tan_alpha + z_base])
        verts_out.append(node)

    graph = _Poly2FacesGraph()

    # Add polygon edges
    for edge in _iter_circular_prev_next(list(range(first_vert_index, first_vert_index + num_poly_verts))):
        graph.add_edge(edge)

    # Add hole edges
    for hole_start, n_hole in hole_infos:
        for edge in _iter_circular_prev_next(list(range(hole_start, hole_start + n_hole))):
            graph.add_edge(edge)

    # Add skeleton edges
    for index, arc in enumerate(skeleton):
        a_index = index + first_skel_index
        for sink in arc.sinks:
            edge_match = [e for e in edges2d if _vec_eq(e.p1, sink)]
            if edge_match:
                s_index = edge_match[0].i1
            else:
                skel_match = [idx for idx, a in enumerate(skeleton) if _vec_eq(a.source, sink)]
                s_index = skel_match[0] + first_skel_index if skel_match else None
            if s_index is not None:
                graph.add_edge((a_index, s_index))

    # Build 2D verts lookup for angle computation
    max_idx = max(max(graph.g_dict), first_skel_index + len(skeleton) - 1) if graph.g_dict else 0
    graph_verts = [None] * (max_idx + 1)
    for i in range(len(verts_out)):
        v = verts_out[i]
        graph_verts[i] = _vec2(v[0], v[1])

    embedding = graph.circular_embedding(graph_verts, "CCW")
    faces3d = graph.faces(embedding, first_skel_index)

    return faces3d, first_skel_index


def _find_spike(face, verts_out):
    """Find a spike vertex in a face (near-180-degree turn). Returns (prev_v, this_v, next_v) or None."""
    if len(face) <= 3:
        return None
    for prev_v, this_v, next_v in _iter_circular_prev_this_next(face):
        s0 = verts_out[this_v] - verts_out[prev_v]
        s1 = verts_out[next_v] - verts_out[this_v]
        s0_2d = _vec2(s0[0], s0[1])
        s1_2d = _vec2(s1[0], s1[1])
        s0m = _magnitude(s0_2d)
        s1m = _magnitude(s1_2d)
        if not (s0m and s1m):
            continue
        dot_cosine = _dot(s0_2d, s1_2d) / (s0m * s1m)
        cross_sine = _cross2(s0_2d, s1_2d)
        if abs(dot_cosine + 1.0) < PARALLEL and cross_sine > -EPSILON:
            return (prev_v, this_v, next_v)
    return None


def _remove_spikes(faces3d, verts_out, first_skel_index):
    """Remove spike vertices from faces by merging adjacent faces."""
    had_spikes = True
    while had_spikes:
        had_spikes = False
        for face in faces3d:
            spike = _find_spike(face, verts_out)
            if spike is None:
                continue

            had_spikes = True
            prev_v, this_v, next_v = spike

            right_idx, left_idx = None, None
            for fi, f in enumerate(faces3d):
                if [p for p, n in _iter_circular_prev_next(f) if p == this_v and n == prev_v]:
                    right_idx = fi
                if [p for p, n in _iter_circular_prev_next(f) if p == next_v and n == this_v]:
                    left_idx = fi

            if right_idx is None or left_idx is None:
                had_spikes = False
                continue

            if right_idx == left_idx:
                common_face = faces3d[right_idx]
                if this_v in common_face:
                    common_face.remove(this_v)
                if prev_v in common_face:
                    common_face.remove(prev_v)
                if this_v in face:
                    face.remove(this_v)
                break

            right_face = faces3d[right_idx]
            rot_index = next(x[0] for x in enumerate(right_face) if x[1] == prev_v)
            right_face = right_face[rot_index:] + right_face[:rot_index]

            left_face = faces3d[left_idx]
            rot_index = next(x[0] for x in enumerate(left_face) if x[1] == this_v)
            left_face = left_face[rot_index:] + left_face[:rot_index]

            merged_face = right_face + left_face[1:]

            orig_indices = [x[0] for x in enumerate(merged_face) if x[1] < first_skel_index]
            if orig_indices:
                next_orig_index = orig_indices[0]
                merged_face = merged_face[next_orig_index:] + merged_face[:next_orig_index]

            if merged_face == face:
                break

            if this_v in face:
                face.remove(this_v)
            for i in sorted([right_idx, left_idx], reverse=True):
                del faces3d[i]
            faces3d.append(merged_face)

            break


def _fix_parallel_edges(faces3d, verts_out, first_skel_index):
    """Remove redundant skeleton vertices on collinear edges and duplicate adjacent vertices."""
    counts = Counter(chain.from_iterable(faces3d))
    for face in faces3d:
        if len(face) > 3:
            verts_to_remove = []
            for prev_v, this_v, next_v in _iter_circular_prev_this_next(face):
                if counts[this_v] < 3 and this_v >= first_skel_index:
                    s0 = verts_out[this_v] - verts_out[prev_v]
                    s1 = verts_out[next_v] - verts_out[this_v]
                    s0_2d = _vec2(s0[0], s0[1])
                    s1_2d = _vec2(s1[0], s1[1])
                    s0m = _magnitude(s0_2d)
                    s1m = _magnitude(s1_2d)
                    if s0m != 0.0 and s1m != 0.0:
                        dot_cosine = _dot(s0_2d, s1_2d) / (s0m * s1m)
                        if abs(dot_cosine - 1.0) < PARALLEL:
                            verts_to_remove.append(this_v)
                    else:
                        if this_v not in verts_to_remove:
                            verts_to_remove.append(this_v)
            for item in verts_to_remove:
                face.remove(item)

        # Remove adjacent identical vertices
        verts_to_remove = []
        for prev_v, next_v in _iter_circular_prev_next(face):
            if prev_v == next_v:
                verts_to_remove.append(prev_v)
        for item in verts_to_remove:
            if item in face:
                face.remove(item)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def polygonize(
    verts_out: list,
    footprint: np.ndarray,
    height: float = 0.0,
    tan: float = 0.0,
    holes: list | None = None,
) -> list[list[int]]:
    """Compute roof faces from a building footprint polygon.

    Args:
        verts_out: mutable list of 3D numpy arrays. Footprint vertices should
            already be at indices 0..N-1. Skeleton nodes are appended.
        footprint: (N, 2) or (N, 3) float64 vertices of outer polygon (CCW).
        height: maximum roof height. Takes precedence over tan.
        tan: tangent of roof pitch angle.
        holes: optional list of (M, 2) or (M, 3) arrays for hole contours (CW).

    Returns:
        list of faces, each a list of vertex indices into verts_out.
    """
    footprint = np.asarray(footprint, dtype=np.float64)
    if footprint.ndim != 2 or footprint.shape[0] < 3:
        return []

    # Extract z-base from first vertex (or 0)
    if footprint.shape[1] >= 3:
        z_base = float(footprint[0, 2])
        fp2d = footprint[:, :2]
    else:
        z_base = float(verts_out[0][2]) if len(verts_out) > 0 and len(verts_out[0]) >= 3 else 0.0
        fp2d = footprint

    num_poly_verts = len(fp2d)
    first_vert_index = 0
    center = np.mean(fp2d, axis=0)

    # Build Edge2 contours
    edges2d = _build_edge2_contours(fp2d, center, num_poly_verts, first_vert_index)
    edge_contours = [edges2d.copy()]

    hole_infos = []
    if holes:
        hole_contours, hole_infos = _build_hole_contours(holes, center, verts_out, z_base, edges2d)
        edge_contours.extend(hole_contours)

    # Skeletonize
    skeleton = _skeletonize_edges(edge_contours)

    # Compute skeleton node heights
    if height and skeleton:
        max_skel_height = max(arc.height for arc in skeleton)
        tan_alpha = height / max_skel_height if max_skel_height > 0 else 0.0
    else:
        tan_alpha = tan

    # Build graph and extract faces
    faces3d, first_skel_index = _build_skeleton_graph(
        skeleton,
        edges2d,
        verts_out,
        center,
        z_base,
        tan_alpha,
        first_vert_index,
        num_poly_verts,
        hole_infos,
    )

    # Clean up faces
    _remove_spikes(faces3d, verts_out, first_skel_index)
    _fix_parallel_edges(faces3d, verts_out, first_skel_index)

    return faces3d
