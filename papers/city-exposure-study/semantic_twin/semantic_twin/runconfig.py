"""One frozen object per run, and the provenance record it writes.

A run is currently forty argparse flags spread over two drivers, threaded through
eight function calls, and reassembled into a manifest by hand at the far end. Two
costs follow from that, and both have already been paid.

The first is that adding a method parameter means touching every layer between
the flag and the manifest, so parameters get added to the flag and not to the
manifest. The second is worse. ``docs/2026-08-03_161712_LAW_CHANGE.md`` is 270
lines of which-numbers-survive tables, and it had to be written by hand because
no output on disk records which illumination law produced it. The law was a
module level constant that got edited, and every number computed before the edit
looks exactly like every number computed after it.

So the law is a field here, and :class:`Provenance` puts it beside the git sha in
every manifest. That turns the survives-or-not question from a document into a
query.

Nothing that leaves the numbers alone belongs in this object. ``--workers`` is the
clear case: the process pool is documented as bit identical to the serial sweep,
so it is an execution choice and not part of what a run is.

The converse is the harder half, and three parameters had to be argued rather than
waved through. ``ray_epsilon_m``, ``roulette_floor`` and ``batch`` all read like
execution details and none of them is one. Each carries the measurement that put
it here in its own comment. ``batch`` is the one to watch: it is inert only while
``rays`` stays under it, so it costs nothing today and would merge two genuinely
different runs under one identity the first time a sweep asks for more rays.

The identity is not the whole object. :meth:`RunConfig.identity` says what the
digest hashes and why the two exceptions are exceptions, and the digests of four
shipped configurations are pinned to literal strings in
``tests/test_runconfig.py``. Adding a field moves every stem in the study, so it
has to announce itself rather than quietly renaming every output.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import platform
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any

#: Which family of illumination law placed the sources.
#:
#: ``band`` puts base stations in a height band and a range band, four numbers per
#: deployment class. ``roofline`` puts them on facade tips read off the geometry,
#: so each azimuth carries one source distance and there is no cap to argue about.
#: This is the single field that answers "which law wrote this number", which is
#: the question ``LAW_CHANGE.md`` exists to answer.
LAWS = ("band", "roofline")

#: How a traced path is credited.
#:
#: ``escape`` weights a ray by the angular source density in the direction it
#: leaves the crop. ``next_event`` connects each path vertex to an explicit source
#: point and tests visibility from there. They answer the same question and
#: disagree by a factor of three to five on real cities, so which one ran is not a
#: detail.
ESTIMATORS = ("escape", "next_event")

#: Where the observation points come from.
#:
#: ``grid`` scatters heads over walkable ground on a lattice and chains them
#: nearest neighbour first. It is a sampling design, it is what every published
#: number used, and it is not a route anyone took. ``route`` stands where the
#: cameras stood, in the order the street connects them.
WALKS = ("grid", "route")

#: What "between the cameras" means for a route walk. ``links`` follows the
#: provider's own panorama link graph, ``street`` asks a routing service for a
#: walking path, ``closest`` measures both and keeps whichever stands nearer a
#: camera.
WALK_PATHS = ("links", "street", "closest")

#: How each triangle gets its electromagnetic properties. ``geometric`` reads
#: material off triangle orientation alone and is the no-photographs control.
#: Everything else binds some layer of image evidence on top of it.
MATERIALS = (
    "geometric",
    "semantic",
    "walk",
    "walk_material",
    "walk_material_mixture",
    "walk_material_over_entity",
    "walk_material_facade_only",
)


@dataclass(frozen=True)
class NextEventConfig:
    """The knobs that only exist when sources are explicit points.

    Kept as a nested object rather than flattened into :class:`RunConfig`, because
    an escape run has no source set and a config listing nine fields that do not
    apply to it invites someone to fill them in. ``next_event is None`` says the
    run had no source set, which is a fact about the run and not a default.
    """

    #: Standpoints used to build the source set. The set is the union of what they
    #: can see on the skyline.
    builders: int = 128
    #: Standpoints scored against the set, kept disjoint from the builders so no
    #: standpoint is measured against a source set it wrote itself.
    held_out: int = 16
    azimuths: int = 1440
    elevations: int = 600
    #: Sources are thinned to one per occupied cell of this size, so a wall seen
    #: edge on is not counted once per ray that grazed it.
    cell_m: float = 1.0
    #: Thin in plan or in space. Two dimensions merges a low roof into the tall
    #: building behind it.
    dims: int = 3
    #: How far a source stands clear of the surface it was found on, so a point on
    #: a facade tip is not buried in the facade.
    site_lift_m: float = 0.5
    #: Source connections attempted per path vertex.
    connections: int = 1
    #: Keep sources off the tips the panoramas call a sign, a pole or a canopy.
    drop_clutter: bool = False

    def __post_init__(self) -> None:
        if self.dims not in (2, 3):
            raise ValueError(f"dims must be 2 or 3, got {self.dims}")
        for name in ("builders", "held_out", "azimuths", "elevations", "connections"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be at least 1, got {getattr(self, name)}")


@dataclass(frozen=True)
class RunConfig:
    """Everything that decides the numbers a run produces.

    Frozen, so a config cannot be edited halfway down a call chain and leave the
    manifest describing a run that did not happen.
    """

    # ------------------------------------------------------------------ scene
    site: str
    #: Crop radius in metres. This used to live inside a mesh file name, which
    #: eighteen files parsed. It is a run parameter, so it is a field.
    crop_m: int = 250

    # ------------------------------------------------------------ illumination
    law: str = "roofline"
    #: The named illumination models the run scored. One trace can be scored under
    #: several, because the source density is a weight on the result and never
    #: enters the ray trace.
    models: tuple[str, ...] = ("isotropic",)

    # --------------------------------------------------------------- estimator
    estimator: str = "next_event"
    next_event: NextEventConfig | None = None

    # -------------------------------------------------------------------- walk
    walk: str = "route"
    walk_path: str = "links"
    walk_radius_m: float = 90.0
    #: Lattice spacing for a grid walk.
    walk_spacing_m: float = 3.0
    #: Spacing of the extra standpoints a route walk adds between cameras.
    walk_stride_m: float = 6.0
    head_height_m: float = 1.5
    #: How many standpoints are traced. Zero means every one the walk produced.
    locations: int = 0

    # ----------------------------------------------------------------- physics
    frequency_hz: float = 15.0e9
    max_bounces: int = 3
    #: Bounce depth at which Russian roulette starts. None means one past the
    #: budget, which is the shipped default and means roulette never fires.
    roulette_start: int | None = None
    #: Floor on the roulette survival probability.
    #:
    #: Inert while roulette never fires, which is the shipped default, and
    #: decisive when it does. Older manifests record ``roulette_start`` 3, and at
    #: that setting ``tracer.py:696`` clips the survival probability to this floor
    #: and then draws against it, so this number chooses which rays are killed.
    #: ``run_seed_replicas.py:146`` and ``repair_torn_sites.py:136`` already read
    #: it back off a manifest as a run parameter.
    roulette_floor: float = 0.05
    #: How far a ray is lifted off a surface before it is cast again, in metres.
    #:
    #: Small and not nothing. ``docs/BUGS.md`` measures ``chi_bounce`` at 1.4541e-4
    #: for a 0.1 mm lift and 1.4590e-4 at the shipped 1 cm, which is a plateau
    #: across two decades rather than a flat line. A plateau still has a slope, so
    #: the number a run used is part of what the run was.
    ray_epsilon_m: float = 1.0e-3
    #: Charge each escaping ray for the distance it travelled. A diagnostic on the
    #: escape estimator's missing range term, off in every published number.
    range_weighted_escape: bool = False
    materials: str = "geometric"
    #: Fused semantics to bind materials from, when the materials mode needs one.
    #: A study relative path, so a config stays portable between checkouts.
    walk_npz: str | None = None

    # ---------------------------------------------------------------- sampling
    rays: int = 200_000
    #: Rays cast per turn of the tracer's inner loop.
    #:
    #: This is documented elsewhere as an execution detail and it is not one.
    #: ``tracer.py:479`` makes one generator per standpoint and ``tracer.py:499``
    #: draws batches from it in sequence, and each batch draws several times over
    #: its own rays: two for the launch direction at ``tracer.py:406`` and one per
    #: bounce depth at ``tracer.py:688``. So 200,000 rays in one batch and the same
    #: 200,000 in two batches of 100,000 hand every ray a different number from the
    #: same stream, and the two runs are not the same run.
    #:
    #: Inert while ``rays`` stays at or below it, which is why it has cost nothing
    #: so far. It is the first higher ray sweep that would find out.
    batch: int = 400_000
    local_cells: int = 512
    exit_bands: int = 18
    seed: int = 7
    #: The ray tracing backend. Included because the CUDA and LLVM backends are
    #: benchmarked against each other and a difference between them would be a
    #: difference in the answer, not in the wall clock.
    variant: str = "llvm_ad_rgb"

    # --------------------------------------------------------------- labelling
    #: What the run's output files are named after.
    #:
    #: A label and not a parameter, and the two are kept apart rather than
    #: promised apart. The tag leads :meth:`stem` and is dropped from
    #: :meth:`identity`, so the same run written twice under two tags has two file
    #: names and one digest. ``--tag-suffix`` at ``run_exposure.py:1503`` exists to
    #: do exactly that.
    tag: str = ""

    def __post_init__(self) -> None:
        self._check_names()
        self._check_quantities()
        self._settle_the_source_set()

    def _check_names(self) -> None:
        """A typo in a law name must not reach a manifest and look authoritative."""
        for name, allowed in (
            ("law", LAWS),
            ("estimator", ESTIMATORS),
            ("walk", WALKS),
            ("walk_path", WALK_PATHS),
            ("materials", MATERIALS),
        ):
            value = getattr(self, name)
            if value not in allowed:
                raise ValueError(f"{name} must be one of {', '.join(allowed)}, got {value!r}")
        if not self.models:
            raise ValueError("a run has to score at least one illumination model")

    def _check_quantities(self) -> None:
        for name in ("crop_m", "rays", "batch", "frequency_hz", "ray_epsilon_m"):
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value}")
        if self.max_bounces < 0:
            raise ValueError(f"max_bounces cannot be negative, got {self.max_bounces}")
        if not 0.0 < self.roulette_floor <= 1.0:
            raise ValueError(f"roulette_floor is a probability, got {self.roulette_floor}")

    def _settle_the_source_set(self) -> None:
        if self.estimator == "next_event" and self.next_event is None:
            object.__setattr__(self, "next_event", NextEventConfig())
        if self.estimator == "escape" and self.next_event is not None:
            raise ValueError("an escape run has no source set, so next_event must be None")

    @property
    def frequency_ghz(self) -> float:
        return self.frequency_hz / 1e9

    @property
    def effective_roulette_start(self) -> int:
        """The bounce depth roulette actually starts at, as the tracer is told it.

        None on the field means one past the budget, so roulette never fires. That
        is the shipped default and it is stored as None rather than as a number so
        that a config does not silently pin an old budget's value when the budget
        changes.

        Not clamped. This is the number that goes into ``TraceConfig``, so it has
        to be what the caller asked for. :meth:`identity` is where the clamp is,
        and it says why.
        """
        return self.max_bounces + 1 if self.roulette_start is None else self.roulette_start

    def stem(self) -> str:
        """The file name stem a run writes on.

        Tag, frequency and digest, and the tag appears once. It used to appear
        twice, as the head and inside the digest, which meant two tags on one run
        gave two names and two identities where the point was to give two names
        and one identity.
        """
        head = self.tag or f"{self.estimator}_{self.site}_{self.crop_m}m"
        return f"{head}_{self.frequency_ghz:g}ghz_{self.digest()}"

    def identity(self) -> dict[str, Any]:
        """What :meth:`digest` hashes: the run, with the label and the aliases gone.

        Two departures from :meth:`as_dict`, both deliberate.

        ``tag`` is dropped, because it names the files and not the physics. The
        drivers ship ``--tag-suffix`` precisely so a rerun can land beside a
        published run instead of on top of it, and if the tag entered the hash
        that rerun would carry a fresh identity and nothing could tell it was the
        same run.

        ``roulette_start`` is replaced by the depth roulette can first fire at,
        clamped to one past the budget. The tracer's predicate is
        ``depth + 1 >= roulette_start`` at ``tracer.py:695``, and the loop breaks
        at ``depth == max_bounces`` before reaching it, so every value above the
        budget leaves the roulette branch unentered, draws no random number and
        produces the same trace. Old manifests write the explicit ``4`` where this
        code writes ``None`` at a three bounce budget. Those are one run.
        """
        document = self.as_dict()
        document.pop("tag")
        document["roulette_start"] = min(self.effective_roulette_start, self.max_bounces + 1)
        return document

    def digest(self, length: int = 12) -> str:
        """A short stable hash of the run identity.

        Two configs that hash the same describe the same run, which is what makes
        this usable as the guard the drivers currently write by hand: a
        reusability check that reads the old manifest back and compares six
        fields. Sorted keys, so the hash does not move when a field is added in
        the middle of the class.

        Adding a field does move the hash, and therefore every output stem in the
        study. ``tests/test_runconfig.py`` pins four of these to literal strings so
        that it happens on purpose.
        """
        payload = json.dumps(self.identity(), sort_keys=True, separators=(",", ":"))
        return hashlib.blake2b(payload.encode(), digest_size=length).hexdigest()[:length]

    # ---------------------------------------------------------- serialisation

    def as_dict(self) -> dict[str, Any]:
        """A plain JSON-ready mapping. Tuples become lists, nesting is kept."""
        return dataclasses.asdict(self)

    def to_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("indent", 2)
        kwargs.setdefault("sort_keys", True)
        return json.dumps(self.as_dict(), **kwargs)

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> RunConfig:
        """Rebuild a config from its mapping, rejecting fields it does not have.

        An unknown key is an error rather than something to ignore. A manifest
        written by a later version carries a parameter this code does not honour,
        and silently dropping it would produce a config that describes a different
        run from the one on disk.
        """
        fields = {entry.name for entry in dataclasses.fields(cls)}
        unknown = set(document) - fields
        if unknown:
            raise ValueError(f"not fields of RunConfig: {', '.join(sorted(unknown))}")
        values = dict(document)
        if "models" in values:
            values["models"] = tuple(values["models"])
        nested = values.get("next_event")
        if isinstance(nested, dict):
            values["next_event"] = NextEventConfig(**nested)
        return cls(**values)

    @classmethod
    def from_json(cls, text: str) -> RunConfig:
        return cls.from_dict(json.loads(text))

    def replace(self, **changes: Any) -> RunConfig:
        """A copy with some fields changed. The frozen object's editing move."""
        return dataclasses.replace(self, **changes)


@dataclass(frozen=True)
class Provenance:
    """What a run was, and what produced it, written beside every output.

    Three of these fields are the whole point. ``law`` and ``estimator`` are
    lifted out of the config to the top level so that a reader scanning manifests
    can group them without parsing anything. ``git_sha`` says which code ran, and
    ``git_dirty`` admits when that is not the whole truth.
    """

    run: RunConfig
    generator: str
    created_utc: str
    git_sha: str
    git_branch: str
    git_dirty: bool
    python: str
    #: Package versions worth pinning, filled by the caller. Left open because
    #: which packages matter differs between an escape run and a figure.
    versions: dict[str, str] = field(default_factory=dict)

    @classmethod
    def capture(cls, run: RunConfig, generator: str, **versions: str) -> Provenance:
        """Take the record now, from this checkout."""
        return cls(
            run=run,
            generator=generator,
            created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            git_sha=git("rev-parse", "HEAD"),
            git_branch=git("rev-parse", "--abbrev-ref", "HEAD"),
            git_dirty=bool(git("status", "--porcelain")),
            python=platform.python_version(),
            versions=dict(versions),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "generator": self.generator,
            "created_utc": self.created_utc,
            "git_sha": self.git_sha,
            "git_branch": self.git_branch,
            "git_dirty": self.git_dirty,
            "python": self.python,
            "versions": dict(self.versions),
            "law": self.run.law,
            "estimator": self.run.estimator,
            "run_digest": self.run.digest(),
            "run": self.run.as_dict(),
        }

    def to_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("indent", 2)
        kwargs.setdefault("sort_keys", True)
        return json.dumps(self.as_dict(), **kwargs)

    @classmethod
    def from_dict(cls, document: dict[str, Any]) -> Provenance:
        return cls(
            run=RunConfig.from_dict(document["run"]),
            generator=document["generator"],
            created_utc=document["created_utc"],
            git_sha=document["git_sha"],
            git_branch=document["git_branch"],
            git_dirty=bool(document["git_dirty"]),
            python=document["python"],
            versions=dict(document.get("versions", {})),
        )

    @classmethod
    def from_json(cls, text: str) -> Provenance:
        return cls.from_dict(json.loads(text))


def git(*args: str) -> str:
    """Ask git, and say ``unknown`` rather than failing a run over it.

    A manifest with an unknown sha is worse than one with a sha and far better
    than a trace that died at the last line because the study was unpacked from a
    tarball.
    """
    from . import paths

    try:
        finished = subprocess.run(["git", *args], cwd=paths.root(), capture_output=True, text=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"
    return finished.stdout.strip()
