"""Local ENU projection for the study frame.

Re-exports the Transverse Mercator projection that ``EnvironmentMesh`` and
``parse_osm_xml`` use, so the city mesh, the building candidates, and the
pedestrian walks all share one origin and one frame. Do not introduce a second
projection here: a frame mismatch would silently misplace walks relative to the
mesh.
"""

from aegis.environment.geo import (
    transverse_mercator_forward as latlon_to_enu,
)
from aegis.environment.geo import (
    transverse_mercator_inverse as enu_to_latlon,
)

__all__ = ["latlon_to_enu", "enu_to_latlon"]
