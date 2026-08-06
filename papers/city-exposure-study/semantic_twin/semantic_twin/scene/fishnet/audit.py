"""Measure what the cut cost, in the units propagation cares about.

Three questions, and they are asked of the output rather than of the code that
made it. The round trip in :func:`rasterize_fishnet` deliberately reuses the
stored image-space triangles instead of re-projecting them, because a
re-projection would hide a projection bug behind the same bug.

* Did the class survive simplification. :func:`class_fidelity`.
* Did visibility survive it, in both directions. :func:`occlusion_fidelity`
  separates a phantom pixel, which puts a scatterer where the camera cannot see
  one, from a deleted pixel, which silently removes a propagation path.
* How much projected surface did occlusion take away, and where did it go.
  :func:`occlusion_budget`.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..pinhole import PinholeView
from ..planar import rasterize_convex
from .regions import UNPAINTABLE, RegionMap
from .surface import REJECTION_REASONS, FishnetRaster, FishnetSurface

# Rejection reasons that remove surface because something stood in the way,
# rather than because the candidate was degenerate.  They split by what happens
# to the removed surface next.  Nothing ever reconstructs what a mesh occluder
# or an unmodelled foreground object was hiding, so that area is simply absent.
# A transient goes to the dynamic body layer and street furniture goes to the
# object proxy pipeline, so that area is deferred rather than lost, and it is
# only a hole if those layers do not run.
ABSENT_SURFACE_REJECTIONS: tuple[str, ...] = (
    "occluded_by_support_mesh",
    "clutter_in_front",
    "mesh_or_pose_conflict",
)
DEFERRED_SURFACE_REJECTIONS: tuple[str, ...] = ("transient_object", "not_support_surface")
OCCLUSION_REJECTIONS: tuple[str, ...] = ABSENT_SURFACE_REJECTIONS + DEFERRED_SURFACE_REJECTIONS


def rasterize_fishnet(surface: FishnetSurface, shape: tuple[int, int]) -> FishnetRaster:
    """Paint the output faces back into the image with a nearest-surface test.

    This is the round trip used to measure what simplification actually cost, so
    it deliberately reuses the stored image-space triangles rather than
    re-projecting and hiding a projection bug.
    """
    height, width = int(shape[0]), int(shape[1])
    if height < 1 or width < 1:
        raise ValueError("shape must be positive")
    painted = np.full((height, width), UNPAINTABLE, dtype=np.int64)
    source = np.full((height, width), UNPAINTABLE, dtype=np.int64)
    depth = np.full((height, width), np.inf, dtype=np.float64)
    for index in range(surface.triangle_count):
        rows, columns = rasterize_convex(surface.face_image[index], width, height)
        if rows.size == 0:
            continue
        nearer = surface.face_depth[index] < depth[rows, columns]
        rows, columns = rows[nearer], columns[nearer]
        painted[rows, columns] = surface.face_class[index]
        source[rows, columns] = surface.face_source_triangle[index]
        depth[rows, columns] = surface.face_depth[index]
    return FishnetRaster(painted, source, np.where(np.isfinite(depth), depth, np.nan))


def class_fidelity(raster: FishnetRaster, regions: RegionMap) -> dict[str, float]:
    """Fraction of source pixels whose class survives the fishnet round trip."""
    painted = raster.class_map
    if painted.shape != regions.source_class.shape:
        raise ValueError("raster must match the region map resolution")
    paintable = regions.source_class != UNPAINTABLE
    covered = paintable & (painted != UNPAINTABLE)
    changed = int(np.count_nonzero(covered & (painted != regions.source_class)))
    paintable_count = int(np.count_nonzero(paintable))
    covered_count = int(np.count_nonzero(covered))
    return {
        "paintable_pixels": paintable_count,
        "covered_pixels": covered_count,
        "coverage": covered_count / paintable_count if paintable_count else 0.0,
        "changed_pixels": changed,
        "changed_fraction": changed / covered_count if covered_count else 0.0,
        "leaked_pixels": int(np.count_nonzero(~paintable & (painted != UNPAINTABLE))),
    }


def occlusion_fidelity(raster: FishnetRaster, face_ids: np.ndarray, regions: RegionMap) -> dict[str, float]:
    """Both directions of the visibility error, which propagation cares about.

    A phantom pixel is one painted by a surface element that is not the mesh
    first hit there, which would put a scatterer where the camera cannot see
    one.  A deleted pixel is a paintable first-hit pixel with no surface element
    over it, which silently removes a propagation path.
    """
    face_ids = np.asarray(face_ids, dtype=np.int64)
    if face_ids.shape != raster.source_triangle.shape:
        raise ValueError("face_ids must match the raster resolution")
    painted = raster.source_triangle != UNPAINTABLE
    phantom = int(np.count_nonzero(painted & (raster.source_triangle != face_ids)))
    paintable = regions.source_class != UNPAINTABLE
    deleted = int(np.count_nonzero(paintable & ~painted))
    painted_count = int(np.count_nonzero(painted))
    paintable_count = int(np.count_nonzero(paintable))
    return {
        "painted_pixels": painted_count,
        "phantom_pixels": phantom,
        "phantom_fraction": phantom / painted_count if painted_count else 0.0,
        "paintable_pixels": paintable_count,
        "deleted_pixels": deleted,
        "deleted_fraction": deleted / paintable_count if paintable_count else 0.0,
    }


def occlusion_budget(surface: FishnetSurface) -> dict[str, Any]:
    """What fraction of the projected support area occlusion removed, per site.

    The propagation stage treats a face as fully visible with its area scaled by
    ``face_visible_fraction``, with no sub-cell mask.  That is only defensible
    while the occluded share stays small, and how small it is depends on the
    site rather than on the cutter: an open square captured at pitch zero is the
    easy case, and a narrow street with scaffolding, street trees and parked
    vehicles is not.  So the budget is measured and reported per site instead of
    assumed.

    Every term is a share of the projected image area of the visible support
    triangles, which is exactly ``emitted_area_px + rejected_area_px``.

    * ``within_cell_fraction`` is what the sub-cell decision is actually about:
      the area accepted faces carry but do not own, summed as
      ``area * (1 - visible_fraction)``.
      ``solid_angle_weighted_visible_fraction`` is the same term in the form the
      propagation stage sees it.
    * ``absent_surface_fraction`` is projected area rejected whole with nothing
      downstream to put back: a mesh occluder, unmodelled clutter, or a
      registration conflict.
    * ``deferred_surface_fraction`` is projected area rejected whole and handed
      to another layer, which is people, vehicles and street furniture.
    * ``occlusion_budget_fraction`` is the three added together.

    The kept faces are a truncated sample, because a piece owning less than
    ``piece_visibility_fraction`` of its footprint is rejected rather than kept
    with a low visible fraction.  That threshold is reported alongside the
    budget so the truncation is not invisible, and it is why the whole-cell
    terms have to be added rather than the within-cell term read on its own.
    """
    corners = np.asarray(surface.face_image, dtype=np.float64)
    edge_a = corners[:, 1] - corners[:, 0]
    edge_b = corners[:, 2] - corners[:, 0]
    face_area_px = 0.5 * np.abs(edge_a[:, 0] * edge_b[:, 1] - edge_a[:, 1] * edge_b[:, 0])
    emitted_px = float(face_area_px.sum())
    within_cell_px = float((face_area_px * (1.0 - surface.face_visible_fraction)).sum())

    rejected_px = np.asarray(surface.rejected_image_area_px, dtype=np.float64)
    reasons = np.asarray(surface.rejected_reason, dtype=np.int64)
    by_reason = {
        name: float(rejected_px[reasons == code].sum()) for name, code in REJECTION_REASONS.items() if code in reasons
    }
    absent_px = float(sum(by_reason.get(name, 0.0) for name in ABSENT_SURFACE_REJECTIONS))
    deferred_px = float(sum(by_reason.get(name, 0.0) for name in DEFERRED_SURFACE_REJECTIONS))

    projected_px = emitted_px + float(rejected_px.sum())
    scale = 1.0 / projected_px if projected_px > 0.0 else 0.0
    solid_angle = np.asarray(surface.face_solid_angle_sr, dtype=np.float64)
    weighted = (
        float((solid_angle * surface.face_visible_fraction).sum() / solid_angle.sum())
        if solid_angle.sum() > 0.0
        else 0.0
    )
    return {
        "projected_source_area_px": projected_px,
        "within_cell_px": within_cell_px,
        "within_cell_fraction": within_cell_px * scale,
        "absent_surface_px": absent_px,
        "absent_surface_fraction": absent_px * scale,
        "deferred_surface_px": deferred_px,
        "deferred_surface_fraction": deferred_px * scale,
        "occlusion_budget_fraction": (within_cell_px + absent_px + deferred_px) * scale,
        "solid_angle_weighted_visible_fraction": weighted,
        "piece_visibility_fraction": float(surface.report.get("piece_visibility_fraction", float("nan"))),
        "by_reason_fraction": {name: area * scale for name, area in by_reason.items()},
    }


def aggregate_occlusion_budget(budgets: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine per-view budgets into the one number that describes a site.

    Areas are summed before the ratio is taken, so a crop that sees very little
    support surface cannot weigh as much as a crop that sees a facade.
    """
    if not budgets:
        raise ValueError("aggregating an occlusion budget needs at least one view")
    projected = sum(budget["projected_source_area_px"] for budget in budgets)
    within = sum(budget["within_cell_px"] for budget in budgets)
    absent = sum(budget["absent_surface_px"] for budget in budgets)
    deferred = sum(budget["deferred_surface_px"] for budget in budgets)
    scale = 1.0 / projected if projected > 0.0 else 0.0
    reasons: dict[str, float] = {}
    for budget in budgets:
        for name, fraction in budget["by_reason_fraction"].items():
            reasons[name] = reasons.get(name, 0.0) + fraction * budget["projected_source_area_px"]
    return {
        "views": len(budgets),
        "projected_source_area_px": projected,
        "within_cell_fraction": within * scale,
        "absent_surface_fraction": absent * scale,
        "deferred_surface_fraction": deferred * scale,
        "occlusion_budget_fraction": (within + absent + deferred) * scale,
        "piece_visibility_fraction": budgets[0]["piece_visibility_fraction"],
        "by_reason_fraction": {name: area * scale for name, area in sorted(reasons.items())},
    }


def angular_tolerance_deg(tolerance_px: float, view: PinholeView) -> float:
    """Worst-case angular error of a boundary displaced by ``tolerance_px``.

    The bound is taken at the image centre, where a rectilinear crop has its
    largest angular pixel pitch.  Boundaries towards the corners are sampled
    more finely in angle, so this is conservative for the whole crop.
    """
    if tolerance_px < 0.0:
        raise ValueError("tolerance_px must be non-negative")
    tangent_x, _tangent_y = view.tangents
    return math.degrees(math.atan(2.0 * tangent_x * tolerance_px / view.width))
