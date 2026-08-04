"""Which company took the photograph, made into a choice rather than an accident.

The study reads panoramas from two providers and, until this module, no document
said so. Every single camera site is Google Street View. The twelve station
Korenmarkt walk, the only multi station set and the one carrying the SAM 3
material binding, is Mapillary. A reader of the old code could not tell, because
:mod:`semantic_twin.panorama` opened by calling itself Street View and the
Mapillary module had no counterpart to compare against.

The two are not interchangeable and the difference lands in the physics.

**Orientation.** Mapillary's structure from motion solves for gravity and
publishes the answer in ``computed_rotation``, so a Mapillary panorama arrives
with a measured tilt and roll. Street View publishes ``tilt`` and ``roll`` too,
but three of the five sites screened for this study reported exactly ``tilt=90``
and ``roll=0``, which is what a capture with no orientation solution looks like
rather than a levelled camera. Both implementations report which of the two they
have in :attr:`PanoramaPose.orientation_source`, and nothing downstream should
treat an assumed level camera as a measured one.

**Resolution.** A Street View car capture is 16384 by 8192. The Korenmarkt walk
panoramas are 5760 by 2880 provider originals. That is the leading suspect for
why walk stations register worse against the skyline, and any comparison across
the two arms has to carry it.

**Completeness.** Street View is asked for one panorama at a time by identifier.
Mapillary has a bounding box endpoint that silently returns a sample, so its
walks are assembled by sequence traversal instead. See
:mod:`semantic_twin.acquire.mapillary`.

:func:`source_for_site` reads the provider off :mod:`semantic_twin.sites`, which
already carries it per site and per imagery set. There is no second list here.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np

from .. import paths, sites


@dataclass(frozen=True)
class PanoramaPose:
    """One panorama camera in the configured geometry's local ENU frame.

    Neither provider supplies a camera altitude, so the initial z is the ground
    under this camera plus ``camera_height_m``. Skyline registration refines it
    before semantic projection.

    ``orientation_source`` exists because a missing orientation and a level
    camera look identical in the numbers. Both arrive as ``tilt_deg = 90`` and
    ``roll_deg = 0``, and every downstream consumer that treats them the same is
    trusting a default it was never given. ``provenance`` carries the altitude
    measurement so the number can be argued with rather than only believed.
    """

    position_enu_m: tuple[float, float, float]
    position_wgs84: tuple[float, float]
    heading_deg: float
    tilt_deg: float
    roll_deg: float
    camera_height_m: float
    altitude_source: str = "terrain_plus_camera_height"
    coordinate_frame: str = "ENU: x east, y north, z up"
    orientation_source: str = "unspecified"
    provenance: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class PanoramaSource(Protocol):
    """What both providers have to supply before a panorama can be used.

    Deliberately small. Everything a provider does that the other cannot is
    behind its own module, and this is only the part the reconstruction side
    depends on: where the camera was, how it was turned, and which of those two
    were measured rather than assumed.
    """

    #: The value :mod:`semantic_twin.sites` records for this provider.
    provider: str

    def image_id(self, metadata: dict[str, Any]) -> str:
        """The provider's own name for one panorama."""
        ...

    def orientation_source(self, metadata: dict[str, Any]) -> str:
        """Whether tilt and roll were measured, defaulted, or absent.

        A sentence rather than a flag, because the three cases are not a scale
        and the reason matters when a pose is later argued about.
        """
        ...

    def pose(
        self,
        metadata: dict[str, Any],
        scene: dict[str, Any],
        *,
        support_mesh: tuple[np.ndarray, np.ndarray] | None = None,
    ) -> PanoramaPose:
        """Initial camera pose in the scene's local ENU frame.

        Initial, not final. Both providers give a position good to a few metres
        and neither gives a camera altitude, so the skyline registration refines
        this before any pixel is bound to a triangle.
        """
        ...


def source_for(provider: str) -> PanoramaSource:
    """The implementation for one provider name.

    Names come from :mod:`semantic_twin.sites`, so a site config and a source
    cannot drift apart. Imports are deferred because the two implementations
    pull in Pillow and the geometry stack, and a caller that only wants to know
    which provider a site uses should not pay for either.
    """
    if provider == sites.GOOGLE_STREETVIEW:
        from .streetview import GoogleStreetView

        return GoogleStreetView()
    if provider == sites.MAPILLARY:
        from .mapillary import Mapillary

        return Mapillary()
    raise KeyError(f"{provider} is not a panorama provider: {sites.GOOGLE_STREETVIEW}, {sites.MAPILLARY}")


def source_for_site(site: str | sites.Site, role: str = "stations") -> PanoramaSource:
    """The provider behind one site's imagery of a given role.

    ``role`` is needed because a site can have more than one set and they need
    not share a provider. Korenmarkt is the case: its ``stations`` set is Street
    View, its ``walk`` and ``multiview`` sets are Mapillary, and the walk is the
    one that carries the material binding.
    """
    resolved = site if isinstance(site, sites.Site) else sites.Site.get(site)
    imagery = resolved.imagery_by_role(role)
    if not imagery:
        raise KeyError(f"{resolved.name} has no imagery with role {role!r}")
    providers = {entry.provider for entry in imagery}
    if len(providers) > 1:
        raise ValueError(f"{resolved.name} mixes providers within role {role!r}: {sorted(providers)}")
    return source_for(providers.pop())


def load_support_mesh(
    scene: dict[str, Any],
    *,
    root: pathlib.Path | None = None,
) -> tuple[np.ndarray, np.ndarray] | None:
    """The scene's traceable support mesh, when one exists.

    Returns None rather than raising, because a camera altitude measured under
    the camera is an improvement on the scene wide constant and not a
    precondition for having a pose at all. A fresh site has no mesh yet: the
    mesh has to exist before ``camera_ground_z_m`` can be measured, and the
    panorama step needs that constant before it can write a pose.
    """
    name = scene.get("name")
    crop_m = scene.get("geometry_selection", {}).get("crop_radius_m")
    if not name or crop_m is None:
        return None
    from ..scene.mesh import read_binary_ply

    try:
        resolved = paths.site_mesh(str(name), int(round(float(crop_m))), root_dir=root)
    except FileNotFoundError:
        return None
    return read_binary_ply(resolved)
