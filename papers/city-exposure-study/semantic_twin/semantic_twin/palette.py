"""Stable display colours for semantic classes.

These are presentation only. Nothing in the propagation or evidence path reads
them, so changing a colour cannot change a result. The named entries keep the
handful of classes that dominate a street scene recognisable between renders,
and everything else falls back to a golden-ratio hue walk so two adjacent class
ids never land on the same hue.
"""

from __future__ import annotations

import colorsys

PREFERRED_COLOURS: dict[str, tuple[float, float, float, float]] = {
    "building": (0.03, 0.64, 0.95, 1.0),
    "vegetation": (0.08, 0.82, 0.25, 1.0),
    "pedestrian area": (0.98, 0.65, 0.18, 1.0),
    "road": (0.46, 0.50, 0.56, 1.0),
    "on rails": (0.96, 0.86, 0.10, 1.0),
    "fence": (1.0, 0.30, 0.08, 1.0),
    "billboard": (0.96, 0.08, 0.65, 1.0),
    "rail track": (0.70, 0.24, 0.92, 1.0),
    "terrain": (0.55, 0.30, 0.10, 1.0),
}


def fallback_colour(class_id: int) -> tuple[float, float, float, float]:
    """Deterministic RGBA for a class with no preferred colour."""
    rgb = colorsys.hsv_to_rgb((class_id * 0.61803398875) % 1.0, 0.72, 0.95)
    return (*rgb, 1.0)
