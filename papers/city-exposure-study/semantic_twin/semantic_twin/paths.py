"""Every filesystem path in the study, in one place.

Thirty files currently open with ``ROOT = pathlib.Path(__file__).resolve().parent``
in five different spellings under three different variable names, then hand build
their own output paths. That is fine until two of them disagree, which has already
happened: there are thirteen copies of "find the mesh for this site" following four
different rules, and one of them silently returns a path that does not exist.

The layout described here was read off the disk, not designed. Where the disk is
irregular, the irregularity is recorded in a docstring rather than smoothed over,
because the irregularities are load bearing. Three examples, all real:

* Milan has no 130 m mesh. Its smallest build is 170 m, and its bare fishnet
  directory was cut against that 170 m mesh while every other site's bare fishnet
  directory was cut against a 130 m one.
* Times Square has no ``_f64`` file at any crop radius. A rule that requires the
  suffix drops it, and once dropped it took Prague with it.
* ``outputs/exposure_korenmarkt`` holds all eleven cities.

This module knows about directories and file names. It does not know that there
are eleven sites, which crops each one has, or what a site is called in a figure
caption. That is :mod:`semantic_twin.sites`, which imports this and not the other
way round.
"""

from __future__ import annotations

import functools
import json
import os
import pathlib
from dataclasses import dataclass

#: Filename stem shared by every support mesh. ``inhouse`` was the working name
#: for the Google Photorealistic 3D Tiles feed, and 79 files on disk still carry
#: it, so the string cannot change until those files are renamed. The constant is
#: named for the provider so that reading the code tells you whose tiles these
#: are without having to know the history.
#:
#: This is not yet the single point of control it should be. The same name is
#: spelled out in every ``config/*.json`` under ``source_mesh``, and in two
#: fishnet manifests under ``fishnet_source_mesh``. Those spellings are records of
#: what was built and they are not resolvers: every config names the unsuffixed
#: file, which at Korenmarkt and Milan is the version 2 build that
#: :func:`site_mesh` exists to refuse. So the ruling is that ``source_mesh`` is
#: acquisition provenance and :func:`site_mesh` is the answer to "which mesh does
#: this run trace". ``tests/test_sites.py`` pins the two sites where they differ.
GOOGLE_MESH_STEM = "inhouse_leaf"

#: Mesh builds below this are refused. Version 2 read tile placement back through
#: Blender in single precision and carries up to a metre of seaming along tile
#: boundaries. Korenmarkt has both a version 2 build and a ``_f64`` rebuild at
#: 130 m, so the version has to be read rather than guessed from the file name.
MIN_MESH_FORMAT_VERSION = 3

#: The exposure runs used to be written here, under a directory named for the
#: first city that ever wrote to it. All eleven are in there. New runs go to
#: :func:`exposure_dir`, and :func:`exposure_file` reads from both so that no
#: published output has to move for a caller to be rewired.
LEGACY_EXPOSURE_DIRNAME = "exposure_korenmarkt"

#: The six files one exposure run writes on a single stem.
EXPOSURE_SUFFIXES = ("_locations.jsonl", "_manifest.json", "_summary.json", "_spectra.npz", "_cdf.png", "_cdf.pdf")


def root() -> pathlib.Path:
    """The study directory, the one holding ``config/``, ``data/`` and ``outputs/``.

    The package sits one level inside it and shares its name, so ``parents[1]``
    from this file is the study and ``parents[0]`` is the package. Everything
    else here is relative to this, which is what lets the study be checked out
    anywhere.
    """
    return pathlib.Path(__file__).resolve().parents[1]


def config_dir() -> pathlib.Path:
    return root() / "config"


def data_dir() -> pathlib.Path:
    return root() / "data"


def aegis_data_dir() -> pathlib.Path:
    """Resolve AEGIS phantom data without assuming one checkout location."""
    override = os.environ.get("AEGIS_DATA_DIR")
    if override is not None:
        if not override.strip():
            raise ValueError("AEGIS_DATA_DIR is set but empty")
        return pathlib.Path(override).expanduser().resolve()
    for parent in (root(), *root().parents):
        candidate = parent / "data"
        if (parent / "pyproject.toml").is_file() and (candidate / "phantoms.yaml").is_file():
            return candidate.resolve()
    raise FileNotFoundError("could not find the AEGIS data directory containing phantoms.yaml")


def outputs_dir() -> pathlib.Path:
    return root() / "outputs"


def site_config(site: str) -> pathlib.Path:
    """The scene JSON for one site. Its stem is the site name everywhere."""
    return config_dir() / f"{site}.json"


def output(kind: str, *parts: str) -> pathlib.Path:
    """A path under ``outputs/<kind>/``, for the study directories that are one per topic.

    ``kind`` is the name of the study, not of a site: ``next_event``, ``skyline``,
    ``station_calibration``, ``crop_convergence``. The per site directories are
    reached through their own functions below, because their names encode a crop
    radius and that encoding is not uniform.
    """
    return outputs_dir().joinpath(kind, *parts)


# ------------------------------------------------------------------ geometry


def geometry_dir(site: str, root_dir: pathlib.Path | None = None) -> pathlib.Path:
    """Where one site's meshes live.

    ``root_dir`` overrides the study root. It is there because the acquisition
    code builds fixture sites under a temporary directory and used to reach them
    by rebuilding the file name itself, which is how the study ended up with two
    mesh resolvers that answer differently.
    """
    return (root_dir or root()) / "data" / "geometry" / site


def site_mesh(site: str, crop_m: int, root_dir: pathlib.Path | None = None) -> pathlib.Path:
    """The support mesh for one site at one crop radius. The only resolver.

    Prefers the ``_f64`` rebuild and falls back to the unsuffixed file, then
    reads ``format_version`` out of the sidecar manifest and refuses anything
    below :data:`MIN_MESH_FORMAT_VERSION`. Both halves matter. Times Square has
    no ``_f64`` file at all and its plain build is already version 3, so a rule
    that insists on the suffix loses a city. Korenmarkt has a version 2 file at
    130 m sitting beside its ``_f64`` rebuild, so a rule that only looks at names
    picks up a mesh with a metre of seaming in it.

    Raises rather than returning a path that does not exist, and the message says
    what was wrong with each candidate rather than naming one guess at the reason.
    Someone reading it at hour two of a sweep needs to know whether to rebuild a
    mesh, rebuild a sidecar or fix a crop radius, and those look identical from
    "no double precision mesh".
    """
    directory = geometry_dir(site, root_dir)
    refused: list[str] = []
    for name in (f"{GOOGLE_MESH_STEM}_{crop_m}m_f64.ply", f"{GOOGLE_MESH_STEM}_{crop_m}m.ply"):
        build = _mesh_build(directory / name)
        if build.usable:
            return directory / name
        refused.append(f"{name} ({build.reason})")
    raise FileNotFoundError(f"no traceable {crop_m} m mesh for {site} in {directory}: {', '.join(refused)}")


def mesh_manifest(mesh: pathlib.Path) -> pathlib.Path:
    """The sidecar JSON beside a mesh, carrying its format version and alignment."""
    return mesh.with_suffix(".json")


@functools.lru_cache(maxsize=64)
def mesh_crops(site: str) -> tuple[int, ...]:
    """Crop radii in metres this site has an acceptable mesh for, ascending.

    Measured from the disk rather than declared, because the set is genuinely
    ragged: Korenmarkt has six, most sites have two, and Milan's two do not
    include the 130 m that every other site leads with.

    Cached because it is a directory listing and it is asked eleven times per
    cross city gate, from a property. :func:`forget_disk_reads` is the one way
    back to the disk.
    """
    found: set[int] = set()
    for path in geometry_dir(site).glob(f"{GOOGLE_MESH_STEM}_*m*.ply"):
        crop = _crop_from_mesh_name(path.name)
        if crop is not None and _mesh_build(path).usable:
            found.add(crop)
    return tuple(sorted(found))


def _crop_from_mesh_name(name: str) -> int | None:
    """The crop radius encoded in a mesh file name, or None if it is not one."""
    stem = name.removesuffix(".ply").removesuffix("_f64")
    prefix = f"{GOOGLE_MESH_STEM}_"
    if not stem.startswith(prefix) or not stem.endswith("m"):
        return None
    digits = stem[len(prefix) : -1]
    return int(digits) if digits.isdigit() else None


@dataclass(frozen=True)
class MeshBuild:
    """Whether one mesh file may be traced, and when it may not, why not.

    Zero used to be the answer to four different questions: the mesh is not
    there, the sidecar is not there, the sidecar is not readable, and the build
    is version 2. Each needs a different fix and the caller was told the same
    thing for all four. :func:`fishnet_manifest` already makes this argument a few
    lines down, so the reason travels with the verdict here too.
    """

    version: int
    #: Empty when the build is usable. Otherwise one clause, ready to be joined
    #: into an error message beside the file name it belongs to.
    reason: str

    @property
    def usable(self) -> bool:
        return self.version >= MIN_MESH_FORMAT_VERSION


@functools.lru_cache(maxsize=256)
def _mesh_build(path: pathlib.Path) -> MeshBuild:
    """Read one mesh's sidecar and say whether the study will trace it.

    Cached because :func:`mesh_crops` reads every manifest in a site directory
    and cross site sweeps call it once per site per run. Cache the verdict and
    not the manifest, so nothing large is held. A script that writes a mesh and
    then verifies it in the same process has to call :func:`forget_disk_reads`
    first, or it reads back the answer from before it wrote.
    """
    manifest = mesh_manifest(path)
    if not path.exists():
        return MeshBuild(0, "no such mesh")
    if not manifest.exists():
        return MeshBuild(0, f"no sidecar {manifest.name} beside it")
    try:
        version = int(json.loads(manifest.read_text()).get("format_version", 0))
    except (json.JSONDecodeError, TypeError, ValueError):
        return MeshBuild(0, f"{manifest.name} carries no readable format_version")
    if version < MIN_MESH_FORMAT_VERSION:
        return MeshBuild(version, f"format_version {version}, below {MIN_MESH_FORMAT_VERSION}")
    return MeshBuild(version, "")


def forget_disk_reads() -> None:
    """Drop every cached answer about what is on disk. The one invalidation point.

    Two answers are held for the life of the process: a mesh build's format
    version and the crop radii a site has a mesh for. That is right for a sweep
    asking eleven sites the same question and wrong for a script that builds a
    mesh and then verifies it, so the script that does both calls this in
    between. :func:`semantic_twin.sites.reload` calls it too, because a registry
    rebuilt against a different ``config/`` must not carry the old disk with it.
    """
    _mesh_build.cache_clear()
    mesh_crops.cache_clear()


# ----------------------------------------------------------------- imagery


def panoramas_dir() -> pathlib.Path:
    return data_dir() / "panoramas"


def panorama_set(name: str) -> pathlib.Path:
    """One captured set of panoramas.

    ``name`` is a directory name and not always a site name. Korenmarkt has three
    sets: its Street View capture under ``korenmarkt``, its twelve station
    Mapillary walk under ``korenmarkt_walk``, and the three view Mapillary
    reconstruction set under ``korenmarkt_mapillary``. Which set belongs to which
    site, and who took it, is recorded on :class:`semantic_twin.sites.Site`.
    """
    return panoramas_dir() / name


def panorama_stations(name: str, prefix: str = "") -> tuple[pathlib.Path, ...]:
    """The camera directories in one set, in name order.

    Two layouts are on disk and both are current. The nine sites fetched by
    ``fetch_site_panoramas.py`` have one subdirectory per camera, named for the
    prefix and the provider's own image identifier. Korenmarkt and Milan were
    acquired before that script and put their single camera's files directly in
    the set directory, so an empty prefix returns the set directory itself when
    it carries a ``semantics/`` folder.
    """
    directory = panorama_set(name)
    if not directory.is_dir():
        return ()
    if prefix:
        return tuple(sorted(path for path in directory.glob(f"{prefix}*") if path.is_dir()))
    return (directory,) if (directory / "semantics").is_dir() else ()


def panorama_semantics(station: pathlib.Path) -> pathlib.Path:
    """The segmentation written beside one camera."""
    return station / "semantics" / "semantics.json"


def panorama_pose(station: pathlib.Path) -> pathlib.Path:
    """The skyline registered pose, which is the one a station is admitted on."""
    return station / "alignment" / "pose_aligned.json"


def tiles_dir(name: str, *, wide: bool = False) -> pathlib.Path:
    """The Google 3D Tiles cache for one acquisition.

    Two roots exist because the crop radius grew. ``data/tiles`` holds the
    original pulls and ``data/tiles250`` the wider ones, and the split is by
    acquisition rather than by site: eight sites have a wide pull, Korenmarkt's
    wide pull is filed under the name ``korenmarkt_340m`` in the narrow root, and
    ``data/tiles`` also holds Istanbul, which was screened and rejected.
    """
    return data_dir() / ("tiles250" if wide else "tiles") / name


def street_routes_dir() -> pathlib.Path:
    return data_dir() / "street_routes"


def street_route(site: str, request_key: str) -> pathlib.Path:
    """One cached Google Routes reply.

    The key is a digest of the waypoints and the optimisation flag, so the same
    request never gets asked twice and two different requests for one site never
    collide.
    """
    return street_routes_dir() / f"{site}_{request_key}.json"


def street_routes(site: str) -> tuple[pathlib.Path, ...]:
    """Every cached route reply for a site, in name order."""
    directory = street_routes_dir()
    return tuple(sorted(directory.glob(f"{site}_*.json"))) if directory.is_dir() else ()


# ------------------------------------------------------ derived evidence


def fishnet_dir(site: str, crop_m: int | None = None) -> pathlib.Path:
    """Where a site's cut fishnet surfaces live.

    ``crop_m`` of None means the site's first build, which is written to the bare
    directory. That is a 130 m cut everywhere except Milan, whose bare directory
    holds a 170 m cut, so the caller that knows the site's first crop radius is
    the one that decides. :meth:`semantic_twin.sites.Site.fishnet_dir` does it.

    A fishnet is only valid against the exact mesh it was cut against, because
    the binding is indexed by triangle with no join key. The mesh is named in the
    directory's own manifest, which is what :func:`fishnet_manifest` reads, and
    that name is the authority rather than the crop radius of the run.
    """
    suffix = "" if crop_m is None else f"_{crop_m}m"
    return outputs_dir() / f"{site}_fishnet_vistas{suffix}"


def fishnet_manifest(directory: pathlib.Path) -> pathlib.Path | None:
    """The manifest of one fishnet build, under either of the two names in use.

    ``fishnet_manifest.json`` was written by the first cutter and survives at
    Korenmarkt and Milan. ``site_fishnet_manifest.json`` is what the site builder
    writes. Returning None rather than guessing keeps the "no fishnet here" case
    apart from the "fishnet whose mesh cannot be resolved" case, which need
    opposite fixes.
    """
    for name in ("fishnet_manifest.json", "site_fishnet_manifest.json"):
        candidate = directory / name
        if candidate.exists():
            return candidate
    return None


def fishnet_source_mesh(
    directory: pathlib.Path,
    site: str,
    root_dir: pathlib.Path | None = None,
) -> pathlib.Path | None:
    """The mesh a fishnet was cut against, resolved to an absolute path.

    Two manifest spellings are on disk, one carrying a study relative path and
    one a bare file name, so a bare name is resolved against the site's geometry
    directory. Handing a binder the mesh of the run instead of the mesh of the
    cut would join two different triangle numberings, and it would do it quietly.
    """
    manifest = fishnet_manifest(directory)
    if manifest is None:
        return None
    named = json.loads(manifest.read_text()).get("mesh")
    if not named:
        return None
    study_root = root_dir or root()
    candidate = pathlib.Path(named)
    if not candidate.is_absolute():
        candidate = study_root / named
    if candidate.exists():
        return candidate
    fallback = geometry_dir(site, study_root) / pathlib.Path(named).name
    return fallback if fallback.exists() else None


def site_semantics(site: str, crop_m: int, suffix: str = ".npz") -> pathlib.Path:
    """The fused station binding for one site at one crop radius.

    The crop radius is part of the identity of the file and not decoration. The
    binding is an array indexed by triangle, so it is only meaningful against the
    mesh it was cast on.
    """
    return outputs_dir() / "site_semantics" / site / f"walk_semantic_{crop_m}m{suffix}"


def joint_atlas(site: str, crop_m: int, resolution: int = 8, suffix: str = ".npz") -> pathlib.Path:
    """The joint entity and material atlas over one support mesh.

    ``resolution`` is the number of cells along a source triangle edge. It is
    part of the file name because changing it changes the retained seams and
    the hit-position material posterior.
    """
    if resolution < 1:
        raise ValueError(f"atlas resolution must be at least 1, got {resolution}")
    return outputs_dir() / "site_semantics" / site / f"joint_atlas_{crop_m}m_r{resolution}{suffix}"


def walk_semantics(suffix: str = ".npz") -> pathlib.Path:
    """Korenmarkt's Mapillary walk binding, the only multi station Mapillary set.

    It has no crop radius in its name because it predates the crop sweep and was
    cut at 130 m. Every published walk number in the study was measured on it.
    """
    return outputs_dir() / "walk_korenmarkt" / f"walk_semantic{suffix}"


def screening() -> pathlib.Path:
    """The city screener's own record, which decides which capture a site walks."""
    return output("city_screening", "screening.json")


# ------------------------------------------------------------------ exposure


def exposure_dir() -> pathlib.Path:
    """Where exposure runs belong.

    Not the directory they are in. The published runs sit in
    ``outputs/exposure_korenmarkt``, which is named for one of the eleven cities
    it holds. Reads go through :func:`exposure_file`, which looks here first and
    then in the old location, so a caller rewired to this module keeps finding
    the published files while new runs land under an honest name.
    """
    return outputs_dir() / "exposure"


def legacy_exposure_dir() -> pathlib.Path:
    """The directory the published exposure runs are actually in."""
    return outputs_dir() / LEGACY_EXPOSURE_DIRNAME


def exposure_file(name: str) -> pathlib.Path:
    """One exposure file, found in either location.

    Returns the first of the two that exists, and the new location when neither
    does, so the same call reads an old run and writes a new one.
    """
    for directory in (exposure_dir(), legacy_exposure_dir()):
        candidate = directory / name
        if candidate.exists():
            return candidate
    return exposure_dir() / name


@dataclass(frozen=True)
class ExposureRun:
    """The six files one exposure run writes on a single stem.

    Every caller that touches an exposure run rebuilds three or four of these by
    hand, and the ones that rebuild only some of them are how a half written run
    gets read as a whole one. :attr:`complete` is the check that the run finished.
    """

    stem: str
    locations: pathlib.Path
    manifest: pathlib.Path
    summary: pathlib.Path
    spectra: pathlib.Path
    cdf_png: pathlib.Path
    cdf_pdf: pathlib.Path

    @property
    def complete(self) -> bool:
        """True when the streamed rows and the manifest describing them both exist.

        The figures and the summary are replottable from those two, so their
        absence means a report was never asked for rather than that the run died.
        """
        return self.locations.exists() and self.manifest.exists()


def exposure_run(stem: str) -> ExposureRun:
    """Resolve one run's six files, all of them in the directory holding the run.

    One directory for the whole family, not six independent lookups. Resolving
    each suffix on its own builds a run object out of two runs the moment a rerun
    streams fresh rows into ``outputs/exposure`` while the published CDFs still
    sit in ``outputs/exposure_korenmarkt``, and :attr:`ExposureRun.complete` then
    returns True over a pair that never ran together.

    The rows decide which directory that is, because the rows are what a run is
    and the figures are replottable from them. The stem is what the drivers call
    a tag plus the frequency, for example ``city250_L3_korenmarkt_15ghz``.
    """
    directory = exposure_dir()
    for candidate in (exposure_dir(), legacy_exposure_dir()):
        if (candidate / f"{stem}_locations.jsonl").exists():
            directory = candidate
            break
    return ExposureRun(stem, *(directory / f"{stem}{suffix}" for suffix in EXPOSURE_SUFFIXES))


def exposure_stems(pattern: str = "*") -> tuple[str, ...]:
    """Stems of every run whose rows are on disk, from both locations.

    Globs the streamed rows rather than the manifests, because a run is only
    readable if its rows are there and a manifest can outlive a deleted JSONL.
    """
    stems: set[str] = set()
    for directory in (exposure_dir(), legacy_exposure_dir()):
        if not directory.is_dir():
            continue
        for path in directory.glob(f"{pattern}_locations.jsonl"):
            stems.add(path.name.removesuffix("_locations.jsonl"))
    return tuple(sorted(stems))
