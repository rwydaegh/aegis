"""Evidence-supported routes on the panorama provider's own link graph.

The contract in this module is deliberately independent of the historical
registered-span pedestrian route. It makes no routing-service request. It
enumerates admitted camera pairs, follows the provider graph between them, and
admits only a corridor whose complete registered polyline remains within the
declared evidence distance of an admitted camera.
"""

from __future__ import annotations

import hashlib
import heapq
import json
import pathlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from .links import LinkGraph
from .route import register_road_leg

PROVIDER_CORRIDOR_V1 = "provider_corridor_v1"
DEFAULT_MAX_EVIDENCE_GAP_M = 20.0


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _finite_xy(value: Any, *, label: str) -> np.ndarray:
    point = np.asarray(value, dtype=np.float64)
    if point.ndim != 1 or point.size < 2 or not np.all(np.isfinite(point[:2])):
        raise ValueError(f"{label} must carry a finite position with at least two coordinates")
    return point[:2]


def provider_graph_seal(graph: LinkGraph) -> dict[str, Any]:
    """Canonical topology and geometry identity for one provider graph."""
    nodes = sorted(graph.position)
    document = {
        "positions_enu_m": {node: [float(v) for v in _finite_xy(graph.position[node], label=node)] for node in nodes},
        "neighbours": {
            node: sorted(other for other in graph.neighbours.get(node, ()) if other in graph.position) for node in nodes
        },
    }
    return {
        "sha256": _sha256_bytes(_canonical_bytes(document)),
        "nodes": len(nodes),
        "edges": sum(len(ends) for ends in document["neighbours"].values()) // 2,
    }


def provider_graph_input_paths(site: str, root: pathlib.Path) -> tuple[pathlib.Path, ...]:
    """Files that contribute provider nodes and links for ``site``.

    This mirrors :func:`semantic_twin.walk.route.load_link_graph` without
    changing that legacy loader's provenance bytes.
    """
    inputs: list[pathlib.Path] = []
    screening = root / "outputs" / "city_screening" / "screening.json"
    if screening.is_file():
        document = json.loads(screening.read_text(encoding="utf-8"))
        if any(row.get("key") == site for row in document.get("rows", ())):
            inputs.append(screening)
    traversal = root / "outputs" / "walk_korenmarkt_saturation" / "walk_selection.json"
    if site == "korenmarkt" and traversal.is_file():
        inputs.append(traversal)
    return tuple(inputs)


def seal_input_files(paths: Sequence[pathlib.Path], root: pathlib.Path) -> tuple[dict[str, Any], ...]:
    """Seal exact provider input bytes in stable path order."""
    sealed = []
    for path in sorted((path.resolve() for path in paths), key=str):
        payload = path.read_bytes()
        sealed.append(
            {
                "path": str(path.relative_to(root.resolve())),
                "sha256": _sha256_bytes(payload),
                "bytes": len(payload),
            }
        )
    return tuple(sealed)


def continuous_nearest_camera_gap_m(polyline: np.ndarray, camera_xy: np.ndarray) -> float:
    """Exact maximum nearest-camera distance over a piecewise-linear route.

    On one segment, squared distances to all cameras share the same quadratic
    term. The nearest camera can therefore change only at a pairwise Voronoi
    breakpoint. Evaluating both segment ends and every breakpoint gives the
    exact maximum of the lower envelope, including a maximum in the interior.
    """
    line = np.asarray(polyline, dtype=np.float64)
    cameras = np.asarray(camera_xy, dtype=np.float64)
    if line.ndim != 2 or line.shape[0] < 2 or line.shape[1] < 2 or not np.all(np.isfinite(line[:, :2])):
        raise ValueError("provider corridor polyline must contain at least two finite points")
    if cameras.ndim != 2 or cameras.shape[0] == 0 or cameras.shape[1] < 2 or not np.all(np.isfinite(cameras[:, :2])):
        raise ValueError("continuous coverage needs at least one finite admitted camera")
    cameras = cameras[:, :2]
    maximum = 0.0
    for start, end in zip(line[:-1, :2], line[1:, :2], strict=True):
        direction = end - start
        parameters = [0.0, 1.0]
        for first in range(len(cameras)):
            for second in range(first + 1, len(cameras)):
                delta = cameras[second] - cameras[first]
                slope = 2.0 * float(np.dot(direction, delta))
                if slope == 0.0:
                    continue
                intercept = (
                    2.0 * float(np.dot(start, delta))
                    + float(np.dot(cameras[first], cameras[first]))
                    - float(np.dot(cameras[second], cameras[second]))
                )
                parameter = -intercept / slope
                if 0.0 < parameter < 1.0:
                    parameters.append(parameter)
        points = start[None, :] + np.asarray(parameters)[:, None] * direction[None, :]
        nearest = np.linalg.norm(points[:, None, :] - cameras[None, :, :], axis=2).min(axis=1)
        maximum = max(maximum, float(nearest.max()))
    return maximum


def _canonical_shortest_path(graph: LinkGraph, source: str, target: str) -> tuple[str, ...]:
    """Shortest provider-node path with a lexical full-path tie break."""
    if source not in graph.position or target not in graph.position:
        return ()
    queue: list[tuple[float, tuple[str, ...], str]] = [(0.0, (source,), source)]
    best: dict[str, tuple[float, tuple[str, ...]]] = {source: (0.0, (source,))}
    while queue:
        distance, path, node = heapq.heappop(queue)
        if best.get(node) != (distance, path):
            continue
        if node == target:
            return path
        here = _finite_xy(graph.position[node], label=node)
        for other in sorted(set(graph.neighbours.get(node, ()))):
            if other not in graph.position or other in path:
                continue
            step = float(np.linalg.norm(_finite_xy(graph.position[other], label=other) - here))
            candidate = (distance + step, (*path, other))
            previous = best.get(other)
            if previous is None or candidate < previous:
                best[other] = candidate
                heapq.heappush(queue, (candidate[0], candidate[1], other))
    return ()


def _registered_path(
    graph: LinkGraph, node_path: Sequence[str], start_xy: np.ndarray, end_xy: np.ndarray
) -> np.ndarray:
    raw = np.asarray([_finite_xy(graph.position[node], label=node) for node in node_path], dtype=np.float64)
    if raw.shape[0] == 1:
        raw = np.repeat(raw, 2, axis=0)
    return register_road_leg(raw, start_xy, end_xy)


@dataclass(frozen=True)
class ProviderCorridor:
    """The selected corridor and its complete deterministic evidence seal."""

    station_ids: tuple[str, str]
    node_path: tuple[str, ...]
    registered_polyline: np.ndarray
    continuous_max_gap_m: float
    endpoint_span_m: float
    path_length_m: float
    audit: tuple[dict[str, Any], ...]
    seal: dict[str, Any]

    def provenance(self) -> dict[str, Any]:
        return {
            "contract": PROVIDER_CORRIDOR_V1,
            "station_ids": list(self.station_ids),
            "provider_node_path": list(self.node_path),
            "registered_polyline_enu_m": self.registered_polyline.tolist(),
            "continuous_max_gap_m": self.continuous_max_gap_m,
            "endpoint_span_m": self.endpoint_span_m,
            "path_length_m": self.path_length_m,
            "selection_audit": [dict(row) for row in self.audit],
            **self.seal,
        }


def select_provider_corridor(
    stations: Sequence[Mapping[str, Any]],
    graph: LinkGraph,
    *,
    max_gap_m: float = DEFAULT_MAX_EVIDENCE_GAP_M,
    centre_xy: tuple[float, float] = (0.0, 0.0),
    radius_m: float | None = None,
    admitted_report: pathlib.Path | None = None,
    provider_inputs: Sequence[pathlib.Path] = (),
    root: pathlib.Path | None = None,
) -> ProviderCorridor:
    """Select the widest continuously evidence-supported provider corridor."""
    if not np.isfinite(max_gap_m) or max_gap_m <= 0.0:
        raise ValueError("provider corridor max_gap_m must be positive and finite")
    centre = np.asarray(centre_xy, dtype=np.float64)
    eligible: list[dict[str, Any]] = []
    for raw in stations:
        station_id = str(raw["name"])
        camera = np.asarray(raw["camera_enu_m"], dtype=np.float64)
        xy = _finite_xy(camera, label=f"station {station_id!r}")
        if radius_m is not None and float(np.linalg.norm(xy - centre)) > radius_m:
            continue
        node = str(raw.get("node") or "")
        if node in graph.position:
            eligible.append({"station_id": station_id, "node": node, "xy": xy})
    if len({row["station_id"] for row in eligible}) != len(eligible):
        raise ValueError("provider corridor station IDs must be unique")
    if len(eligible) < 2:
        raise RuntimeError("provider corridor needs at least two admitted cameras in the provider graph")
    eligible.sort(key=lambda row: (row["station_id"], row["node"]))
    audits: list[dict[str, Any]] = []
    accepted: list[tuple[tuple[Any, ...], dict[str, Any], np.ndarray, tuple[str, ...]]] = []
    for first in range(len(eligible)):
        for second in range(first + 1, len(eligible)):
            left, right = eligible[first], eligible[second]
            node_path = _canonical_shortest_path(graph, left["node"], right["node"])
            row: dict[str, Any] = {
                "station_ids": [left["station_id"], right["station_id"]],
                "endpoint_node_ids": [left["node"], right["node"]],
                "connected": bool(node_path),
            }
            if not node_path:
                row.update({"admitted": False, "reason": "provider nodes are disconnected"})
                audits.append(row)
                continue
            component = [
                station for station in eligible if _canonical_shortest_path(graph, left["node"], station["node"])
            ]
            cameras = np.asarray([station["xy"] for station in component], dtype=np.float64)
            polyline = _registered_path(graph, node_path, left["xy"], right["xy"])
            span = float(np.linalg.norm(right["xy"] - left["xy"]))
            path_length = float(np.linalg.norm(np.diff(polyline, axis=0), axis=1).sum())
            maximum_gap = continuous_nearest_camera_gap_m(polyline, cameras)
            admitted = maximum_gap <= max_gap_m
            row.update(
                {
                    "provider_node_path": list(node_path),
                    "evidence_station_ids": [station["station_id"] for station in component],
                    "endpoint_span_m": span,
                    "path_length_m": path_length,
                    "continuous_max_gap_m": maximum_gap,
                    "admitted": admitted,
                    "reason": None if admitted else f"continuous evidence gap exceeds {max_gap_m:g} m",
                }
            )
            audits.append(row)
            if admitted:
                key = (-span, path_length, left["station_id"], right["station_id"])
                accepted.append((key, row, polyline, node_path))
    if not accepted:
        raise RuntimeError(f"no provider corridor remains everywhere within {max_gap_m:g} m of an admitted camera")
    accepted.sort(key=lambda item: item[0])
    _, selected, polyline, node_path = accepted[0]
    for row in audits:
        row["selected"] = row is selected

    base = root.resolve() if root is not None else None
    report_seal = None
    if admitted_report is not None:
        report_bytes = admitted_report.read_bytes()
        report_seal = {
            "path": str(admitted_report.resolve().relative_to(base)) if base is not None else str(admitted_report),
            "sha256": _sha256_bytes(report_bytes),
            "bytes": len(report_bytes),
        }
    input_seals = seal_input_files(provider_inputs, base) if base is not None else ()
    graph_seal = provider_graph_seal(graph)
    seal_payload = {
        "contract": PROVIDER_CORRIDOR_V1,
        "max_evidence_gap_m": float(max_gap_m),
        "admitted_station_report": report_seal,
        "provider_graph_inputs": list(input_seals),
        "provider_graph": graph_seal,
        "station_ids": selected["station_ids"],
        "provider_node_path": list(node_path),
        "registered_polyline_enu_m": polyline.tolist(),
        "continuous_max_gap_m": selected["continuous_max_gap_m"],
        "endpoint_span_m": selected["endpoint_span_m"],
        "path_length_m": selected["path_length_m"],
        "selection_audit": audits,
    }
    seal = {
        "max_evidence_gap_m": float(max_gap_m),
        "admitted_station_report": report_seal,
        "provider_graph_inputs": list(input_seals),
        "provider_graph": graph_seal,
        "selection_sha256": _sha256_bytes(_canonical_bytes(seal_payload)),
    }
    return ProviderCorridor(
        station_ids=tuple(selected["station_ids"]),
        node_path=node_path,
        registered_polyline=polyline,
        continuous_max_gap_m=float(selected["continuous_max_gap_m"]),
        endpoint_span_m=float(selected["endpoint_span_m"]),
        path_length_m=float(selected["path_length_m"]),
        audit=tuple(audits),
        seal=seal,
    )
