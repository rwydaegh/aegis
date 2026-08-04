"""Shared pieces of the source construction measurements.

`measure_source_thickness.py`, `measure_source_construction.py`,
`measure_source_silhouette.py` and `measure_source_near_share.py` compare ways of
placing base station sites on a mesh. The comparison is only worth reading if
every one of them runs through the same estimator.

The estimator and the silhouette cloud now live in
`semantic_twin.illumination.sources`, because the tracer uses them too and one
copy is better than two. They are re-exported here so the scripts read the way
they did.
"""

from __future__ import annotations

from semantic_twin.illumination.sources import direct_from_sites, silhouette_cloud

__all__ = ["direct_from_sites", "silhouette_cloud"]
