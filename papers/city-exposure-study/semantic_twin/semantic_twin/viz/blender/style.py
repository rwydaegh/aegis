"""Colours, ramps and drawn sizes for the propagation blend.

Presentation only. Nothing here can change a number, and every constant carries
the reason it has the value it has, because a drawn size chosen to look right at
one square is a bug at the next one. The rim break fraction is the clearest case:
it is 0.15 because a flat wall seen at 85 degrees of grazing moves 0.10 of its own
range per half degree of azimuth, so 0.15 cuts at a street opening and never along
a facade.
"""

from __future__ import annotations

import numpy as np

#: The three illumination models a trace is scored under.
MODEL_NAMES: tuple[str, ...] = ("isotropic", "rooftop", "street_small_cell")


def angular_law_sample_object_name(model: str) -> str:
    """A Blender name that cannot be mistaken for a counted transmitter set."""
    return f"angular_law_samples_{model}_not_counted_sites"


def angular_law_sample_metadata(model: str) -> dict[str, str | bool]:
    """Reading notes for the hidden point sample used to picture one law."""
    return {
        "model": model,
        "role": "hidden Monte Carlo picture of the analytic angular illumination law",
        "marker_points_used_in_exposure": False,
        "analytic_population_defines_scored_angular_law": True,
        "placement": "sampled from the stated height and range bands, not fitted to the city mesh",
        "roofline_evidence_relation": (
            "separate geometry evidence; in a production blend it supplies no exposure value"
        ),
        "why_hidden": "these samples float in the model bands rather than marking mapped transmitter sites",
    }


#: Elevation support of each directional model, degrees. Only used to sort the
#: recorded rays into the bundle that carries that model's power, so a reader can
#: see which escapes matter and which merely escape.
MODEL_BANDS: dict[str, tuple[float, float]] = {"rooftop": (3.1, 60.1), "street_small_cell": (0.95, 33.0)}

#: Surface class tints, matching the class order of
#: ``semantic_twin.materials.CLASS_NAMES``.
CLASS_TINT: dict[str, tuple[float, float, float]] = {
    "ground": (0.28, 0.27, 0.26),
    "facade": (0.55, 0.42, 0.34),
    "roof": (0.34, 0.36, 0.42),
    "soffit": (0.22, 0.23, 0.25),
}

#: Ray bundle name -> (emission colour, whether it is on by default).
RAY_STYLE: dict[str, tuple[tuple[float, float, float], bool]] = {
    "direct_sky_in_rooftop_band": ((1.00, 0.42, 0.10), True),
    "direct_sky_elsewhere": ((0.16, 0.52, 0.95), True),
    "multipath_to_rooftop_band": ((1.00, 0.78, 0.30), True),
    "multipath_elsewhere": ((0.30, 0.75, 0.85), True),
    "stopped_in_the_scene": ((0.45, 0.10, 0.22), True),
}

#: Leg index -> emission colour. The first leg is the one that left the
#: standpoint, the second is the one after the first reflection, and so on. The
#: budget stops at three reflections because the panoramas measure the material
#: for the first two, so the fourth entry is everything past what the evidence
#: covers and is deliberately the dimmest.
BOUNCE_STYLE: tuple[tuple[tuple[float, float, float], str], ...] = (
    ((1.00, 0.55, 0.12), "leg_0_before_any_bounce"),
    ((0.98, 0.85, 0.30), "leg_1_after_one_bounce"),
    ((0.45, 0.85, 0.95), "leg_2_after_two_bounces"),
    ((1.00, 0.20, 0.85), "leg_3_and_beyond"),
)

#: Nine anchors of the matplotlib inferno map. Blender ships no matplotlib and
#: adding one to a headless render for a colour ramp would be absurd.
INFERNO = np.array(
    [
        [0.001462, 0.000466, 0.013866],
        [0.087411, 0.044556, 0.224813],
        [0.258234, 0.038571, 0.406485],
        [0.416331, 0.090203, 0.432943],
        [0.578304, 0.148039, 0.404411],
        [0.735683, 0.215906, 0.330245],
        [0.865006, 0.316822, 0.226055],
        [0.954506, 0.468744, 0.099874],
        [0.988260, 0.652325, 0.211364],
    ]
)

#: Where the rim polyline is cut. Two azimuths half a degree apart whose tips are
#: further apart than this fraction of their own range are not one roofline: the
#: silhouette has stepped across a street opening onto a facade behind it, and
#: joining them draws a wire across the square. A flat wall seen at 85 degrees of
#: grazing moves 0.10 of its range per half degree, so 0.15 cuts at the openings
#: and never along a facade.
RIM_BREAK_FRACTION = 0.15

#: Inferno starts at black. A rim shaded from its black end loses the rooflines
#: that carry least power rather than merely dimming them, so the ramp is entered
#: at this fraction of its length and the dimmest azimuth is still a visible line.
RIM_RAMP_FLOOR = 0.18

#: Display gain on the rim, its sites and the connections that land on it. The
#: mesh is sunlit and an emitter at one is dimmer than the roof it is drawn over,
#: which stops a rim of light looking like light. It multiplies every value on the
#: layer alike, so no ordering and no ratio moves.
RIM_EMISSION_STRENGTH = 2.0

#: The rim is drawn this many tube radii above the tip. A tip is the top of the
#: silhouette and on a photogrammetric roof it is often a ridge behind the facade,
#: so a tube centred on it sits half inside the roof and disappears. Lifting it
#: puts the whole tube in the sky the tip borders on. Nothing else moves: the
#: height is the only coordinate touched and it is recorded.
RIM_LIFT_RADII = 2.0

#: Marker radius, in tube radii. Five is about two metres at a roofline thirty
#: metres off, which is what it takes to read a site from an overview of a square
#: rather than only from the pavement.
RIM_SITE_RADII = 5.0

#: The connection colours. Clear is bright and blocked is dark, and that is the
#: whole of the default reading, because the visibility term is the one thing a
#: connection carries that the rim it lands on does not. How much the site
#: delivers is on the rim, and is a colour layer away on the connection too.
NEE_CLEAR_COLOUR = (1.0, 0.96, 0.86)
NEE_BLOCKED_COLOUR = (0.24, 0.05, 0.09)
NEE_RAY_COLOUR = (0.62, 0.44, 0.22)

#: The animation uses fixed colours because each one names a role rather than a
#: measured scalar. The escaped leg is pale blue so it cannot be mistaken for a
#: finite surface-to-surface segment. NEE origins and endpoints use different
#: marker colours, while clear and blocked visibility lines keep the still
#: figure's white and dark red convention.
ANIMATION_PATH_COLOUR = (1.0, 0.57, 0.12)
ANIMATION_PROXY_COLOUR = (0.40, 0.82, 1.0)
ANIMATION_NEE_CHAIN_COLOUR = (0.70, 0.44, 0.16)
ANIMATION_CLEAR_CONNECTION_COLOUR = NEE_CLEAR_COLOUR
ANIMATION_BLOCKED_CONNECTION_COLOUR = (1.0, 0.04, 0.07)
ANIMATION_SCATTER_COLOUR = (1.0, 0.22, 0.72)
ANIMATION_SOURCE_COLOUR = (0.65, 1.0, 0.18)


def colour_ramp(values: np.ndarray, low: float, high: float) -> np.ndarray:
    """Map values to inferno RGBA, clamped to ``[low, high]``."""
    span = max(high - low, 1.0e-30)
    t = np.clip((np.asarray(values, dtype=np.float64) - low) / span, 0.0, 1.0)
    position = t * (INFERNO.shape[0] - 1)
    lower = np.floor(position).astype(int)
    upper = np.minimum(lower + 1, INFERNO.shape[0] - 1)
    blend = (position - lower)[:, None]
    rgb = INFERNO[lower] * (1.0 - blend) + INFERNO[upper] * blend
    return np.column_stack([rgb, np.ones(rgb.shape[0])])


def log_ramp(values: np.ndarray, floor: float = 1.0) -> tuple[np.ndarray, float, float]:
    """Inferno over the base ten logarithm, for counts that span decades."""
    scaled = np.log10(np.maximum(np.asarray(values, dtype=np.float64), floor))
    low, high = float(scaled.min()), float(scaled.max())
    return colour_ramp(scaled, low, max(high, low + 1.0e-6)), low, high


def categorical_colours(codes: np.ndarray, palette: np.ndarray) -> np.ndarray:
    """RGBA for integer codes, with anything outside the palette drawn as grey."""
    codes = np.asarray(codes, dtype=np.int64)
    inside = (codes >= 0) & (codes < palette.shape[0])
    rgb = np.full((codes.size, 3), 0.35)
    rgb[inside] = palette[codes[inside]]
    return np.column_stack([rgb, np.ones(codes.size)])
