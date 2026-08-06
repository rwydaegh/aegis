"""The eleven squares, read from ``config/`` instead of retyped.

The list of sites appears as a literal in seven files and disagrees with itself
in four different orderings. Six more files carry a subset, and six carry a table
of display names, of which no two agree on what to call Prague. None of them read
``config/``, which has had one JSON per city all along.

This module is the one place that knows there are eleven. Everything a caller
used to hardcode is a field or a method here: the crop radii a site has a mesh
for, whose photographs it was built from, where its evidence sits, and what it is
called in a figure caption.

Two facts the old literals encoded by accident, now recorded on purpose.

**Milan has no 130 m build.** Its smallest mesh is 170 m, because the cathedral's
109 m spire needs a wider acquisition ball than the other ten. That is why it
sits ninth in the study's own site order rather than seventh alphabetically: it
joins a cross city sweep only at 250 m. It is now ``130 not in site.crops`` and
no caller needs a branch for it.

**Two imagery providers are in use and nothing said so.** Every single panorama
site is Google Street View. The twelve station Korenmarkt walk, the only multi
station set and the one carrying the SAM 3 binding, is Mapillary. That was an
undocumented accident. It is :attr:`Site.imagery` now.
"""

from __future__ import annotations

import functools
import json
from dataclasses import dataclass
from typing import Any

from . import paths
from .scene.enu import EnuFrame

#: Panorama providers the study pulls from.
GOOGLE_STREETVIEW = "google_streetview"
MAPILLARY = "mapillary"

#: Keys ``semantic_twin.scene.load_scene`` insists on. A file in ``config/``
#: carrying all four is a site, and one that does not is a lookup table. That is
#: how ``itu_p2040_4.json`` and ``showcase.json`` stay out of the site registry
#: without being named in a skip list that would go stale.
SITE_CONFIG_KEYS = frozenset({"name", "location", "enu_origin", "camera_ground_z_m"})

#: The site order the study reports in, which is not alphabetical.
#:
#: Milan sits ninth because it was acquired first, before the crop radius settled,
#: and has no 130 m mesh. Three files carry this exact order and one of them says
#: outright that it is "the study's, not alphabetical". Three more files sort
#: alphabetically and one puts Korenmarkt first, but none of those three give a
#: reason, and the cross city figure that the paper prints uses this one. So this
#: is canonical and the others are re-sorts of it.
STUDY_ORDER: tuple[str, ...] = (
    "brussels_grandplace",
    "korenmarkt",
    "krakow_rynek",
    "london_trafalgar",
    "madrid_plazamayor",
    "mexico_zocalo",
    "newyork_timessquare",
    "prague_staromestske",
    "milan_duomo",
    "tokyo_hachiko",
    "toulouse_capitole",
)


@dataclass(frozen=True)
class ImagerySet:
    """One captured set of panoramas belonging to a site.

    A site can have more than one. Korenmarkt has three, taken by two providers
    on two occasions, and which of them a run used decides what the material
    binding is worth. Carrying them as records rather than as a directory naming
    convention is what lets a manifest say where its photographs came from.
    """

    provider: str
    directory: str
    #: Prefix of the per camera subdirectory names. Empty for the two sites
    #: acquired before the multi camera fetcher, whose single camera's files sit
    #: directly in the set directory.
    station_prefix: str
    #: What the set is for. ``stations`` is the site's own spread of cameras,
    #: ``walk`` is a connected chain along a street, ``multiview`` is a small
    #: cluster kept for reconstruction rather than for coverage.
    role: str


@dataclass(frozen=True)
class Naming:
    """The four naming facts every label in the study is built from.

    Six display schemes exist across the figure scripts and they disagree. They
    are not six facts, they are four facts rendered six ways, so the facts are
    stored and the renderings are derived. :meth:`Site.title`, :meth:`Site.label`
    and :meth:`Site.pretty` reproduce three of the six exactly, and the two that
    they do not reproduce are figure specific abbreviations.
    """

    square: str
    #: The square's name cut to one word where one word is unambiguous, for a
    #: crowded axis. "Rynek" rather than "Rynek Glowny".
    short: str
    city: str
    country: str


#: Square, short name, city and country per site.
#:
#: ``square`` and ``country`` are the values ``screen_cities.py`` put forward when
#: the site was proposed, so they are the study's own first statement of what each
#: place is called. ``city`` is not derivable from ``country``, since Hachiko is in
#: Tokyo and not in Japan-the-city, so it is stored. ``short`` is the axis label the
#: multipath figure uses, with Times Square kept whole: two figures write "Times
#: Square" and one writes "Times Sq", and squeezing a name to fit an axis is the
#: figure's business rather than the site's.
NAMES: dict[str, Naming] = {
    "brussels_grandplace": Naming("Grand-Place", "Grand-Place", "Brussels", "Belgium"),
    "korenmarkt": Naming("Korenmarkt", "Korenmarkt", "Ghent", "Belgium"),
    "krakow_rynek": Naming("Rynek Glowny", "Rynek", "Krakow", "Poland"),
    "london_trafalgar": Naming("Trafalgar Square", "Trafalgar", "London", "United Kingdom"),
    "madrid_plazamayor": Naming("Plaza Mayor", "Plaza Mayor", "Madrid", "Spain"),
    "mexico_zocalo": Naming("Plaza de la Constitucion", "Zocalo", "Mexico City", "Mexico"),
    "milan_duomo": Naming("Piazza del Duomo", "Duomo", "Milan", "Italy"),
    "newyork_timessquare": Naming("Times Square", "Times Square", "New York", "United States"),
    "prague_staromestske": Naming("Staromestske namesti", "Staromestske", "Prague", "Czechia"),
    "tokyo_hachiko": Naming("Hachiko square, Shibuya", "Hachiko", "Tokyo", "Japan"),
    "toulouse_capitole": Naming("Place du Capitole", "Capitole", "Toulouse", "France"),
}

#: Which photographs each site was built from.
#:
#: Read off the disk and then written down, because the disk says it in metadata
#: keys rather than in directory names: a Street View camera's ``metadata.json``
#: carries ``panoId`` and a Mapillary one carries ``sequence``. Krakow and
#: Toulouse have no panoramas at all, which is why they carry no image evidence
#: anywhere in the study and why four of the six subset literals leave them out.
IMAGERY: dict[str, tuple[ImagerySet, ...]] = {
    "brussels_grandplace": (ImagerySet(GOOGLE_STREETVIEW, "brussels_grandplace", "pano_", "stations"),),
    "korenmarkt": (
        ImagerySet(GOOGLE_STREETVIEW, "korenmarkt", "", "stations"),
        ImagerySet(MAPILLARY, "korenmarkt_walk", "walk_", "walk"),
        ImagerySet(MAPILLARY, "korenmarkt_mapillary", "view_", "multiview"),
    ),
    "krakow_rynek": (),
    "london_trafalgar": (ImagerySet(GOOGLE_STREETVIEW, "london_trafalgar", "pano_", "stations"),),
    "madrid_plazamayor": (ImagerySet(GOOGLE_STREETVIEW, "madrid_plazamayor", "pano_", "stations"),),
    "mexico_zocalo": (ImagerySet(GOOGLE_STREETVIEW, "mexico_zocalo", "pano_", "stations"),),
    "milan_duomo": (ImagerySet(GOOGLE_STREETVIEW, "milan_duomo", "", "stations"),),
    "newyork_timessquare": (ImagerySet(GOOGLE_STREETVIEW, "newyork_timessquare", "pano_", "stations"),),
    "prague_staromestske": (ImagerySet(GOOGLE_STREETVIEW, "prague_staromestske", "pano_", "stations"),),
    "tokyo_hachiko": (ImagerySet(GOOGLE_STREETVIEW, "tokyo_hachiko", "pano_", "stations"),),
    "toulouse_capitole": (),
}


@dataclass(frozen=True)
class Site:
    """One city square, with everything a run needs to know about it.

    Two kinds of fact live here and they age differently, so the policy is
    written down rather than left to whoever reads the code next.

    The config fields are loaded once and held for the process. A site's anchor
    and datum do not change under a running sweep, and eleven JSON reads per call
    would be paid by every caller.

    The disk-derived answers are read when asked. :attr:`crops` goes through
    :func:`semantic_twin.paths.mesh_crops`, which caches, because it is a
    directory listing behind a property and properties get used inside loops.
    :meth:`has_fishnet` and :meth:`station_binding` do not cache, because they
    cost one ``is_dir`` and a short-circuiting glob and a build script wants the
    truth. Either way :func:`reload` is the way back to the disk.
    """

    name: str
    naming: Naming
    imagery: tuple[ImagerySet, ...]
    lat: float
    lon: float
    #: The half width of the square the site stands for, from the config. Not the
    #: crop radius, which is how much surrounding geometry a run carries.
    radius_m: float
    enu_origin: tuple[float, float, float]
    #: Pavement height under the site's panorama camera, in the mesh's own ENU
    #: frame. Used as a cross check on the datum a run measures from the mesh, and
    #: never as the datum itself. Whether it came from a skyline registration or
    #: from a patch of tile surfaces is recorded in :attr:`ground_datum_note`.
    camera_ground_z_m: float
    camera_height_m: float
    frequencies_hz: tuple[float, ...]
    extrapolated_frequencies_hz: tuple[float, ...]
    #: The crop radius the site was first built at, from the config. Milan is the
    #: only site where this is not 130 m.
    built_crop_m: float
    #: Radius of the tile request ball. Larger than the crop, and much larger at
    #: Milan, because the ball is centred on the ellipsoid rather than on the
    #: terrain and a high site loses horizontal reach to its own altitude.
    acquisition_radius_m: float
    #: The whole config document, so a field nobody has needed yet is still there.
    document: dict[str, Any]

    # ---------------------------------------------------------------- naming

    @property
    def square(self) -> str:
        return self.naming.square

    @property
    def city(self) -> str:
        return self.naming.city

    @property
    def country(self) -> str:
        return self.naming.country

    @property
    def short(self) -> str:
        """One word where one word is unambiguous. For a crowded axis."""
        return self.naming.short

    @property
    def title(self) -> str:
        """Square then city, as the gallery and the city sheet write it."""
        return f"{self.naming.square}, {self.naming.city}"

    @property
    def label(self) -> str:
        """The city alone, as the law ordering table writes it."""
        return self.naming.city

    @property
    def pretty(self) -> str:
        """City then short square, as the eleven city exposure figure writes it."""
        return f"{self.naming.city} {self.naming.short}"

    @property
    def ground_datum_note(self) -> str | None:
        """How :attr:`camera_ground_z_m` was arrived at, where the config says.

        Absent on the two sites whose value came out of a panorama registration
        with nothing surprising about it, present on the rest, and worth reading
        before quoting the number: Milan's says outright that one scene wide
        constant is a known weakness and that a camera on the cathedral steps
        would inherit a biased altitude.
        """
        note = self.document.get("camera_ground_z_note")
        return str(note) if note else None

    # ---------------------------------------------------------------- geometry

    @property
    def config_path(self):
        return paths.site_config(self.name)

    @property
    def crops(self) -> tuple[int, ...]:
        """Crop radii in metres this site has an acceptable mesh for, ascending."""
        return paths.mesh_crops(self.name)

    def has_crop(self, crop_m: int) -> bool:
        return crop_m in self.crops

    def mesh(self, crop_m: int):
        """The support mesh at one crop radius, raising when there is none.

        Not :attr:`document`'s ``source_mesh``. That key names the unsuffixed file
        at every site, and at Korenmarkt and Milan the unsuffixed file is the
        version 2 build that ``paths.site_mesh`` refuses. The key is a record of
        what the acquisition wrote and this is what a run traces, and where the
        two disagree this one is right.
        """
        return paths.site_mesh(self.name, crop_m)

    def frame(self) -> EnuFrame:
        """The local metric frame the mesh and every walk are expressed in.

        Built from ``enu_origin`` rather than from ``location``. The two agree at
        every site today, and they are separate fields because the anchor a mesh
        was aligned to must not move when the screening centre is nudged.
        """
        return EnuFrame(*self.enu_origin)

    # ---------------------------------------------------------------- evidence

    @property
    def has_panoramas(self) -> bool:
        return bool(self.imagery)

    def imagery_by_role(self, role: str) -> tuple[ImagerySet, ...]:
        return tuple(entry for entry in self.imagery if entry.role == role)

    def stations(self, role: str = "stations"):
        """The camera directories of one imagery set, in name order."""
        found: list = []
        for entry in self.imagery_by_role(role):
            found.extend(paths.panorama_stations(entry.directory, entry.station_prefix))
        return tuple(found)

    def registered_stations(self, role: str = "stations"):
        """The cameras that solved for a pose against the skyline.

        Having a photograph and having a usable one are different facts, and the
        gap is wide. London has fifteen panoramas on disk and not one registered
        pose, which is why it drops out of every evidence list even though it
        drops out of no imagery list. This predicate is what those lists were
        written by hand to express.
        """
        return tuple(path for path in self.stations(role) if paths.panorama_pose(path).exists())

    @property
    def has_registered_stations(self) -> bool:
        return bool(self.registered_stations())

    def fishnet_dir(self, crop_m: int):
        """Where this site's cut surfaces live at one crop radius.

        The first build went to a directory with no radius in its name. That is a
        130 m cut everywhere and a 170 m cut at Milan, which is exactly why this
        belongs on the site and not in a path helper.
        """
        return paths.fishnet_dir(self.name, None if crop_m == int(self.built_crop_m) else crop_m)

    def has_fishnet(self, crop_m: int) -> bool:
        """True when cut surfaces exist here and sit where a binder can find them.

        A binder globs the top of the directory and does not recurse, so a site
        whose surfaces were written one folder per camera has a directory full of
        evidence and nothing bindable. Both of those are false here, and they need
        opposite fixes, so a caller that gets False should look before rebuilding.
        """
        directory = self.fishnet_dir(crop_m)
        return directory.is_dir() and any(directory.glob("*_fishnet.npz"))

    def station_binding(self, crop_m: int):
        """The fused station binding at one crop radius, or None.

        Korenmarkt keeps its Mapillary built walk binding at its first crop, which
        is what every published walk number was measured on, and falls through to
        its Street View binding at any other radius.
        """
        if self.name == "korenmarkt" and crop_m == 130:
            walk = paths.walk_semantics()
            if walk.exists():
                return walk
        path = paths.site_semantics(self.name, crop_m)
        return path if path.exists() else None

    def has_station_binding(self, crop_m: int) -> bool:
        return self.station_binding(crop_m) is not None

    # ---------------------------------------------------------------- registry

    @staticmethod
    def all() -> tuple[Site, ...]:
        """The eleven, in the study's own order."""
        return _registry()

    @staticmethod
    def names() -> tuple[str, ...]:
        return tuple(site.name for site in _registry())

    @staticmethod
    def get(name: str) -> Site:
        for site in _registry():
            if site.name == name:
                return site
        raise KeyError(f"{name} is not one of the {len(_registry())} sites: {', '.join(Site.names())}")


def with_mesh(crop_m: int) -> tuple[Site, ...]:
    """Sites a cross city sweep can run at one crop radius.

    This is the gate the sweep already applies and never wrote down: a site enters
    only if it has a mesh at the run's radius, so the geometry stays comparable
    across the set. At 130 m it drops Milan and at 250 m it drops nobody.
    """
    return tuple(site for site in _registry() if site.has_crop(crop_m))


def with_fishnet(crop_m: int) -> tuple[Site, ...]:
    """Sites whose cut surfaces are on disk and bindable at one crop radius."""
    return tuple(site for site in _registry() if site.has_fishnet(crop_m))


def with_station_binding(crop_m: int) -> tuple[Site, ...]:
    """Sites whose registered cameras fused into a surface binding.

    Smaller than :func:`with_fishnet`, because cutting surfaces needs one admitted
    camera and fusing them into a binding needs enough of them to agree.
    """
    return tuple(site for site in _registry() if site.has_station_binding(crop_m))


def with_panoramas() -> tuple[Site, ...]:
    """Sites that have photographs at all. Nine of eleven."""
    return tuple(site for site in _registry() if site.has_panoramas)


def with_registered_stations() -> tuple[Site, ...]:
    """Sites with at least one camera that solved for a pose. Eight of eleven.

    This is the set the fishnet builder was given as a literal, and the reason
    London is missing from it while it is present in :func:`with_panoramas`.
    """
    return tuple(site for site in _registry() if site.has_registered_stations)


def config_names() -> tuple[str, ...]:
    """Every site config in ``config/``, by stem, sorted.

    A file counts as a site config when it carries the four keys the scene loader
    insists on, which keeps the material and vegetation tables out without a skip
    list. Used to check the registry against the directory rather than trusting
    either one alone.
    """
    found: list[str] = []
    for path in sorted(paths.config_dir().glob("*.json")):
        try:
            document = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(document, dict) and SITE_CONFIG_KEYS <= document.keys():
            found.append(path.stem)
    return tuple(found)


def reload() -> None:
    """Read the registry and the disk again on the next question.

    The registry is cached for the life of the process, which is right and which
    also means a test that points :func:`semantic_twin.paths.config_dir` at a
    fixture tree leaves the real eleven cached behind it for everything that runs
    afterwards. There was no way to say so. This is it, and it clears the path
    module's disk caches with it, because a registry rebuilt against a different
    ``config/`` must not answer about the old ``data/``.
    """
    _registry.cache_clear()
    paths.forget_disk_reads()


@functools.lru_cache(maxsize=1)
def _registry() -> tuple[Site, ...]:
    """Load and cache the eleven. Eleven small JSON reads, done once."""
    return tuple(_load(name) for name in STUDY_ORDER)


def _load(name: str) -> Site:
    document = json.loads(paths.site_config(name).read_text())
    location = document["location"]
    origin = document["enu_origin"]
    geometry = document.get("geometry_selection", {})
    return Site(
        name=name,
        naming=NAMES[name],
        imagery=IMAGERY[name],
        lat=float(location["lat"]),
        lon=float(location["lon"]),
        radius_m=float(location["radius_m"]),
        enu_origin=(
            float(origin["lat"]),
            float(origin["lon"]),
            float(origin.get("ellipsoid_height_m", 0.0)),
        ),
        camera_ground_z_m=float(document["camera_ground_z_m"]),
        camera_height_m=float(document["camera_height_m"]),
        frequencies_hz=tuple(float(value) for value in document.get("frequencies_hz", ())),
        extrapolated_frequencies_hz=tuple(float(value) for value in document.get("extrapolated_frequencies_hz", ())),
        built_crop_m=float(geometry.get("crop_radius_m", 130.0)),
        acquisition_radius_m=float(geometry.get("acquisition_radius_m", 0.0)),
        document=document,
    )
