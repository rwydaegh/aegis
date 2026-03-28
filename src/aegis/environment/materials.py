"""EM material properties (ITU-R P.2040) and vertex-color classification."""

from __future__ import annotations

import colorsys

from aegis.environment import MATERIAL_EM_PROPERTIES, MaterialType


def get_em_properties(
    material: MaterialType,
    freq_hz: float = 28e9,
    overrides: dict | None = None,
) -> tuple[float, float]:
    """Return (eps_r, sigma) for a material at given frequency.

    If overrides contains a key matching the material name (lowercase),
    those values are used instead of the defaults.
    """
    name = material.name.lower()
    if overrides and name in overrides:
        props = overrides[name]
        return props["eps_r"], props["sigma"]
    props = MATERIAL_EM_PROPERTIES[material]
    return props["eps_r"], props["sigma"]


def classify_color(r: int, g: int, b: int) -> MaterialType:
    """Classify an RGB vertex color (0-255) into a MaterialType.

    Uses HSV-based heuristics similar to scene_data.classify_material().
    """
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    h360 = h * 360

    # very dark -> asphalt
    if v < 0.30:
        return MaterialType.ASPHALT

    # low saturation -> concrete or asphalt
    if s < 0.15:
        if v < 0.45:
            return MaterialType.ASPHALT
        return MaterialType.CONCRETE

    # blue -> water
    if 190 < h360 < 260 and s > 0.3:
        return MaterialType.WATER

    # green -> vegetation
    if 80 < h360 < 170 and s > 0.2:
        return MaterialType.VEGETATION

    # orange-brown -> brick
    if 10 < h360 < 45 and s > 0.3:
        return MaterialType.BRICK

    # yellow-ish -> wood
    if 35 < h360 < 65 and s > 0.2:
        return MaterialType.WOOD

    # high value, low saturation metallic
    if v > 0.7 and s < 0.1:
        return MaterialType.METAL

    return MaterialType.CONCRETE
