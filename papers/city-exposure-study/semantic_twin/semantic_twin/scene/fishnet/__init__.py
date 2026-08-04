"""Cut a support mesh at semantic class boundaries instead of tiling image space.

The projection path this replaced built an axis-aligned quadtree over the label
image and ray-splatted two triangles per leaf outward onto the support surface.
Every class boundary became a staircase of squares and flat facade paid for
triangles it did not need.

Four modules, in the order a crop passes through them.

* :mod:`.regions` reads the labels, decides which pixels may be projected at
  all, and groups the survivors into depth-continuous single-class islands. The
  cracks between islands are the boundary chains everything downstream cuts on.
* :mod:`.cut` projects each visible mesh triangle into the crop, intersects it
  with the local chains, and maps the pieces back onto the triangle's own plane.
* :mod:`.surface` is what comes out: triangles that carry their class, their
  material posterior, their solid angle and the pixels they were built from,
  plus the parallel table of what was rejected and why.
* :mod:`.audit` renders the result back into the image and measures what
  simplification and occlusion cost.

Nothing here imports ``bpy``. The Blender and rendering wrappers live in the
standalone scripts next to this package.
"""

from __future__ import annotations

from .audit import (
    ABSENT_SURFACE_REJECTIONS,
    DEFERRED_SURFACE_REJECTIONS,
    OCCLUSION_REJECTIONS,
    aggregate_occlusion_budget,
    angular_tolerance_deg,
    class_fidelity,
    occlusion_budget,
    occlusion_fidelity,
    rasterize_fishnet,
)
from .cut import CutLimits, build_fishnet
from .regions import PAINT_REASONS, UNPAINTABLE, RegionMap, boundary_chains, build_region_map, paintability
from .surface import REJECTION_REASONS, FishnetRaster, FishnetSurface, load_fishnet, save_fishnet

__all__ = [
    "ABSENT_SURFACE_REJECTIONS",
    "DEFERRED_SURFACE_REJECTIONS",
    "OCCLUSION_REJECTIONS",
    "PAINT_REASONS",
    "REJECTION_REASONS",
    "UNPAINTABLE",
    "CutLimits",
    "FishnetRaster",
    "FishnetSurface",
    "RegionMap",
    "aggregate_occlusion_budget",
    "angular_tolerance_deg",
    "boundary_chains",
    "build_fishnet",
    "build_region_map",
    "class_fidelity",
    "load_fishnet",
    "occlusion_budget",
    "occlusion_fidelity",
    "paintability",
    "rasterize_fishnet",
    "save_fishnet",
]
