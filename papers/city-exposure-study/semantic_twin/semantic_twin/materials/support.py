"""Structural support rules for image evidence bound to mesh faces.

The support mesh already decides whether a triangle is ground, facade, roof,
or soffit. Image labels may refine the material of that surface. They may not
turn a road triangle into a vehicle, a rail, or a tree merely because one of
those occupied pixels projected onto the triangle.

This table is deliberately explicit and versioned. Mapillary Vistas has only
65 entity labels, and changing the role of one of them changes traced physics.
"""

from __future__ import annotations

from enum import StrEnum

from .binding import CLASS_NAMES

SUPPORT_COMPATIBILITY_VERSION = "v1-host-surface-majority"
HOST_SURFACE_CLASS_RULE = (
    "image material posterior only where compatible host-surface and spatially resolved embedded-surface "
    "evidence strictly outweighs incompatible object, volume, void, and unresolved evidence; geometric "
    "orientation rule on ties and everywhere else"
)


class SupportKind(StrEnum):
    """How an image entity relates to the structural support mesh."""

    GROUND_HOST = "ground_host"
    BUILT_HOST = "built_host"
    EMBEDDED_SUBFACE = "embedded_subface"
    VEGETATION_VOLUME = "vegetation_volume"
    NON_HOST_VOLUME = "non_host_volume"
    OBJECT = "object"
    VOID = "void"
    UNRESOLVED = "unresolved"


GROUND_HOST_ENTITIES = frozenset(
    {
        "Bike Lane",
        "Crosswalk - Plain",
        "Curb Cut",
        "Mountain",
        "Parking",
        "Pedestrian Area",
        "Pothole",
        "Road",
        "Sand",
        "Service Lane",
        "Sidewalk",
        "Snow",
        "Terrain",
    }
)

BUILT_HOST_ENTITIES = frozenset({"Bridge", "Building", "Tunnel", "Wall"})

# These are real surfaces, but they cover only part of a support triangle. The
# current walk product retains only a modal label and a ray count. It has no
# physical within-triangle coverage with which to mix the host and the insert.
EMBEDDED_SUBFACE_ENTITIES = frozenset(
    {
        "Catch Basin",
        "Curb",
        "Lane Marking - Crosswalk",
        "Lane Marking - General",
        "Manhole",
        "Rail Track",
    }
)

VEGETATION_ENTITIES = frozenset({"Vegetation"})
NON_HOST_VOLUME_ENTITIES = frozenset({"Water"})
VOID_ENTITIES = frozenset({"Sky"})
OBJECT_ENTITIES = frozenset(
    {
        "Banner",
        "Barrier",
        "Bench",
        "Bicycle",
        "Bicyclist",
        "Bike Rack",
        "Billboard",
        "Bird",
        "Boat",
        "Bus",
        "CCTV Camera",
        "Car",
        "Car Mount",
        "Caravan",
        "Ego Vehicle",
        "Fence",
        "Fire Hydrant",
        "Ground Animal",
        "Guard Rail",
        "Junction Box",
        "Mailbox",
        "Motorcycle",
        "Motorcyclist",
        "On Rails",
        "Other Rider",
        "Other Vehicle",
        "Person",
        "Phone Booth",
        "Pole",
        "Street Light",
        "Traffic Light",
        "Traffic Sign (Back)",
        "Traffic Sign (Front)",
        "Traffic Sign Frame",
        "Trailer",
        "Trash Can",
        "Truck",
        "Utility Pole",
        "Wheeled Slow",
    }
)


def entity_support_kind(entity: str | None) -> SupportKind:
    """Return the structural role of one dense semantic entity."""
    if entity in GROUND_HOST_ENTITIES:
        return SupportKind.GROUND_HOST
    if entity in BUILT_HOST_ENTITIES:
        return SupportKind.BUILT_HOST
    if entity in EMBEDDED_SUBFACE_ENTITIES:
        return SupportKind.EMBEDDED_SUBFACE
    if entity in VEGETATION_ENTITIES:
        return SupportKind.VEGETATION_VOLUME
    if entity in NON_HOST_VOLUME_ENTITIES:
        return SupportKind.NON_HOST_VOLUME
    if entity in VOID_ENTITIES:
        return SupportKind.VOID
    if entity in OBJECT_ENTITIES:
        return SupportKind.OBJECT
    return SupportKind.UNRESOLVED


def entity_supports_geometric_class(entity: str | None, geometric_class: int) -> bool:
    """Whether an entity can refine the host material of this triangle."""
    if not 0 <= int(geometric_class) < len(CLASS_NAMES):
        raise ValueError(f"geometric class {geometric_class} leaves {CLASS_NAMES}")
    kind = entity_support_kind(entity)
    if CLASS_NAMES[int(geometric_class)] == "ground":
        return kind == SupportKind.GROUND_HOST
    return kind == SupportKind.BUILT_HOST


def entity_supports_atlas_cell(entity: str | None, geometric_class: int) -> bool:
    """Whether a spatially resolved atlas cell can refine its host surface.

    Unlike the legacy whole-face products, the joint atlas retains the
    position of each observation within a support triangle. Ground inserts
    such as rails and lane markings can therefore affect only their own cells.
    """
    if not 0 <= int(geometric_class) < len(CLASS_NAMES):
        raise ValueError(f"geometric class {geometric_class} leaves {CLASS_NAMES}")
    kind = entity_support_kind(entity)
    if CLASS_NAMES[int(geometric_class)] == "ground":
        return kind in {SupportKind.GROUND_HOST, SupportKind.EMBEDDED_SUBFACE}
    return kind == SupportKind.BUILT_HOST
