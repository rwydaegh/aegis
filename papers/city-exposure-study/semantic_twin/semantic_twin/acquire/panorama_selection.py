"""Choose a dated, spatially useful subset of a site's panorama walk."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import numpy as np


@dataclass(frozen=True)
class SelectionOptions:
    """Controls for panorama selection and the open-sky screen."""

    count: int
    walk_date: str | None = None
    support_mesh: tuple[np.ndarray, np.ndarray] | None = None
    ground_z_m: float | None = None
    open_sky_m: float = 2.5
    along_links: bool = False


def spread_subset(positions: np.ndarray, count: int) -> list[int]:
    """Farthest-point sampling, seeded with the point nearest the centre."""
    if positions.shape[0] == 0:
        return []
    count = min(count, positions.shape[0])
    first = int(np.argmin(np.linalg.norm(positions, axis=1)))
    chosen = [first]
    distance = np.linalg.norm(positions - positions[first], axis=1)
    while len(chosen) < count:
        nxt = int(np.argmax(distance))
        if distance[nxt] <= 0.0:
            break
        chosen.append(nxt)
        distance = np.minimum(distance, np.linalg.norm(positions - positions[nxt], axis=1))
    return chosen


def chain_subset(walk: list[dict[str, Any]], positions: np.ndarray, count: int) -> list[int]:
    """Take consecutive linked panoramas, growing outwards from the centre."""
    if not walk:
        return []
    count = min(count, len(walk))
    index = {p["pano_id"]: i for i, p in enumerate(walk)}
    first = int(np.argmin(np.linalg.norm(positions, axis=1)))

    chosen = [first]
    seen = {first}
    frontier = [[first], [first]]
    while len(chosen) < count:
        grew = False
        for end in frontier:
            if len(chosen) >= count or not end:
                continue
            here = end[-1]
            options = _unseen_neighbours(walk[here], index, seen)
            if not options:
                end.clear()
                continue
            nxt = min(options, key=lambda i, here=here: float(np.linalg.norm(positions[i] - positions[here])))
            chosen.append(nxt)
            seen.add(nxt)
            end.append(nxt)
            grew = True
        if not grew:
            break
    return chosen


def _unseen_neighbours(panorama: dict[str, Any], index: dict[str, int], seen: set[int]) -> list[int]:
    neighbours = [link if isinstance(link, str) else link.get("pano_id") for link in panorama.get("links", [])]
    return [index[name] for name in neighbours if name in index and index[name] not in seen]


def topmost_surface(
    support_mesh: tuple[np.ndarray, np.ndarray],
    positions: np.ndarray,
) -> np.ndarray:
    """Return the highest tile surface above each horizontal position."""
    try:
        import trimesh
        from trimesh.ray.ray_pyembree import RayMeshIntersector
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise SystemExit(
            "the open sky filter needs the raycast extra: pip install trimesh embreex, "
            "or pass --open-sky-m 0 to select on count alone"
        ) from exc
    vertices, faces = support_mesh
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices, np.float64), faces=np.asarray(faces), process=False)
    ceiling = float(mesh.vertices[:, 2].max()) + 50.0
    origins = np.column_stack([positions, np.full(len(positions), ceiling)])
    directions = np.tile(np.array([0.0, 0.0, -1.0]), (len(positions), 1))
    locations, index_ray, _ = RayMeshIntersector(mesh).intersects_location(origins, directions, multiple_hits=False)
    height = np.full(len(positions), np.nan)
    if len(index_ray):
        height[index_ray] = locations[:, 2]
    return height


def select(row: dict[str, Any], options: SelectionOptions) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Choose a subset of one dated panorama walk and record its provenance."""
    date = options.walk_date or row["walk_date"]
    walk = [p for p in row["panoramas"] if p["date"] == date and p["links"]]
    if not walk:
        dates = sorted({p["date"] for p in row["panoramas"] if p["links"]})
        raise SystemExit(f"{row['key']}: no linked panoramas dated {date}, available: {', '.join(dates)}")
    positions = np.array([[p["east_m"], p["north_m"]] for p in walk], dtype=np.float64)

    roofed = 0
    if options.open_sky_m > 0.0 and options.support_mesh is not None and options.ground_z_m is not None:
        walk, positions, roofed = _drop_roofed(row["key"], date, walk, positions, options)

    order = (
        chain_subset(walk, positions, options.count) if options.along_links else spread_subset(positions, options.count)
    )
    picked = [walk[i] for i in order]
    taken = positions[order] if order else np.zeros((0, 2))
    provenance = _selection_provenance(row, options, date, len(walk), roofed, taken)
    return picked, provenance


def _drop_roofed(
    site: str,
    date: str,
    walk: list[dict[str, Any]],
    positions: np.ndarray,
    options: SelectionOptions,
) -> tuple[list[dict[str, Any]], np.ndarray, int]:
    support_mesh = cast(tuple[np.ndarray, np.ndarray], options.support_mesh)
    ground_z_m = cast(float, options.ground_z_m)
    above = topmost_surface(support_mesh, positions)
    outdoor = ~(above > ground_z_m + options.open_sky_m)
    roofed = int((~outdoor).sum())
    if not outdoor.any():
        raise SystemExit(
            f"{site}: every one of the {len(walk)} panoramas dated {date} has tile surface more "
            f"than {options.open_sky_m} m above it, so the whole capture is indoors. Name another capture "
            f"date with --walk-date."
        )
    return [p for p, keep in zip(walk, outdoor, strict=True) if keep], positions[outdoor], roofed


def _selection_provenance(
    row: dict[str, Any],
    options: SelectionOptions,
    date: str,
    walk_count: int,
    roofed: int,
    taken: np.ndarray,
) -> dict[str, Any]:
    separations = [float(np.linalg.norm(taken[i] - taken[:i], axis=1).min()) for i in range(1, len(taken))]
    return {
        "selection": (
            "consecutive panoramas along the capture links, grown outward from the centre"
            if options.along_links
            else "farthest-point sampling over the walk, seeded at the panorama nearest the centre"
        ),
        "walk_date": date,
        "screened_walk_date": row["walk_date"],
        "walk_date_overridden": options.walk_date is not None and options.walk_date != row["walk_date"],
        "walk_panoramas": walk_count,
        "walk_panoramas_dropped_as_roofed": roofed,
        "open_sky_m": options.open_sky_m if options.open_sky_m > 0.0 else None,
        "open_sky_rule": (
            "a candidate is dropped when the topmost tile surface above it is more than open_sky_m "
            "above the scene ground datum, which is what an arcade or a concourse looks like from "
            "above. It screens the geometry, not the image, so it costs no request."
        )
        if options.open_sky_m > 0.0
        else None,
        "selected": len(taken),
        "minimum_separation_m": round(min(separations), 2) if separations else None,
        "median_separation_m": round(float(np.median(separations)), 2) if separations else None,
        "extent_east_m": [round(float(taken[:, 0].min()), 1), round(float(taken[:, 0].max()), 1)]
        if len(taken)
        else None,
        "extent_north_m": [round(float(taken[:, 1].min()), 1), round(float(taken[:, 1].max()), 1)]
        if len(taken)
        else None,
        "screening_median_spacing_m": row["walk_spacing_m"],
    }
