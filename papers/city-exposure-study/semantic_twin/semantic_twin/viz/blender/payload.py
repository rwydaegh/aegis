"""What the payload holds, and everything derived from it. No Blender in here.

This is the half of the blend builder that is arithmetic, and separating it is the
point of the split. ``propagation_blender.py`` opened with ``import bpy``, so a
function that decides where the rim breaks or which bundle a ray belongs to could
only run inside Blender, and a function that can only run inside Blender does not
get a test. ``tests/test_propagation_viz.py`` covers the exporter that writes the
payload and covered none of this, which is the stage that reads it.

Everything here takes numpy arrays or a mapping that behaves like an ``npz`` and
returns numpy arrays. The one Blender-adjacent thing it does is
:func:`camera_rotation`, and that is trigonometry with a Blender convention in it
rather than a Blender call.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import pathlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, cast

import numpy as np

from .style import MODEL_BANDS, RIM_LIFT_RADII, RIM_RAMP_FLOOR, colour_ramp

#: The sources a blend is built from. A blend whose fingerprint over these does
#: not match today's is a build artefact from different code, exactly the way a
#: compiled binary is, and on 3 August every blend in the tree was one.
#:
#: Lives here rather than in the runner because ``qa_propagation_blend.py`` has to
#: compute the same hash outside Blender and used to keep a hand copy of the list
#: with a comment explaining that importing the real one would pull in ``bpy``.
#: That is no longer true, so there is one list.
BUILDER_SOURCES: tuple[str, ...] = (
    "propagation_blender.py",
    "export_propagation_payload.py",
    "semantic_twin/viz/blender/exporter.py",
    "semantic_twin/viz/blender/payload.py",
    "semantic_twin/viz/blender/style.py",
    "semantic_twin/viz/blender/scene.py",
    "semantic_twin/viz/blender/estimator.py",
    "semantic_twin/viz/blender/evidence.py",
    "semantic_twin/viz/blender/renders.py",
    "semantic_twin/walk/__init__.py",
    "semantic_twin/walk/builders.py",
    "semantic_twin/walk/grid.py",
    "semantic_twin/walk/ground.py",
    "semantic_twin/walk/links.py",
    "semantic_twin/walk/model.py",
    "semantic_twin/walk/ordering.py",
    "semantic_twin/walk/route.py",
    "semantic_twin/walk/site.py",
)


@dataclass(frozen=True)
class ProductionFiles:
    """The three files that together make one streamed exposure result."""

    locations: pathlib.Path
    spectra: pathlib.Path
    manifest: pathlib.Path

    def hashes(self) -> dict[str, dict[str, str]]:
        """Exact input identity written into the visualization manifest."""
        return {
            name: {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for name, path in (
                ("locations_jsonl", self.locations),
                ("spectra_npz", self.spectra),
                ("manifest_json", self.manifest),
            )
        }


@dataclass(frozen=True)
class ProductionData:
    """Validated arrays and rows read from one production exposure result."""

    files: ProductionFiles
    input_identity: dict[str, dict[str, str]]
    manifest: dict[str, Any]
    rows: tuple[dict[str, Any], ...]
    index: np.ndarray
    rho_rooftop: np.ndarray
    local_grid: np.ndarray
    solid_angle: float


def production_files(
    *,
    stem: pathlib.Path | None,
    locations: pathlib.Path | None,
    spectra: pathlib.Path | None,
    manifest: pathlib.Path | None,
    default_directory: pathlib.Path,
) -> ProductionFiles | None:
    """Resolve a named stem or three exact paths, and reject mixed input."""
    exact = (locations, spectra, manifest)
    if stem is not None and any(path is not None for path in exact):
        raise ValueError("use --production-stem or the three exact production paths, not both")
    if stem is not None:
        base = stem if stem.parent != pathlib.Path(".") else default_directory / stem
        return ProductionFiles(
            base.with_name(f"{base.name}_locations.jsonl"),
            base.with_name(f"{base.name}_spectra.npz"),
            base.with_name(f"{base.name}_manifest.json"),
        )
    if not any(path is not None for path in exact):
        return None
    if not all(path is not None for path in exact):
        raise ValueError(
            "production input needs --production-locations, --production-spectra, and --production-manifest"
        )
    return ProductionFiles(
        cast(pathlib.Path, locations),
        cast(pathlib.Path, spectra),
        cast(pathlib.Path, manifest),
    )


def read_production_data(files: ProductionFiles) -> ProductionData:
    """Read the three files without deciding whether they describe this model."""
    missing = [str(path) for path in (files.locations, files.spectra, files.manifest) if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"production exposure input does not exist: {', '.join(missing)}")
    content = {
        "locations_jsonl": files.locations.read_bytes(),
        "spectra_npz": files.spectra.read_bytes(),
        "manifest_json": files.manifest.read_bytes(),
    }
    identity = {
        name: {"path": str(path.resolve()), "sha256": hashlib.sha256(content[name]).hexdigest()}
        for name, path in (
            ("locations_jsonl", files.locations),
            ("spectra_npz", files.spectra),
            ("manifest_json", files.manifest),
        )
    }
    manifest = json.loads(content["manifest_json"])
    if not isinstance(manifest, dict):
        raise TypeError(f"{files.manifest} must contain one JSON object")
    text = content["locations_jsonl"].decode()
    if text and not text.endswith("\n"):
        raise ValueError(f"{files.locations} ends with an incomplete JSONL row")
    rows = tuple(json.loads(line) for line in text.splitlines())
    with np.load(io.BytesIO(content["spectra_npz"])) as saved:
        arrays = {
            name: np.array(saved[name], copy=True) for name in ("index", "rho_rooftop", "local_grid", "solid_angle")
        }
    return ProductionData(
        files=files,
        input_identity=identity,
        manifest=manifest,
        rows=rows,
        index=arrays["index"],
        rho_rooftop=arrays["rho_rooftop"],
        local_grid=arrays["local_grid"],
        solid_angle=float(arrays["solid_angle"]),
    )


def builder_fingerprint(root: pathlib.Path | None = None) -> str:
    """A hash over the code that writes a blend, stamped into the blend.

    A timestamp cannot answer "was this built by today's code". Committing an
    unchanged file moves its commit time forward and makes a perfectly current
    blend look stale, which is what happened the first time this was checked.
    Hashing the bytes answers it exactly and says nothing about when.
    """
    if root is None:
        from ... import paths

        root = paths.root()
    digest = hashlib.sha256()
    for name in BUILDER_SOURCES:
        path = root / name
        digest.update(path.read_bytes() if path.exists() else b"")
    return digest.hexdigest()[:16]


def has(payload: Any, prefix: str) -> bool:
    """Does the payload carry any array whose name starts with this?

    Every evidence layer is optional, and the test for whether a site has one is
    whether its arrays are in the file. A site with no panorama is not an error
    and never has been.
    """
    return any(key.startswith(prefix) for key in payload.files)


def available_spectrum_models(payload: Any, candidates: Sequence[str]) -> tuple[str, ...]:
    """Models whose angular spectrum is actually present in this payload."""
    keys = payload.files if hasattr(payload, "files") else payload
    return tuple(name for name in candidates if f"rho_{name}" in keys)


def elevation_deg(directions: np.ndarray) -> np.ndarray:
    return np.degrees(np.arcsin(np.clip(np.asarray(directions, dtype=np.float64)[:, 2], -1.0, 1.0)))


def ray_bundles(payload: Any, terminations: Sequence[str]) -> dict[str, np.ndarray]:
    """Sort recorded paths into five exclusive bundles.

    The split is by what happened to the ray, not by how it looks. A ray either
    left the scene or died in it, and if it left, it either left into the
    elevation band the rooftop model illuminates from or it did not. That last
    distinction is the one worth drawing: an escape outside the band contributes
    nothing under that model no matter how far it travelled.
    """
    sky = list(terminations).index("sky")
    escaped = payload["path_termination"] == sky
    bounced = payload["path_bounces"] > 0
    low, high = MODEL_BANDS["rooftop"]
    exit_elevation = elevation_deg(payload["path_exit_direction"])
    band = (exit_elevation >= low) & (exit_elevation <= high)
    return {
        "direct_sky_in_rooftop_band": escaped & ~bounced & band,
        "direct_sky_elsewhere": escaped & ~bounced & ~band,
        "multipath_to_rooftop_band": escaped & bounced & band,
        "multipath_elsewhere": escaped & bounced & ~band,
        "stopped_in_the_scene": ~escaped,
    }


def path_slice(offsets: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Vertex indices of a chosen set of paths, concatenated in path order.

    The paths are stored as one vertex array with a start offset per path, so
    picking a subset is a gather rather than a slice. Empty in gives empty out
    with the right dtype, which matters because an empty float index array cannot
    index anything.
    """
    indices = np.asarray(indices, dtype=np.int64)
    if indices.size == 0:
        return np.zeros(0, dtype=np.int64)
    return np.concatenate([np.arange(offsets[i], offsets[i + 1]) for i in indices])


def octahedra(centres: np.ndarray, radius: np.ndarray | float) -> tuple[np.ndarray, np.ndarray]:
    """A marker mesh: one eight sided diamond per centre, in one triangle soup."""
    unit = np.array(
        [[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0], [0.0, 0.0, -1.0]]
    )
    template = np.array(
        [[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]], dtype=np.int64
    )
    centres = np.asarray(centres, dtype=np.float64)
    count = centres.shape[0]
    scale = np.full(count, radius) if np.isscalar(radius) else np.asarray(radius, dtype=np.float64)
    vertices = (centres[:, None, :] + scale[:, None, None] * unit[None, :, :]).reshape(-1, 3)
    faces = (template[None, :, :] + 6 * np.arange(count)[:, None, None]).reshape(-1, 3)
    return vertices, faces


def unit_sphere(subdivisions: int = 2) -> tuple[np.ndarray, np.ndarray]:
    """A sphere by subdividing an octahedron, so no external primitive is needed."""
    vertices = np.array(
        [[1.0, 0, 0], [-1.0, 0, 0], [0, 1.0, 0], [0, -1.0, 0], [0, 0, 1.0], [0, 0, -1.0]], dtype=np.float64
    )
    faces = np.array(
        [[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]], dtype=np.int64
    )
    for _ in range(subdivisions):
        a, b, c = vertices[faces[:, 0]], vertices[faces[:, 1]], vertices[faces[:, 2]]
        base = vertices.shape[0]
        count = faces.shape[0]
        midpoints = np.concatenate([(a + b) / 2.0, (b + c) / 2.0, (c + a) / 2.0])
        vertices = np.concatenate([vertices, midpoints])
        ab = base + np.arange(count)
        bc = ab + count
        ca = bc + count
        faces = np.concatenate(
            [
                np.column_stack([faces[:, 0], ab, ca]),
                np.column_stack([ab, faces[:, 1], bc]),
                np.column_stack([ca, bc, faces[:, 2]]),
                np.column_stack([ab, bc, ca]),
            ]
        )
    return vertices / np.linalg.norm(vertices, axis=1, keepdims=True), faces


# ---------------------------------------------------------------------------
# The skyline rim
# ---------------------------------------------------------------------------


def rim_tube(slant: np.ndarray, width_scale: float) -> tuple[np.ndarray, np.ndarray]:
    """Drawn radius of the rim at a slant range, and how far above the tip it goes.

    The radius rises as the square root of the range, which is between constant
    world size and constant angular size, so the far rim neither swells nor
    vanishes. It carries no flux, so there is no second reading of that number to
    reconcile with the colour.
    """
    radius = width_scale * np.sqrt(np.maximum(np.asarray(slant, dtype=np.float64), 1.0e-6))
    return radius, RIM_LIFT_RADII * radius


def rim_shading(weight: np.ndarray, found: np.ndarray) -> tuple[Callable[[np.ndarray], np.ndarray], float, float]:
    """The flux ramp, and the two logarithms it spans. Shared, so nothing drifts.

    The rim and the connections that land on it are shaded by the same call, or a
    bright line could arrive at a dark roofline and the reader would have no way to
    know which of the two was lying.

    The ramp spans the middle eight tenths of the azimuths rather than the whole
    range, so a tenth of the rim saturates at each end. A single tip a metre and a
    half away carries eighty times the median at Korenmarkt, and shading to it
    leaves every other roofline in one dark colour. Most rooflines deliver within a
    factor of three of each other, so what is left after the tails are cut is 1.07
    decades at Korenmarkt rather than 1.58. The true range and the span shaded are
    both on the object.
    """
    live = np.asarray(weight)[np.asarray(found, dtype=bool)]
    low, high = (float(np.log10(value)) for value in np.percentile(live, [10, 90]))

    def shade(values: np.ndarray) -> np.ndarray:
        scaled = np.log10(np.maximum(np.asarray(values, dtype=np.float64), 1.0e-12))
        step = np.clip((scaled - low) / max(high - low, 1.0e-9), 0.0, 1.0)
        return colour_ramp(RIM_RAMP_FLOOR + (1.0 - RIM_RAMP_FLOOR) * step, 0.0, 1.0)

    return shade, low, high


def contiguous_runs(mask: np.ndarray) -> list[np.ndarray]:
    """Runs of consecutive true indices, joined across the wrap at azimuth zero.

    The rim closes on itself, so a run ending at the last azimuth and one starting
    at the first are one run through the seam rather than two.
    """
    index = np.flatnonzero(mask)
    if index.size == 0:
        return []
    runs = np.split(index, np.flatnonzero(np.diff(index) > 1) + 1)
    if len(runs) > 1 and runs[0][0] == 0 and runs[-1][-1] == mask.size - 1:
        runs = [np.concatenate([runs[-1], runs[0]])] + runs[1:-1]
    return runs


def rim_polylines(found: np.ndarray, offset: np.ndarray, *, break_fraction: float) -> list[np.ndarray]:
    """The rim as drawable polylines: index runs with a tip, cut where it steps.

    Two cuts, and they are different questions. An azimuth with no tip is open to
    the horizon and carries no source, so the rim has a hole there. An azimuth
    whose tip jumps is a corner: the silhouette has moved onto a facade behind the
    one it was on, and the two tips are both real and are not joined by a roofline.
    """
    pieces: list[np.ndarray] = []
    for run in contiguous_runs(found):
        if run.size == found.size:
            run = np.append(run, run[0])
        reach = np.linalg.norm(offset[run], axis=1)
        step = np.linalg.norm(np.diff(offset[run], axis=0), axis=1)
        cut = np.flatnonzero(step > break_fraction * np.minimum(reach[:-1], reach[1:])) + 1
        pieces += [piece for piece in np.split(run, cut) if piece.size >= 2]
    return pieces


def shorten_sky_legs(points: np.ndarray, lengths: np.ndarray, *, reach: float) -> np.ndarray:
    """Pull the last vertex of each polyline back to ``reach`` metres.

    Only the last one, and only along its own direction. A recorded path that
    escaped ends on a sky sphere 176 m out, which in a close view runs off the
    frame and takes the connections with it. A path that stopped in the scene has
    its last vertex sitting on the previous one and is left alone.
    """
    moved = np.array(points, dtype=np.float64, copy=True)
    end = np.cumsum(lengths) - 1
    span = moved[end] - moved[end - 1]
    distance = np.linalg.norm(span, axis=1)
    live = distance > 1.0e-9
    moved[end[live]] = moved[end[live] - 1] + reach * span[live] / distance[live, None]
    return moved


def camera_rotation(location: np.ndarray, target: np.ndarray) -> tuple[float, float, float]:
    """XYZ Euler angles aiming a Blender camera from ``location`` at ``target``.

    A Blender camera looks down its own -Z with +Y up, so this solves
    ``Rz(rz) Rx(rx) (0, 0, -1) = d``. That gives ``rx`` from ``-dz`` and ``rz``
    from ``(-dx, dy)``. Every other arrangement of those signs aims somewhere
    plausible looking and wrong, and the failure is a black frame or a view of the
    inside of a roof rather than an error.
    """
    direction = np.asarray(target, dtype=np.float64) - np.asarray(location, dtype=np.float64)
    direction = direction / max(float(np.linalg.norm(direction)), 1.0e-12)
    return (
        math.acos(float(np.clip(-direction[2], -1.0, 1.0))),
        0.0,
        math.atan2(-direction[0], direction[1]),
    )


def place_body(vertices: np.ndarray, hero: np.ndarray, ground_z: float) -> np.ndarray:
    """Stand the phantom on the local ground at the hero standpoint.

    The mesh arrives in metres with its own origin, so it is placed by its own feet
    rather than by assuming where that origin sits. Getting this wrong buries the
    phantom or floats it, and both look deliberate.
    """
    vertices = np.asarray(vertices, dtype=np.float64)
    centre = vertices.mean(axis=0)
    origin = np.array([centre[0], centre[1], vertices[:, 2].min()])
    return vertices - origin + np.array([hero[0], hero[1], ground_z])
