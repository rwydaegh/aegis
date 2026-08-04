"""Everything in the study that talks to somebody else's server.

Four services sit behind this package: Google Photorealistic 3D Tiles for the
geometry, Google Street View and Mapillary for the photographs, and Google
Routes for the walking path. They were spread over a package module, a
propagation module and three top level scripts, which is why two of them
disagreed about how a cached thing is named and why nothing recorded that the
study reads its imagery from two different companies.

Three rules hold across the package.

**One cache policy.** A cached thing is named by what it is, never by where it
came from. :mod:`~semantic_twin.acquire.cache` is the only place that decides
this.

**Providers are a choice, not an accident.**
:class:`~semantic_twin.acquire.source.PanoramaSource` is the interface, and
:mod:`semantic_twin.sites` says which site uses which.

**A sampled endpoint may not be used for selection.** Mapillary's bounding box
query returns an undeclared sample of the imagery in the box, measured here at
2 frames of 13. :mod:`~semantic_twin.acquire.mapillary` allows it to name
sequences and refuses to let it return image records.

Only the interface is re-exported here. The four service modules are not, and
:func:`~semantic_twin.acquire.source.source_for` reaches them through a deferred
import, because each one pulls in Pillow or the geometry stack and a caller that
only wants to know which provider a site uses should pay for neither.
"""

from __future__ import annotations

from .source import PanoramaPose, PanoramaSource, load_support_mesh, source_for, source_for_site

__all__ = [
    "PanoramaPose",
    "PanoramaSource",
    "load_support_mesh",
    "source_for",
    "source_for_site",
]
