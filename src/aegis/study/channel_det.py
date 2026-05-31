"""Deterministic channel arm: per-sector ray-traced per-element paths.

A thin wrapper over ``paths_from_differt_scene_obj``. Each sector's UPA element
positions are the transmitters; the rx point is the body. The returned
``PropagationPaths`` already carries per-element complex ``psi`` and
``element_index`` (full TE/TM phase tracking), so it feeds the coherent
body-surface channel directly. Do not call ``expand_paths_to_array`` on it:
the per-element phase is already applied.

Uses the in-memory ``TriangleScene`` from ``EnvironmentMesh.to_differt_scene()``
rather than the Sionna XML export. The XML export targets Sionna's Mitsuba
loader and is not accepted by differt_core's stricter parser, and reusing one
scene object avoids re-parsing per call.
"""

from __future__ import annotations

import numpy as np

from aegis.integration.differt import paths_from_differt_scene_obj


def sector_paths_det(
    scene,
    sector,
    rx_position,
    freq_hz,
    max_bounces=3,
    tx_power_dbm=30.0,
):
    """Per-element ray-traced paths (one tx per array element)."""
    return paths_from_differt_scene_obj(
        scene,
        tx_positions=np.asarray(sector.array.element_positions),
        rx_position=np.asarray(rx_position, dtype=float),
        freq_hz=freq_hz,
        max_bounces=max_bounces,
        tx_power_dbm=tx_power_dbm,
        initial_polarisation="vertical",
    )


def center_paths_det(
    scene,
    sector,
    rx_position,
    freq_hz,
    max_bounces=3,
    tx_power_dbm=30.0,
):
    """Center-of-array paths: trace from the array phase center as a single tx.

    These feed the translation-phasor Gram and (after expand_paths_to_array) the
    coherent Sab map. Tracing once from the center instead of M_ant times is the
    far-field array model and is much cheaper.
    """
    return paths_from_differt_scene_obj(
        scene,
        tx_positions=np.asarray(sector.array.reference_position)[None, :],
        rx_position=np.asarray(rx_position, dtype=float),
        freq_hz=freq_hz,
        max_bounces=max_bounces,
        tx_power_dbm=tx_power_dbm,
        initial_polarisation="vertical",
    )
