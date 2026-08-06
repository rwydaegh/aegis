"""Bind a material posterior to the tracer instead of a material label.

:func:`~.evidence.bind_fishnet` takes the argmax of a per triangle vote and
gives the tracer one row. That is a point estimate of a quantity nobody
measured, and it throws away the only part of the material model that carries
the uncertainty. This module keeps the distribution.

There are exactly two defensible ways to trace a surface whose material is
uncertain and they answer different questions.

Draw a material per face from the posterior. Every facet stays a real material,
which is what a square metre of wall actually is, and repeating the draw with
another seed gives the spread of the answer under material ignorance. That is an
error bar the current pipeline cannot produce at all.

Or mix the reflectance in power. That is the ensemble mean over the draws, so it
is the right thing to quote as a central value and the wrong thing to trace on
its own, because no wall has it.

Both are exposed. The draw is the default because the tracer wants a class per
face, and the mean is available in closed form through
:func:`~.stack.posterior_power_reflectance` for the arithmetic that does not
need a trace.

This is a third evidence route and it does not touch the other two. It composes
with the geometric rule in the same way: the geometric classes stay in the
table, and only the classes a posterior was supplied for are overwritten.
"""

from __future__ import annotations

import numpy as np

from .binding import CLASS_NAMES, Provenance, SurfaceBinding, extend_classes
from .catalogue import IMAGE_MATERIALS, MATERIAL_SUBSTITUTION

#: Prefix every drawn class name carries in the class table.
POSTERIOR_PREFIX = "posterior_"


def _traceable(posterior: dict[str, float]) -> dict[str, float]:
    """Drop the unknown mass and renormalise.

    An unknown patch has no ITU row and cannot be traced. Spreading its mass over
    the materials that do have rows is the honest reading of "this is a facade
    and I cannot tell which kind", and it is stated here rather than hidden
    because the alternative, silently assigning unknown to a default row, is the
    failure this module exists to remove.
    """
    mass: dict[str, float] = {}
    for name, value in posterior.items():
        if name == "unknown" or value <= 0.0:
            continue
        row = name if name in IMAGE_MATERIALS else MATERIAL_SUBSTITUTION.get(name)
        if row is None or row not in IMAGE_MATERIALS:
            raise ValueError(f"posterior names a material with no ITU row and no substitution: {name}")
        mass[row] = mass.get(row, 0.0) + float(value)
    total = sum(mass.values())
    if total <= 0.0:
        raise ValueError("posterior has no traceable mass")
    return {name: value / total for name, value in mass.items()}


def bind_posterior(
    areas: np.ndarray,
    geometric_class: np.ndarray,
    posterior_by_class: dict[str, dict[str, float]],
    *,
    seed: int = 0,
    face_posterior: np.ndarray | None = None,
    face_posterior_materials: tuple[str, ...] | None = None,
    face_posterior_mask: np.ndarray | None = None,
) -> SurfaceBinding:
    """Draw a material for every face of the named geometric classes.

    ``posterior_by_class`` maps a geometric class name, typically ``facade``, to
    a distribution over the RF vocabulary. Faces of classes not named keep their
    geometric row.

    ``face_posterior`` optionally overrides the class level distribution on the
    faces where ``face_posterior_mask`` is true, which is how per face image
    evidence enters. The class level distribution then covers the rest, which at
    Korenmarkt is most of the scene, because street level capture reaches a few
    percent of the surface and no amount of image evidence changes that.
    """
    rng = np.random.default_rng(seed)
    face_class = np.asarray(geometric_class, dtype=np.int64).copy()
    materials = sorted(IMAGE_MATERIALS)
    class_names, spec = extend_classes(materials, POSTERIOR_PREFIX, IMAGE_MATERIALS)
    offset = len(CLASS_NAMES)

    drawn = np.zeros(face_class.size, dtype=bool)
    for name, posterior in posterior_by_class.items():
        if name not in CLASS_NAMES:
            raise ValueError(f"{name!r} is not a geometric class, expected one of {CLASS_NAMES}")
        rows = np.flatnonzero(np.asarray(geometric_class) == CLASS_NAMES.index(name))
        if rows.size == 0:
            continue
        mass = _traceable(posterior)
        names = sorted(mass)
        probability = np.array([mass[n] for n in names])
        picks = rng.choice(len(names), size=rows.size, p=probability)
        face_class[rows] = np.array([offset + materials.index(names[p]) for p in picks], dtype=np.int64)
        drawn[rows] = True

    if face_posterior is not None:
        if face_posterior_materials is None or face_posterior_mask is None:
            raise ValueError("face_posterior needs both its material names and its mask")
        rows = np.flatnonzero(np.asarray(face_posterior_mask))
        table = np.asarray(face_posterior, dtype=np.float64)[rows]
        keep = [i for i, n in enumerate(face_posterior_materials) if n in IMAGE_MATERIALS]
        table = table[:, keep]
        totals = table.sum(axis=1)
        usable = totals > 0.0
        rows, table, totals = rows[usable], table[usable], totals[usable]
        cumulative = np.cumsum(table / totals[:, None], axis=1)
        picks = np.argmax(rng.random(rows.size)[:, None] < cumulative, axis=1)
        chosen = [face_posterior_materials[keep[p]] for p in picks]
        face_class[rows] = np.array([offset + materials.index(name) for name in chosen], dtype=np.int64)
        drawn[rows] = True

    areas = np.asarray(areas, dtype=np.float64)
    return SurfaceBinding(
        class_names=class_names,
        spec=spec,
        face_class=face_class,
        face_source=np.where(drawn, int(Provenance.POSTERIOR_DRAW), int(Provenance.GEOMETRIC)).astype(np.int8),
        face_area_m2=areas,
        provenance={
            "rule": "one material drawn per face from its posterior, never an argmax and never a blended medium",
            "seed": seed,
            "posterior_by_class": posterior_by_class,
            "face_posterior_faces": int(np.count_nonzero(face_posterior_mask))
            if face_posterior_mask is not None
            else 0,
            "unknown_policy": "unknown mass is dropped and the remainder renormalised, because unknown has no ITU row",
        },
    )


def sample_face_materials(
    posterior_by_face: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Draw one material index per face from its own posterior.

    This is the alternative to averaging, and it is the physically honest one. A
    square metre of wall is one material, not a blend, so a draw keeps every
    facet a real material and puts the ignorance where it belongs, in the spread
    of the answer over repeated draws, rather than in a fictitious average
    medium that no wall is made of.
    """
    posterior_by_face = np.asarray(posterior_by_face, dtype=np.float64)
    if posterior_by_face.ndim != 2:
        raise ValueError("posterior_by_face must be [faces, materials]")
    totals = posterior_by_face.sum(axis=1, keepdims=True)
    if np.any(totals <= 0.0):
        raise ValueError("every face needs a posterior carrying some mass")
    cumulative = np.cumsum(posterior_by_face / totals, axis=1)
    draws = rng.random(posterior_by_face.shape[0])[:, None]
    return np.argmax(draws < cumulative, axis=1).astype(np.int64)


def realised_composition(binding: SurfaceBinding) -> dict[str, float]:
    """Area share of each drawn material, keyed by its bare vocabulary name.

    What the draw actually produced, which is not the posterior it was drawn
    from. On a mesh with few facade triangles the two differ visibly, and that
    difference is the sampling error the draw exists to expose.
    """
    fractions = binding.area_fraction_by_class()
    return {
        name[len(POSTERIOR_PREFIX) :]: value
        for name, value in fractions.items()
        if name.startswith(POSTERIOR_PREFIX) and value > 0.0
    }
