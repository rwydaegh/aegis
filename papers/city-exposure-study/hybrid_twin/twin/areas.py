"""Working areas and authored viewpoints. No bpy, so every layer can import it."""

from __future__ import annotations

# (centre_x, centre_y, radius) in scene ENU metres.
AREAS: dict[str, tuple[float, float, float]] = {
    "graslei": (-58.5, 63.7, 58.0),   # the guild-house row, measured centroid
    "korenmarkt": (0.0, 0.0, 90.0),
    "block": (0.0, 0.0, 210.0),
}

# Authored hero viewpoints, as (eye_xy, target_xy, lens_mm).
#
# A hero shot is a composition. Deriving it from a building blob kept putting the
# camera inside an alley, so this is chosen, and chosen from evidence: an eight-plate
# contact sheet around the area settled it in one Blender run rather than eight
# guesses. The PCA derivation in `realise.hero_camera` remains the fallback for areas
# with no entry here, which is what a new city gets on its first pass.
CAMERAS: dict[str, tuple[tuple[float, float], tuple[float, float], float]] = {
    # From the north end, looking south down the water at the guild-house row.
    # Plate v03 of the contact sheet: reflections, trees and benches all in frame.
    "graslei": ((-96.0, 93.0), (-70.0, 52.0), 32.0),
}


# Authored small-cell deployments, as (position_xyz, aim_xyz).
#
# Also a choice, not a derivation. Aiming the panel at the "area centre" put it on
# the wrong facade, looking into the block, because the centroid of a study area is
# usually inside a building. A real operator picks a wall and a direction.
CELLS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    # On the Graslei quay frontage, 5.5 m up, looking south down the pavement so the
    # beam sweeps the walkway rather than the masonry behind it.
    "graslei": ((-72.5, 80.0, 55.9), (-72.5, 44.0, 51.9)),
}
