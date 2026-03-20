"""Tests for simplified voxel loading pipeline."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "viewer_env_test"


def test_parse_reads_unit_from_metadata():
    """Voxel size should come from JSON metadata, not be recomputed."""
    from aegis.viewer.scene_data import _parse_voxel_json

    path = FIXTURES / "voxels_with_metadata.json"
    result = _parse_voxel_json(path)
    # New return value includes tile_unit
    assert len(result) == 5  # grid_coords, positions, colors, materials, tile_unit
    _, _, _, _, tile_unit = result
    assert tile_unit == pytest.approx(0.5)


def test_positions_are_passthrough_yup():
    """World positions from JSON must not be transformed. They stay Y-up."""
    from aegis.viewer.scene_data import load_voxels

    path = FIXTURES / "voxels_with_metadata.json"
    positions, colors, materials, voxel_sizes = load_voxels(path, bbox_radius=100, exterior_only=False)
    # wx=9.75 should appear unchanged in output
    assert positions[0, 0] == pytest.approx(9.75)
    # wy=0.0 stays at index 1 (Y-up, no axis swap)
    assert positions[0, 1] == pytest.approx(0.0)
    # wz=4.75 stays at index 2
    assert positions[0, 2] == pytest.approx(4.75)


def test_returns_per_voxel_sizes():
    """load_voxels returns a per-voxel size array, not a single float."""
    from aegis.viewer.scene_data import load_voxels

    path = FIXTURES / "voxels_with_metadata.json"
    positions, colors, materials, voxel_sizes = load_voxels(path, bbox_radius=100, exterior_only=False)
    assert isinstance(voxel_sizes, np.ndarray)
    assert voxel_sizes.dtype == np.float32
    assert len(voxel_sizes) == len(positions)
    assert all(v == pytest.approx(0.5) for v in voxel_sizes)


def test_old_format_without_metadata_still_loads():
    """Bare array voxel JSON (no unit/bbox) should still work with fallback."""
    from aegis.viewer.scene_data import load_voxels

    path = FIXTURES / "voxels.json"
    positions, colors, materials, voxel_sizes = load_voxels(path, bbox_radius=100, exterior_only=False)
    assert len(positions) == 4
    # Fallback: voxel size computed from adjacent grid cells
    assert all(voxel_sizes > 0)
