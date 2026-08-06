"""What produced a figure, recorded beside the figure.

``docs/2026-08-03_161712_LAW_CHANGE.md`` is 270 lines of survives-or-not tables. It
had to be written by hand, and it had to be written at all, because no output in
this study recorded which illumination law made it. The law was a module level
constant, somebody edited it, and every PNG written before the edit looks exactly
like every PNG written after it. The same day, ``AGGREGATE_REBUILD.md`` had to
open eleven location files by hand to find out that one of them held 3 standpoints.

Both of those are the same missing thing. A figure is a build artefact and it went
out with no record of its inputs.

So a figure written through :mod:`semantic_twin.viz.figures` carries a
:class:`FigureProvenance`: the generator, the checkout, and one :class:`Source`
per input file with that file's hash and, where the input is a run, the law and
the estimator read out of the run's own manifest. It goes into a JSON sidecar and
into the image metadata, so a PNG that has been copied somewhere else still
answers the question.

The law is read rather than declared. A generator that asserted its own law would
be a fourth place for the same fact to disagree with itself, which is knot 8 of
``TANGLE.md``.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import platform
import time
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ..runconfig import RunConfig, git

#: How a manifest's ``illumination_models[*].law`` string maps to the law family
#: that :data:`semantic_twin.runconfig.LAWS` names. The band family covers every
#: variant that puts sources in a height band and a range band, including the two
#: fixed height ones kept only to reproduce superseded numbers, because for the
#: purpose of "which law wrote this" they are all the law that was replaced.
LAW_FAMILY: dict[str, str] = {
    "isotropic": "",
    "uniform_sites": "band",
    "uniform_sites_band": "band",
    "uniform_sites_band_pathloss": "band",
    "facade_tip": "roofline",
    "roofline": "roofline",
}


@dataclass(frozen=True)
class Source:
    """One input file, hashed, with whatever the run beside it will admit to.

    ``law`` and ``estimator`` are the two fields that make this worth writing.
    They are None when the input is not a run output, which is the honest answer
    for a geometry sheet or a literature comparison, and they are ``"unknown"``
    when the input is a run whose manifest predates the field.
    """

    path: str
    sha256: str
    bytes: int
    law: str | None = None
    estimator: str | None = None
    crop_radius_m: float | None = None
    frequency_hz: float | None = None
    max_bounces: int | None = None
    locations: int | None = None
    run_digest: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {key: value for key, value in self.__dict__.items() if value is not None}


def _relative(path: pathlib.Path) -> str:
    """The path as the study names it, so a sidecar is readable in another checkout."""
    from .. import paths

    resolved = pathlib.Path(path).resolve()
    try:
        return str(resolved.relative_to(paths.root()))
    except ValueError:
        return str(resolved)


def _digest(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            hasher.update(block)
    return hasher.hexdigest()


def law_family(manifest: Mapping[str, Any]) -> str:
    """Which illumination law family a run manifest describes.

    Isotropic is not a family. It has no sources in it, which is exactly why
    ``LAW_CHANGE.md`` lists every isotropic result as surviving the law change, so
    a run scored only under isotropic gets an empty answer rather than a wrong one.
    """
    models = manifest.get("illumination_models") or {}
    families = {LAW_FAMILY.get(str(entry.get("law", "")), "unknown") for entry in models.values()}
    families.discard("")
    if not families:
        return ""
    if len(families) == 1:
        return families.pop()
    return "+".join(sorted(families))


def _manifest_for(path: pathlib.Path) -> pathlib.Path | None:
    """The run manifest beside a location file, if this input is a run output.

    The convention is one stem per run and six files on it, so a manifest is the
    location file's name with the tail swapped. Nothing here parses the stem for
    meaning, which is the mistake ``TANGLE.md`` knot 8 counts eighteen files making.
    """
    for tail in ("_locations.jsonl", "_spectra.npz", "_summary.json"):
        if path.name.endswith(tail):
            candidate = path.with_name(path.name[: -len(tail)] + "_manifest.json")
            return candidate if candidate.exists() else None
    return None


def source(path: str | pathlib.Path) -> Source:
    """Record one input file, reading the run beside it when there is one."""
    path = pathlib.Path(path)
    record: dict[str, Any] = {
        "path": _relative(path),
        "sha256": _digest(path),
        "bytes": path.stat().st_size,
    }
    manifest_path = _manifest_for(path)
    if manifest_path is not None:
        manifest = json.loads(manifest_path.read_text())
        trace = manifest.get("trace_config") or {}
        record.update(
            law=law_family(manifest) or "isotropic only",
            estimator=str(manifest.get("estimator", "escape")),
            crop_radius_m=manifest.get("crop_radius_m"),
            frequency_hz=trace.get("frequency_hz"),
            max_bounces=trace.get("max_bounces"),
            locations=manifest.get("locations_traced"),
            run_digest=manifest.get("run_digest"),
        )
    return Source(**record)


@dataclass(frozen=True)
class FigureProvenance:
    """The record written beside a figure, and stamped into it.

    ``notes`` is free form and is where a generator puts the numbers it used to
    print into a 5.4 pt line under the axes. ``FIGURES/POLISH_NOTES.md`` removed
    those lines because no printed page carries type that small, and said the
    numbers now go to the terminal. A terminal is not an archive, so they come
    here too.
    """

    figure: str
    generator: str
    created_utc: str
    git_sha: str
    git_branch: str
    git_dirty: bool
    python: str
    #: The registered figure number, or zero for a plot that is not a paper
    #: figure. The pipeline writes a CDF beside every run as a quick look, and
    #: those want a provenance record without claiming a slot in ``FIGURES/``.
    number: int = 0
    sources: tuple[Source, ...] = ()
    notes: dict[str, Any] = field(default_factory=dict)
    run: RunConfig | None = None

    @classmethod
    def capture(
        cls,
        figure: str,
        generator: str,
        *,
        number: int = 0,
        sources: Iterable[str | pathlib.Path] = (),
        run: RunConfig | None = None,
        **notes: Any,
    ) -> FigureProvenance:
        """Take the record now, from this checkout and these input files."""
        return cls(
            figure=figure,
            number=number,
            generator=generator,
            created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            git_sha=git("rev-parse", "HEAD"),
            git_branch=git("rev-parse", "--abbrev-ref", "HEAD"),
            git_dirty=bool(git("status", "--porcelain")),
            python=platform.python_version(),
            sources=tuple(source(path) for path in sources),
            notes=dict(notes),
            run=run,
        )

    @property
    def laws(self) -> tuple[str, ...]:
        """Every distinct law family among the inputs.

        More than one means the figure was assembled from runs under two laws,
        which is the defect ``LAW_CHANGE.md`` exists to track and the reason the
        eleven city figure and the eleven city table disagreed for a day.
        """
        return tuple(sorted({entry.law for entry in self.sources if entry.law}))

    def as_dict(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "figure": self.figure,
            "number": self.number,
            "generator": self.generator,
            "created_utc": self.created_utc,
            "git_sha": self.git_sha,
            "git_branch": self.git_branch,
            "git_dirty": self.git_dirty,
            "python": self.python,
            "laws": list(self.laws),
            "sources": [entry.as_dict() for entry in self.sources],
            "notes": dict(self.notes),
        }
        if self.run is not None:
            document["run"] = self.run.as_dict()
            document["run_digest"] = self.run.digest()
        return document

    def to_json(self, **kwargs: Any) -> str:
        kwargs.setdefault("indent", 2)
        kwargs.setdefault("sort_keys", True)
        return json.dumps(self.as_dict(), **kwargs)

    def stamp(self) -> str:
        """The one line version, for image metadata where space is a real constraint."""
        laws = "+".join(self.laws) or "no illumination law in the inputs"
        dirty = ", working tree dirty" if self.git_dirty else ""
        return f"{self.generator} at {self.git_sha[:12]}{dirty}, {self.created_utc}, law {laws}"

    def write_beside(self, path: str | pathlib.Path) -> pathlib.Path:
        """Write the sidecar next to an output that is not a registered figure.

        ``outputs/`` holds a CDF beside every run, drawn by the driver as a quick
        look. Those are figures too, and the whole point of ``LAW_CHANGE.md`` is
        that a figure with no record of its law costs more later than it saved.
        """
        path = pathlib.Path(path)
        sidecar = path.with_suffix(".provenance.json")
        sidecar.write_text(self.to_json() + "\n")
        return sidecar

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> FigureProvenance:
        run = document.get("run")
        return cls(
            figure=document["figure"],
            number=int(document.get("number", 0)),
            generator=document["generator"],
            created_utc=document["created_utc"],
            git_sha=document["git_sha"],
            git_branch=document["git_branch"],
            git_dirty=bool(document["git_dirty"]),
            python=document["python"],
            sources=tuple(Source(**entry) for entry in document.get("sources", ())),
            notes=dict(document.get("notes", {})),
            run=RunConfig.from_dict(run) if isinstance(run, dict) else None,
        )
