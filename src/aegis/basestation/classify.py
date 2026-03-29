"""Archetype classification and element grid inference for base stations.

Three archetypes:
- mmimo: high-gain 5G panels with digital beamforming (e.g. Ericsson AIR 4518)
- sector: conventional sector panels with fixed patterns
- small_cell: low-gain omnidirectional or small box antennas
"""

from __future__ import annotations

# Default standard grids [n_h, n_v] per archetype. Configurable via config.
DEFAULT_GRIDS: dict[str, list[tuple[int, int]]] = {
    "mmimo": [(4, 4), (4, 8), (8, 8), (8, 16)],
    "sector": [(1, 2), (1, 4), (2, 4), (2, 8)],
    "small_cell": [(1, 1), (2, 2)],
}

DEFAULT_ELEMENT_GAIN_DBI = 5.0
DEFAULT_MMIMO_THRESHOLD = 20.0
DEFAULT_SMALL_CELL_THRESHOLD = 10.0


def classify_antenna(
    gain_dbi: float,
    technology: str | None,
    freq_mhz: float = 0.0,
    h_bw: float = 0.0,
    v_bw: float = 0.0,
    *,
    mmimo_threshold: float = DEFAULT_MMIMO_THRESHOLD,
    small_cell_threshold: float = DEFAULT_SMALL_CELL_THRESHOLD,
) -> str:
    """Classify a base station antenna into an archetype.

    Returns one of: "mmimo", "sector", "small_cell".
    """
    tech = (technology or "").upper()
    is_5g = "5G" in tech

    if gain_dbi >= mmimo_threshold and is_5g:
        return "mmimo"
    if gain_dbi < small_cell_threshold:
        return "small_cell"
    return "sector"


def infer_element_grid(
    archetype: str,
    gain_dbi: float,
    element_gain_dbi: float = DEFAULT_ELEMENT_GAIN_DBI,
    *,
    standard_grids: dict[str, list[tuple[int, int]]] | None = None,
) -> tuple[int, int]:
    """Infer antenna element grid (n_h, n_v) from gain and archetype.

    Computes raw element count from array gain, then snaps to the nearest
    standard grid for the archetype. For mmimo, n_v >= n_h (tall panels).
    For sector, n_h is 1 or 2 (cross-pol columns).
    """
    grids = standard_grids or DEFAULT_GRIDS
    candidates = grids.get(archetype, [(1, 1)])

    array_gain_db = gain_dbi - element_gain_dbi
    if array_gain_db <= 0:
        return candidates[0]

    n_raw = 10 ** (array_gain_db / 10)

    best = candidates[0]
    best_dist = float("inf")
    for grid in candidates:
        n_total = grid[0] * grid[1]
        dist = abs(n_total - n_raw)
        if dist < best_dist:
            best_dist = dist
            best = grid
    return best


def compute_panel_dimensions(
    n_h: int,
    n_v: int,
    freq_mhz: float,
    *,
    margin: float = 0.02,
    default_freq_mhz: float = 2100.0,
) -> tuple[float, float]:
    """Compute physical panel dimensions from element grid and frequency.

    Uses half-wavelength spacing. Returns (width_m, height_m).
    """
    freq = freq_mhz if freq_mhz > 0 else default_freq_mhz
    c = 299_792_458.0
    wavelength = c / (freq * 1e6)
    spacing = wavelength / 2

    width = max((n_h - 1) * spacing + margin, margin * 2)
    height = max((n_v - 1) * spacing + margin, margin * 2)
    return width, height


def classify_basestation(
    gain_dbi: float,
    technology: str | None,
    freq_mhz: float = 0.0,
    h_bw: float = 0.0,
    v_bw: float = 0.0,
    *,
    mmimo_threshold: float = DEFAULT_MMIMO_THRESHOLD,
    small_cell_threshold: float = DEFAULT_SMALL_CELL_THRESHOLD,
    element_gain_dbi: float = DEFAULT_ELEMENT_GAIN_DBI,
    standard_grids: dict[str, list[tuple[int, int]]] | None = None,
    margin: float = 0.02,
    default_freq_mhz: float = 2100.0,
) -> dict:
    """Full classification: archetype + grid + panel dimensions.

    Returns dict with keys: archetype, n_h, n_v, panel_width_m, panel_height_m.
    """
    archetype = classify_antenna(
        gain_dbi,
        technology,
        freq_mhz,
        h_bw,
        v_bw,
        mmimo_threshold=mmimo_threshold,
        small_cell_threshold=small_cell_threshold,
    )
    n_h, n_v = infer_element_grid(
        archetype,
        gain_dbi,
        element_gain_dbi,
        standard_grids=standard_grids,
    )
    width, height = compute_panel_dimensions(
        n_h,
        n_v,
        freq_mhz,
        margin=margin,
        default_freq_mhz=default_freq_mhz,
    )
    return {
        "archetype": archetype,
        "n_h": n_h,
        "n_v": n_v,
        "panel_width_m": round(width, 4),
        "panel_height_m": round(height, 4),
    }
