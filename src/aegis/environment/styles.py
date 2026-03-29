"""Building style system for facade colors, window placement, and per-building randomization.

Simplified port of blosm's PML/grammar system: no parser, just Python dataclasses and dicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------
# Color palettes (RGB tuples, 0-1 float range)
# ---------------------------------------------------------------------------

BRICK_COLORS: tuple[tuple[float, float, float], ...] = (
    (0.698, 0.278, 0.176),  # classic red brick
    (0.780, 0.404, 0.259),  # light terracotta
    (0.588, 0.231, 0.145),  # dark red brick
    (0.643, 0.369, 0.224),  # warm brown brick
    (0.714, 0.486, 0.337),  # sandy brick
)

PLASTER_COLORS: tuple[tuple[float, float, float], ...] = (
    (0.902, 0.882, 0.863),  # off-white plaster
    (0.851, 0.831, 0.800),  # warm light gray
    (0.922, 0.898, 0.859),  # cream
    (0.800, 0.792, 0.769),  # cool light gray
    (0.878, 0.851, 0.812),  # beige
)

CONCRETE_COLORS: tuple[tuple[float, float, float], ...] = (
    (0.627, 0.627, 0.627),  # medium gray
    (0.714, 0.714, 0.706),  # light gray
    (0.549, 0.549, 0.549),  # dark gray
)

GLASS_COLOR: tuple[float, float, float] = (0.404, 0.616, 0.749)  # blue-green glass

DOOR_COLOR: tuple[float, float, float] = (0.259, 0.169, 0.102)  # dark brown


# ---------------------------------------------------------------------------
# Window and door parameters
# ---------------------------------------------------------------------------


@dataclass
class WindowParams:
    """Parameters governing window placement on a facade."""

    width: float = 1.2
    height: float = 1.8
    margin_left: float = 1.0
    margin_right: float = 1.0
    sill_height: float = 0.9

    @property
    def total_width(self) -> float:
        """Horizontal space consumed by one window cell (margins + window)."""
        return self.margin_left + self.width + self.margin_right

    def count_for_width(self, facade_width: float) -> int:
        """Number of windows that fit across a facade of the given width."""
        return int(facade_width / self.total_width)


@dataclass
class DoorParams:
    """Parameters governing door placement on a facade."""

    width: float = 1.2
    height: float = 2.1
    margin_left: float = 1.0
    margin_right: float = 1.0

    @property
    def total_width(self) -> float:
        """Horizontal space consumed by one door cell (margins + door)."""
        return self.margin_left + self.width + self.margin_right


# ---------------------------------------------------------------------------
# Building style
# ---------------------------------------------------------------------------

_DEFAULT_PLASTER_PALETTE = PLASTER_COLORS
_DEFAULT_ROOF_COLOR: tuple[float, float, float] = (0.400, 0.400, 0.400)


@dataclass
class BuildingStyle:
    """Visual and procedural parameters for a building type."""

    level_height: float = 3.0
    ground_level_height: float = 3.5
    num_levels: int | None = None
    bottom_height: float = 0.5

    window: WindowParams = field(default_factory=WindowParams)
    door: DoorParams = field(default_factory=DoorParams)

    has_ground_floor_doors: bool = True
    cladding_material: str = "plaster"
    cladding_palette: tuple[tuple[float, float, float], ...] = field(default_factory=lambda: _DEFAULT_PLASTER_PALETTE)
    roof_color: tuple[float, float, float] = field(default_factory=lambda: _DEFAULT_ROOF_COLOR)

    def facade_color(self, seed: int) -> tuple[float, float, float]:
        """Return a deterministic facade color from the palette using the given seed."""
        rng = np.random.RandomState(seed)
        idx = rng.randint(0, len(self.cladding_palette))
        return self.cladding_palette[idx]

    def compute_num_levels(self, height: float) -> int:
        """Derive number of levels from building height."""
        if self.num_levels is not None:
            return self.num_levels
        # Subtract ground level height, then count upper floors
        remaining = max(0.0, height - self.ground_level_height)
        upper = int(remaining / self.level_height)
        return 1 + upper  # at least the ground level


# ---------------------------------------------------------------------------
# Style library
# ---------------------------------------------------------------------------


class StyleLibrary:
    """Registry mapping building type names to BuildingStyle instances."""

    def __init__(self) -> None:
        self._styles: dict[str, BuildingStyle] = dict(_STYLES)

    def get(self, name: str) -> BuildingStyle:
        """Return the style for the given name, falling back to 'default'."""
        return self._styles.get(name, self._styles["default"])

    def register(self, name: str, style: BuildingStyle) -> None:
        """Register a new style or overwrite an existing one."""
        self._styles[name] = style


# ---------------------------------------------------------------------------
# Built-in style definitions
# ---------------------------------------------------------------------------

_STYLES: dict[str, BuildingStyle] = {
    "default": BuildingStyle(
        level_height=3.0,
        ground_level_height=3.5,
        cladding_material="plaster",
        cladding_palette=PLASTER_COLORS,
        roof_color=(0.400, 0.400, 0.400),
    ),
    "house": BuildingStyle(
        level_height=2.8,
        ground_level_height=3.0,
        num_levels=2,
        cladding_material="brick",
        cladding_palette=BRICK_COLORS,
        roof_color=(0.349, 0.149, 0.102),  # terracotta roof
    ),
    "detached": BuildingStyle(
        level_height=2.8,
        ground_level_height=3.0,
        num_levels=2,
        cladding_material="brick",
        cladding_palette=BRICK_COLORS,
        roof_color=(0.302, 0.200, 0.149),  # dark brown roof
    ),
    "apartments": BuildingStyle(
        level_height=3.0,
        ground_level_height=3.5,
        cladding_material="plaster",
        cladding_palette=PLASTER_COLORS,
        roof_color=(0.451, 0.451, 0.451),
        has_ground_floor_doors=True,
    ),
    "office": BuildingStyle(
        level_height=3.5,
        ground_level_height=4.0,
        cladding_material="glass",
        cladding_palette=((0.404, 0.616, 0.749), (0.369, 0.565, 0.710), (0.447, 0.647, 0.780)),
        roof_color=(0.300, 0.300, 0.310),
        window=WindowParams(width=1.5, height=2.5, margin_left=0.5, margin_right=0.5, sill_height=0.5),
        has_ground_floor_doors=True,
    ),
    "commercial": BuildingStyle(
        level_height=4.0,
        ground_level_height=4.5,
        cladding_material="plaster",
        cladding_palette=PLASTER_COLORS,
        roof_color=(0.400, 0.400, 0.400),
        has_ground_floor_doors=True,
    ),
    "industrial": BuildingStyle(
        level_height=5.0,
        ground_level_height=5.0,
        num_levels=1,
        cladding_material="concrete",
        cladding_palette=CONCRETE_COLORS,
        roof_color=(0.500, 0.490, 0.478),
        has_ground_floor_doors=True,
        window=WindowParams(width=1.5, height=1.5, margin_left=1.5, margin_right=1.5, sill_height=1.5),
    ),
    "retail": BuildingStyle(
        level_height=4.0,
        ground_level_height=4.5,
        num_levels=1,
        cladding_material="plaster",
        cladding_palette=PLASTER_COLORS,
        roof_color=(0.400, 0.400, 0.400),
        has_ground_floor_doors=True,
        window=WindowParams(width=2.0, height=3.0, margin_left=0.5, margin_right=0.5, sill_height=0.3),
    ),
    "garage": BuildingStyle(
        level_height=3.0,
        ground_level_height=3.0,
        num_levels=1,
        cladding_material="concrete",
        cladding_palette=CONCRETE_COLORS,
        roof_color=(0.500, 0.490, 0.478),
        has_ground_floor_doors=True,
        window=WindowParams(width=0.8, height=0.6, margin_left=1.0, margin_right=1.0, sill_height=2.0),
    ),
}

# Palette lookup by building:material tag value
_MATERIAL_PALETTE_MAP: dict[str, tuple[tuple[float, float, float], ...]] = {
    "brick": BRICK_COLORS,
    "bricks": BRICK_COLORS,
    "plaster": PLASTER_COLORS,
    "render": PLASTER_COLORS,
    "concrete": CONCRETE_COLORS,
    "glass": ((GLASS_COLOR),),
}


# ---------------------------------------------------------------------------
# resolve_style
# ---------------------------------------------------------------------------


def resolve_style(tags: dict[str, str]) -> BuildingStyle:
    """Resolve a BuildingStyle from OSM building tags.

    Looks up building type in the style library, then applies overrides from
    ``building:levels`` and ``building:material`` tags.

    Args:
        tags: OSM tag dict (e.g. from ``_parse_tags``).

    Returns:
        A new BuildingStyle (copy) with tag-derived overrides applied.
    """
    import dataclasses

    building_type = tags.get("building", "default")
    lib = StyleLibrary()
    base = lib.get(building_type)

    # Copy so we don't mutate the library entry
    style = dataclasses.replace(base)

    # Override num_levels from tag
    if "building:levels" in tags:
        import contextlib

        with contextlib.suppress(ValueError):
            style = dataclasses.replace(style, num_levels=int(tags["building:levels"]))

    # Override palette from building:material tag
    mat = tags.get("building:material", "").lower()
    if mat in _MATERIAL_PALETTE_MAP:
        palette = _MATERIAL_PALETTE_MAP[mat]
        style = dataclasses.replace(style, cladding_palette=palette, cladding_material=mat)

    return style
