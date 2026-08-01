"""Which segmentation labels are surfaces and which are unmodelled objects.

A label that names a discrete object must never paint the background triangle
its camera ray happens to land on. The predicate here is the coarse test used by
the quadtree projection path: one set covering both movable objects and street
furniture.

``build_fishnet_surface.py`` deliberately keeps a finer split, separating
``TRANSIENT_WORDS`` from ``NON_SURFACE_WORDS`` so the rejection table can say
whether a face was dropped because something moved through the shot or because
the class is reconstructed as its own proxy geometry. The two are not merged
here because the coarse set is what the quadtree path has always used and its
outputs are still being compared against the fishnet ones.
"""

from __future__ import annotations

OBJECT_WORDS: frozenset[str] = frozenset(
    {
        "person",
        "rider",
        "bicyclist",
        "motorcyclist",
        "animal",
        "bird",
        "car",
        "truck",
        "bus",
        "vehicle",
        "motorcycle",
        "bicycle",
        "boat",
        "caravan",
        "trailer",
        "bollard",
        "bench",
        "trash can",
        "traffic light",
        "traffic sign",
        "street light",
        "pole",
        "fire hydrant",
        "bike rack",
    }
)


def is_object(label: str) -> bool:
    """True when a class label names a discrete object rather than a surface."""
    text = label.casefold()
    return any(word in text for word in OBJECT_WORDS)
