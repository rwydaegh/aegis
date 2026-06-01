"""Deterministic channel arm: per-sector ray-traced per-element paths.

Two tracer backends, selected per call:

- ``"sionna"`` (default): Sionna RT via Dr.Jit. Runs on CPU and auto-uses a GPU
  when present, scales to city scenes (SBR), and consumes the radio-material
  Mitsuba scene from ``CityCache.sionna_scene``.
- ``"differt"``: the JAX image-method tracer. Exact specular paths, useful as an
  independent second tracer for the ground-truth comparison, but O(N^K) in scene
  size. Consumes the in-memory ``CityCache.differt_scene``.

Both return a coherent ``PropagationPaths`` with per-element ``psi`` and
``element_index`` (full polarization), ready for the coherent body channel. Do
not call ``expand_paths_to_array`` on the per-element result: the per-element
phase is already applied. ``center_paths`` traces from the array phase center as
a single tx (the far-field array model) for the translation-phasor Gram.
"""

from __future__ import annotations

import numpy as np

# Shoot-and-bounce rays per source for Sionna RT. A convergence sweep on the
# Ghent core at 28 GHz (rooftop -> ground receiver, max_depth 3, 1-100M samples,
# 5 seeds) showed the bridge default of 1M finds only ~9 of the 19 valid paths
# with ~19% power error and large seed-to-seed variance. The path set is fully
# resolved (19 paths every seed, power flat to <0.01% vs 100M) at 30M, which
# costs ~3 s here, negligible beside the ~60 s coherent dosimetry. mmWave needs
# this many because a small receiver subtends a tiny solid angle. Geometry
# dependent: deep-NLOS receivers may warrant a re-check.
SAMPLES_PER_SRC = 30_000_000

# Diffraction on by default for the deterministic arm. A rooftop antenna looking
# down at a near-ground receiver is partly shadowed by its own roof edge, so edge
# diffraction carries real energy: on the Ghent core at 28 GHz, enabling it raised
# the received power ~2.2x over specular-only (and the diffracted power converges
# by max_depth 3). Sionna's diffraction is an approximate UTD-style model and the
# discovered-path set is mildly sample-noisy, so treat the magnitude as indicative
# and sanity-check it in the deterministic-vs-stochastic comparison.
DIFFRACTION = True


def _trace(
    scene,
    tx_positions,
    rx_position,
    freq_hz,
    engine,
    max_bounces,
    tx_power_dbm,
    samples_per_src=SAMPLES_PER_SRC,
    diffraction=DIFFRACTION,
):
    tx_positions = np.asarray(tx_positions, dtype=float)
    rx_position = np.asarray(rx_position, dtype=float)
    if engine == "sionna":
        from aegis.integration.sionna import paths_from_sionna_scene

        return paths_from_sionna_scene(
            scene,
            tx_positions=tx_positions,
            rx_position=rx_position,
            freq_hz=freq_hz,
            max_bounces=max_bounces,
            tx_power_dbm=tx_power_dbm,
            samples_per_src=samples_per_src,
            diffraction=diffraction,
            edge_diffraction=diffraction,
        )
    if engine == "differt":
        from aegis.integration.differt import paths_from_differt_scene_obj

        return paths_from_differt_scene_obj(
            scene,
            tx_positions=tx_positions,
            rx_position=rx_position,
            freq_hz=freq_hz,
            max_bounces=max_bounces,
            tx_power_dbm=tx_power_dbm,
            initial_polarisation="vertical",
        )
    raise ValueError(f"unknown ray-tracing engine: {engine!r} (use 'sionna' or 'differt')")


def sector_paths(
    scene,
    sector,
    rx_position,
    freq_hz,
    *,
    engine="sionna",
    max_bounces=3,
    tx_power_dbm=30.0,
    samples_per_src=SAMPLES_PER_SRC,
    diffraction=DIFFRACTION,
):
    """Per-element ray-traced paths (one tx per array element)."""
    return _trace(
        scene,
        sector.array.element_positions,
        rx_position,
        freq_hz,
        engine,
        max_bounces,
        tx_power_dbm,
        samples_per_src,
        diffraction,
    )


def center_paths(
    scene,
    sector,
    rx_position,
    freq_hz,
    *,
    engine="sionna",
    max_bounces=3,
    tx_power_dbm=30.0,
    samples_per_src=SAMPLES_PER_SRC,
    diffraction=DIFFRACTION,
):
    """Center-of-array paths: trace from the array phase center as a single tx.

    These feed the translation-phasor Gram and (after expand_paths_to_array) the
    coherent Sab map. Tracing once from the center instead of M_ant times is the
    far-field array model and is much cheaper.
    """
    return _trace(
        scene,
        np.asarray(sector.array.reference_position)[None, :],
        rx_position,
        freq_hz,
        engine,
        max_bounces,
        tx_power_dbm,
        samples_per_src,
        diffraction,
    )
