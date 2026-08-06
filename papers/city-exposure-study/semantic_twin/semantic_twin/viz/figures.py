"""The figure registry. Content is the identity, the number is assigned here.

``FIGURES/`` grew two figure 24s and two figure 25s, because two work streams
numbered their own output and neither looked at the other's. ``24`` was the
diffraction bound and also the walk route. ``25`` was the bounce budget and also
the walk cities sheet. Nothing broke, because ``paper/paper.tex`` writes
``\\includegraphics{24_diffraction_bound}`` and names the whole stem, but a
directory listing was ambiguous and a reader asking "what is figure 24" had two
answers.

The cause is that a number was chosen at creation time, by whoever was writing the
generator, from what they remembered of the directory. So the number moves here.
A generator names its figure by content, asks this module for the file stem, and
never types a number. Two generators cannot pick the same number because
:data:`FIGURES` is checked for collisions when this module is imported.

**The collision and how it was resolved.** ``24_diffraction_bound`` and
``25_bounce_budget`` keep their numbers, because ``paper/paper.tex`` places both.
The walk figures were not placed, so they take the next free numbers:
``24_walk_route`` becomes ``26_walk_route`` and ``25_walk_cities`` becomes
``27_walk_cities``. The two files under the old stems are left where they are.
They are cited from ``docs/`` by name, and deleting a file to tidy a listing is
how a citation becomes a dead link. :func:`orphans` finds them and says why they
are there, so the state is recorded rather than merely tolerated.

The numbers here are not a reading order and they are not consecutive with the
paper's own figure numbering, which LaTeX assigns. They are file names, and their
one job is to be stable, because 106 files outside ``docs/`` cite this study's
artefacts by name.
"""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .provenance import FigureProvenance

#: Formats every figure is written in. PDF is what the paper places, PNG is what a
#: human opens. Both, always, so the two cannot drift out of step, which they did
#: for the figures that shipped as a PNG only.
FORMATS: tuple[str, ...] = ("pdf", "png")


@dataclass(frozen=True)
class Figure:
    """One figure, identified by content and numbered by this table."""

    #: The content name. This is the identity and it does not change.
    name: str
    #: The file number. A file name detail, decided here and nowhere else.
    number: int
    #: What the figure shows, in one line.
    what: str
    #: The script that draws it, relative to the study root.
    generator: str
    #: True when ``paper/paper.tex`` or ``paper/body.tex`` places it. A placed
    #: figure's stem is load bearing and cannot be renumbered without editing the
    #: LaTeX, which is why the collision was resolved in favour of the placed pair.
    placed: bool = False
    #: Formats on disk. Six of the early sheets are PNG only because they are
    #: renders rather than plots.
    formats: tuple[str, ...] = FORMATS

    @property
    def stem(self) -> str:
        return f"{self.number:02d}_{self.name}"

    def path(self, suffix: str = "png", directory: pathlib.Path | None = None) -> pathlib.Path:
        return (directory or figures_dir()) / f"{self.stem}.{suffix.lstrip('.')}"

    @property
    def provenance_path(self) -> pathlib.Path:
        return figures_dir() / f"{self.stem}.provenance.json"


#: Renders rather than plots, so PNG only.
_PNG = ("png",)

#: Every figure the study produces, in file order. Adding one here is the whole
#: act of adding a figure: the number is taken from this table, the stem follows
#: from it, and the collision check below runs at import.
FIGURES: tuple[Figure, ...] = (
    Figure("korenmarkt_twin", 1, "The twin at Korenmarkt", "render_showcase.py", formats=_PNG),
    Figure("milan_twin", 2, "The twin at Piazza del Duomo", "render_showcase.py", formats=_PNG),
    Figure("what_one_panorama_sees", 3, "First hit coverage of a single panorama", "render_showcase.py", formats=_PNG),
    Figure("facade_class_vs_photo", 4, "Resolved facade against its source crop", "render_showcase.py", formats=_PNG),
    Figure(
        "four_layers_deep", 5, "Geometry, class, material and roughness stacked", "render_showcase.py", formats=_PNG
    ),
    Figure("what_the_cutter_refused", 6, "Rejected surface elements, by reason", "render_showcase.py", formats=_PNG),
    Figure("mesh_study", 7, "Nineteen mesh candidates on one ray cast", "make_remesh_panel.py", formats=_PNG),
    Figure("brickwork_bistatic", 8, "Bistatic orders of standard brickwork", "plot_masonry_grating.py", formats=_PNG),
    Figure(
        "brickwork_specular_law",
        9,
        "Predicted against measured, nothing fitted",
        "plot_masonry_grating.py",
        formats=_PNG,
    ),
    Figure("remesh_visual", 10, "What remeshing does to a market square", "make_remesh_panel.py", formats=_PNG),
    Figure(
        "eleven_cities", 11, "Contact sheet of every acquired city", "make_city_sheet.py", placed=True, formats=_PNG
    ),
    Figure(
        "foliage_sensitivity",
        12,
        "Three foliage treatments against canopy solid angle",
        "run_foliage_study.py",
        formats=_PNG,
    ),
    Figure(
        "brickwork_convergence",
        13,
        "Retained Floquet orders against the answer",
        "plot_masonry_grating.py",
        formats=_PNG,
    ),
    Figure(
        "exposure_cdf_korenmarkt",
        14,
        "The exposure distribution along one Korenmarkt walk",
        "FIGURES/make_walk_exposure_cdf.py",
    ),
    Figure("crop_convergence", 15, "Has the crop radius converged", "FIGURES/make_crop_convergence.py", placed=True),
    Figure(
        "eleven_cities_exposure",
        16,
        "Pedestrian exposure across eleven squares",
        "FIGURES/make_eleven_cities_exposure.py",
        placed=True,
    ),
    Figure("evidence_ladder", 17, "Does image evidence move the distribution", "FIGURES/make_evidence_ladder.py"),
    Figure(
        "elevation_geometry", 18, "Elevation is a ratio, not a height", "FIGURES/make_explainer_figures.py", placed=True
    ),
    Figure(
        "deployment_box",
        19,
        "The deployment box and the density it induces",
        "FIGURES/make_explainer_figures.py",
        placed=True,
    ),
    Figure("adjoint_idea", 20, "Why the tracer runs backwards", "FIGURES/make_explainer_figures.py", placed=True),
    Figure("one_ray", 21, "One ray from launch to deposit", "FIGURES/make_explainer_figures.py", placed=True),
    Figure(
        "evidence_reach",
        22,
        "How far the photographic evidence reaches",
        "FIGURES/make_evidence_reach_figure.py",
        placed=True,
    ),
    Figure("multipath_surplus", 23, "What the bounces add, under both estimators", "FIGURES/make_multipath_surplus.py"),
    Figure(
        "diffraction_bound",
        24,
        "The diffraction hole, bounded on the traced geometry",
        "FIGURES/make_diffraction_bound_figure.py",
        placed=True,
    ),
    Figure(
        "bounce_budget",
        25,
        "Three interactions, measured rather than preferred",
        "FIGURES/make_bounce_budget_figure.py",
        placed=True,
    ),
    # Renumbered out of the collision. Were 24 and 25.
    Figure("walk_route", 26, "Where the walk stands now against where it used to", "FIGURES/make_walk_route.py"),
    Figure(
        "walk_cities", 27, "Both candidate walks at every square whose panoramas chain", "FIGURES/make_walk_cities.py"
    ),
)

#: Stems that existed before the numbers moved here, and what they became. The
#: files stay on disk: ``docs/`` cites them and a dead citation is worse than a
#: duplicate file. :func:`orphans` reads this so that "why are there two 24s"
#: has an answer in code rather than in a commit message.
SUPERSEDED_STEMS: dict[str, str] = {
    "24_walk_route": "26_walk_route",
    "25_walk_cities": "27_walk_cities",
}

BY_NAME: dict[str, Figure] = {}
BY_NUMBER: dict[int, Figure] = {}
for _figure in FIGURES:
    if _figure.name in BY_NAME:
        raise RuntimeError(f"two figures are called {_figure.name!r}")
    if _figure.number in BY_NUMBER:
        raise RuntimeError(
            f"figure number {_figure.number} is claimed by {BY_NUMBER[_figure.number].name!r} and by {_figure.name!r}. "
            f"This is the collision the registry exists to make impossible."
        )
    BY_NAME[_figure.name] = _figure
    BY_NUMBER[_figure.number] = _figure
del _figure


def figures_dir() -> pathlib.Path:
    from .. import paths

    return paths.root() / "FIGURES"


def get(name: str) -> Figure:
    """One figure by content name, with the near misses named on a typo."""
    if name in BY_NAME:
        return BY_NAME[name]
    close = sorted(other for other in BY_NAME if name in other or other in name)
    hint = f" Did you mean {', '.join(close)}?" if close else ""
    raise KeyError(f"no figure called {name!r}.{hint}")


def stem(name: str) -> str:
    """The file stem a generator writes on. The only way a generator learns a number."""
    return get(name).stem


def next_free_number() -> int:
    """The number a new figure would take. Used when adding one, not at draw time."""
    return max(BY_NUMBER) + 1


def orphans(directory: pathlib.Path | None = None) -> tuple[str, ...]:
    """Stems on disk that the registry does not name, with the reason where known.

    The two superseded walk stems come back with an explanation. Anything else
    coming back means a generator wrote a file the registry has not been told
    about, which is exactly how the numbering drifted the first time.
    """
    directory = directory or figures_dir()
    if not directory.is_dir():
        return ()
    known = {figure.stem for figure in FIGURES}
    found: dict[str, None] = {}
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() not in (".png", ".pdf"):
            continue
        if path.stem in known:
            continue
        found.setdefault(path.stem, None)
    return tuple(
        f"{name} -> renumbered to {SUPERSEDED_STEMS[name]}, file kept because docs/ cites it"
        if name in SUPERSEDED_STEMS
        else f"{name} -> not in the registry"
        for name in found
    )


def missing(directory: pathlib.Path | None = None) -> tuple[str, ...]:
    """Registry entries with no file on disk, one line per missing format."""
    directory = directory or figures_dir()
    gone: list[str] = []
    for figure in FIGURES:
        for suffix in figure.formats:
            if not figure.path(suffix, directory).exists():
                gone.append(f"{figure.stem}.{suffix}")
    return tuple(gone)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


#: PDF carries a fixed set of document information keys and matplotlib warns on
#: anything else, so the provenance goes into Subject and the law into Keywords.
#: PNG takes arbitrary text chunks, so it gets the whole record.
def _pdf_metadata(figure: Figure, record: FigureProvenance) -> dict[str, str]:
    return {
        "Title": f"Figure {figure.number}: {figure.what}",
        "Subject": record.stamp(),
        "Keywords": " ".join(["law=" + ("+".join(record.laws) or "none"), "figure=" + figure.name]),
        "Creator": record.generator,
    }


def _png_metadata(figure: Figure, record: FigureProvenance) -> dict[str, str]:
    return {
        "Title": f"Figure {figure.number}: {figure.what}",
        "Description": record.stamp(),
        "Software": record.generator,
        "Source": record.to_json(indent=None, sort_keys=True),
    }


def save(
    figure: Any,
    name: str,
    record: FigureProvenance,
    *,
    directory: pathlib.Path | None = None,
    formats: Sequence[str] | None = None,
    dpi: int = 300,
    **savefig: Any,
) -> tuple[pathlib.Path, ...]:
    """Write a matplotlib figure under its registered stem, with its provenance.

    Three things land: the PDF the paper places, the PNG a human opens, and a
    ``.provenance.json`` sidecar. The record also goes into the image metadata, so
    a PNG that has been copied into a slide deck still answers which law and which
    checkout made it. The sidecar is the one to read, because PDF document
    information is a short field and the source list is not short.
    """
    spec = get(name)
    if record.figure != spec.name or record.number != spec.number:
        raise ValueError(
            f"the provenance says figure {record.number} {record.figure!r} and the registry says "
            f"{spec.number} {spec.name!r}. Build the record with provenance_for()."
        )
    directory = directory or figures_dir()
    directory.mkdir(parents=True, exist_ok=True)
    written: list[pathlib.Path] = []
    for suffix in formats or spec.formats:
        path = spec.path(suffix, directory)
        metadata = _pdf_metadata(spec, record) if suffix == "pdf" else _png_metadata(spec, record)
        figure.savefig(path, dpi=dpi, metadata=metadata, **savefig)
        written.append(path)
    sidecar = directory / f"{spec.stem}.provenance.json"
    sidecar.write_text(record.to_json() + "\n")
    written.append(sidecar)
    return tuple(written)


def save_image(
    image: Any,
    name: str,
    record: FigureProvenance,
    *,
    directory: pathlib.Path | None = None,
) -> tuple[pathlib.Path, ...]:
    """The same, for a sheet assembled with Pillow rather than drawn with matplotlib.

    The contact sheet is a montage of renders, so it is built by pasting images
    rather than by plotting. It still has to say what made it, and a PNG text chunk
    is the same place the matplotlib path writes to, so the two are readable by one
    reader.
    """
    from PIL import PngImagePlugin

    spec = get(name)
    directory = directory or figures_dir()
    directory.mkdir(parents=True, exist_ok=True)
    info = PngImagePlugin.PngInfo()
    for key, value in _png_metadata(spec, record).items():
        info.add_text(key, value)
    path = spec.path("png", directory)
    image.save(path, pnginfo=info)
    sidecar = directory / f"{spec.stem}.provenance.json"
    sidecar.write_text(record.to_json() + "\n")
    return (path, sidecar)


def provenance_for(
    name: str,
    generator: str,
    *,
    sources: Iterable[Any] = (),
    **notes: Any,
) -> FigureProvenance:
    """The record for one registered figure, with its number filled in from here.

    A generator never types its own number, and it never types its own git sha
    either. Both come from somewhere that cannot be out of date.
    """
    spec = get(name)
    return FigureProvenance.capture(spec.name, generator, number=spec.number, sources=sources, **notes)


def read_provenance(name: str, directory: pathlib.Path | None = None) -> FigureProvenance | None:
    """The sidecar for a figure, or None if that figure predates the sidecar."""
    import json

    spec = get(name)
    path = (directory or figures_dir()) / f"{spec.stem}.provenance.json"
    if not path.exists():
        return None
    return FigureProvenance.from_dict(json.loads(path.read_text()))


def index(rows: Mapping[str, str] | None = None) -> str:
    """The registry as a markdown table, for the index in ``FIGURES/README.md``."""
    notes = rows or {}
    lines = ["| # | figure | what it shows | generator | in the paper |", "| --- | --- | --- | --- | --- |"]
    for figure in FIGURES:
        placed = "yes" if figure.placed else ""
        what = notes.get(figure.name, figure.what)
        lines.append(f"| {figure.number:02d} | `{figure.stem}` | {what} | `{figure.generator}` | {placed} |")
    return "\n".join(lines)
