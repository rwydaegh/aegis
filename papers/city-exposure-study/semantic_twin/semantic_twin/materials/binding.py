"""Triangles that have a material, and where each one got it.

A :class:`SurfaceBinding` is the other half of the line this package draws. It
owns triangles: which class each one carries, how large it is, and which piece
of evidence decided it. It owns no permittivity at all. Ask it for
:meth:`SurfaceBinding.evaluate` and it hands back a
:class:`~.catalogue.MaterialTable` at whatever carrier you name.

Provenance is a required field and it is per triangle, not per run. That is the
whole reason this object exists. The eleven city headline was produced with
``--materials geometric``, and the coverage it reported was a zero written by
hand in the branch that never calls the image binding. Here the same zero is a
measurement: :attr:`SurfaceBinding.covered_fraction_by_area` counts the area
whose source is not :attr:`Provenance.GEOMETRIC`, so a run that used no
photographs says so because it is true and not because someone typed it.
"""

from __future__ import annotations

import enum
import pathlib
from dataclasses import dataclass
from typing import Any, Mapping

import numpy as np

from .catalogue import CLASS_NAMES, GEOMETRIC_CLASS_RULE, SURFACE_CLASSES, MaterialSpec, MaterialTable, load_table


class Provenance(enum.IntEnum):
    """Where one triangle's material came from.

    The integer values are written into ``face_source`` arrays, so they are as
    load bearing as the class index and are appended to rather than reordered.
    """

    #: The orientation rule. No photograph saw this triangle.
    GEOMETRIC = 0
    #: A single panorama's fishnet, joined onto the tracer mesh by centroid.
    IMAGE_FISHNET = 1
    #: The fused multi station walk, voting with Mapillary Vistas entity classes.
    IMAGE_WALK_ENTITY = 2
    #: The fused multi station walk, voting with the SAM 3 open vocabulary material axis.
    IMAGE_WALK_MATERIAL = 3
    #: A material drawn per face from a posterior distribution.
    POSTERIOR_DRAW = 4


@dataclass(frozen=True)
class SurfaceBinding:
    """Per triangle class and per triangle provenance over one mesh.

    ``face_class`` indexes ``class_names``, which is the same index a
    :class:`~.catalogue.MaterialTable` built from ``spec`` will use. A binding
    with no provenance, or with a class it has no spec for, refuses to be
    constructed.

    ``face_station`` is the one optional field. It names which camera's evidence
    decided each triangle, as an index into ``provenance["image_ids"]``, and it
    is what would let a run say "this material came from a camera we could not
    place". The registration record is already available, keyed on those same
    image ids, from :func:`semantic_twin.vision.provenance.station_registrations`.
    No route fills it yet: deciding which station won a multi station vote is a
    modelling choice, and it lands with the pass that uses it rather than here.
    """

    class_names: tuple[str, ...]
    spec: dict[str, MaterialSpec]
    face_class: np.ndarray
    face_source: np.ndarray
    face_area_m2: np.ndarray
    provenance: dict[str, Any]
    face_station: np.ndarray | None = None

    def __post_init__(self) -> None:
        count = self.face_class.shape[0]
        if self.face_source.shape != (count,) or self.face_area_m2.shape != (count,):
            raise ValueError(f"{count} faces but {self.face_source.shape} sources and {self.face_area_m2.shape} areas")
        if self.face_station is not None and self.face_station.shape != (count,):
            raise ValueError(f"{count} faces but {self.face_station.shape} stations")
        if count and (self.face_class.min() < 0 or self.face_class.max() >= len(self.class_names)):
            raise ValueError(f"face_class leaves the {len(self.class_names)} classes it names")
        known = {int(entry) for entry in Provenance}
        unknown = sorted(set(np.unique(self.face_source).tolist()) - known)
        if unknown:
            raise ValueError(f"face_source carries values {unknown} that name no Provenance member")
        missing = [name for name in self.class_names if name not in self.spec]
        if missing:
            raise ValueError(f"no material spec for {missing}")
        if not self.provenance:
            raise ValueError("a surface binding must record how its classes were decided")

    # The evidence bindings hand this straight back to ``load_table``, which is
    # why the name survives the rename of the field it reads.
    @property
    def class_binding(self) -> dict[str, MaterialSpec]:
        return self.spec

    @property
    def covered(self) -> np.ndarray:
        """Triangles whose class came from image evidence rather than orientation."""
        return self.face_source != int(Provenance.GEOMETRIC)

    @property
    def covered_fraction_by_face(self) -> float:
        return float(self.covered.mean())

    @property
    def covered_fraction_by_area(self) -> float:
        covered = self.covered
        return float(self.face_area_m2[covered].sum() / self.face_area_m2.sum())

    def area_fraction_by_source(self) -> dict[str, float]:
        """Surface area share of every provenance present, keyed by member name."""
        total = float(self.face_area_m2.sum())
        present = np.unique(self.face_source)
        return {
            Provenance(int(value)).name: float(self.face_area_m2[self.face_source == value].sum() / total)
            for value in present
        }

    def area_fraction_by_class(self) -> dict[str, float]:
        total = float(self.face_area_m2.sum())
        return {
            name: float(self.face_area_m2[self.face_class == i].sum() / total)
            for i, name in enumerate(self.class_names)
        }

    def evaluate(self, config_dir: pathlib.Path, frequency_hz: float, **kwargs: Any) -> MaterialTable:
        """Resolve this binding's classes into permittivities at one carrier."""
        kwargs.setdefault("class_rule", self.provenance.get("class_rule", GEOMETRIC_CLASS_RULE))
        return load_table(
            config_dir,
            frequency_hz,
            class_names=self.class_names,
            class_binding=self.spec,
            **kwargs,
        )


def classify_faces(
    vertices: np.ndarray,
    faces: np.ndarray,
    ground_datum_m: float,
    *,
    facade_cosine: float = 0.5,
    roof_height_m: float = 4.0,
) -> np.ndarray:
    """Assign a surface class index to every triangle.

    ``ground_datum_m`` is the z of the walkable surface. Upward facing faces
    within ``roof_height_m`` of it are ground, above it they are roof.
    """
    a = vertices[faces[:, 0]]
    b = vertices[faces[:, 1]]
    c = vertices[faces[:, 2]]
    normals = np.cross(b - a, c - a)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, np.where(norms > 0.0, norms, 1.0))
    centroid_z = (a[:, 2] + b[:, 2] + c[:, 2]) / 3.0

    index = np.full(faces.shape[0], CLASS_NAMES.index("facade"), dtype=np.int8)
    up = normals[:, 2] > facade_cosine
    down = normals[:, 2] < -facade_cosine
    index[up & (centroid_z <= ground_datum_m + roof_height_m)] = CLASS_NAMES.index("ground")
    index[up & (centroid_z > ground_datum_m + roof_height_m)] = CLASS_NAMES.index("roof")
    index[down] = CLASS_NAMES.index("soffit")
    return index


def class_area_fractions(face_class: np.ndarray, area: np.ndarray) -> dict[str, float]:
    total = float(area.sum())
    return {name: float(area[face_class == i].sum() / total) for i, name in enumerate(CLASS_NAMES)}


def geometric_binding(
    vertices: np.ndarray,
    faces: np.ndarray,
    areas: np.ndarray,
    ground_datum_m: float,
    *,
    facade_cosine: float = 0.5,
    roof_height_m: float = 4.0,
) -> SurfaceBinding:
    """The orientation rule as a binding, so its coverage is measured not asserted.

    Every triangle here is :attr:`Provenance.GEOMETRIC`, so
    :attr:`SurfaceBinding.covered_fraction_by_area` returns exactly 0.0. That is
    the same number the geometric branch of ``run_exposure.py`` writes today,
    arrived at by counting instead of by typing.
    """
    face_class = classify_faces(
        vertices,
        faces,
        ground_datum_m,
        facade_cosine=facade_cosine,
        roof_height_m=roof_height_m,
    ).astype(np.int64)
    return SurfaceBinding(
        class_names=tuple(CLASS_NAMES),
        spec=dict(SURFACE_CLASSES),
        face_class=face_class,
        face_source=np.full(face_class.shape[0], int(Provenance.GEOMETRIC), dtype=np.int8),
        face_area_m2=np.asarray(areas, dtype=np.float64),
        provenance={
            "class_rule": GEOMETRIC_CLASS_RULE,
            "facade_cosine": float(facade_cosine),
            "roof_height_m": float(roof_height_m),
            "ground_datum_m": float(ground_datum_m),
        },
    )


def extend_classes(
    materials: list[str],
    prefix: str,
    catalogue: Mapping[str, MaterialSpec],
) -> tuple[tuple[str, ...], dict[str, MaterialSpec]]:
    """The geometric classes, plus one prefixed class per evidence material.

    Every evidence binding lays its materials on top of the orientation rule
    rather than replacing it, because no run has ever covered a whole crop.
    That means the class table is always the four geometric classes followed by
    the evidence ones, and the offset between the two is ``len(CLASS_NAMES)``.
    """
    class_names = tuple(CLASS_NAMES) + tuple(f"{prefix}{name}" for name in materials)
    spec = dict(SURFACE_CLASSES)
    for name in materials:
        spec[f"{prefix}{name}"] = catalogue[name]
    return class_names, spec
