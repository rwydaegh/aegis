"""Integration test: verify device offsets are reasonable for real phantom meshes."""

import pytest

from aegis.geometry.device_offset import estimate_device_offset
from aegis.geometry.mesh import load_stl_binary

# Heights from PHANTOM_META (IT'IS Virtual Population)
EXPECTED = {
    "duke": {"height_m": 1.77, "eye_z_min": 1.60, "eye_z_max": 1.75},
    "ella": {"height_m": 1.63, "eye_z_min": 1.45, "eye_z_max": 1.60},
    "thelonious": {"height_m": 1.15, "eye_z_min": 1.00, "eye_z_max": 1.15},
    "eartha": {"height_m": 1.36, "eye_z_min": 1.20, "eye_z_max": 1.35},
}


def _try_load(name, data_dir):
    path = data_dir / f"{name}.stl"
    if not path.exists():
        pytest.skip(f"STL data not available: {name}")
    verts, _, _ = load_stl_binary(path)
    return verts


@pytest.mark.slow
@pytest.mark.parametrize("name", ["duke", "ella", "thelonious", "eartha"])
def test_device_offset_height_range(name, data_dir):
    """Device Z (from ground) should be near known eye height for each phantom."""
    verts = _try_load(name, data_dir)
    offset = estimate_device_offset(verts, forward_distance=0.30)
    z_min = float(verts.reshape(-1, 3)[:, 2].min())
    eye_z_from_ground = offset[2] - z_min
    exp = EXPECTED[name]
    assert exp["eye_z_min"] < eye_z_from_ground < exp["eye_z_max"], (
        f"{name}: eye_z_from_ground={eye_z_from_ground:.3f}, expected [{exp['eye_z_min']}, {exp['eye_z_max']}]"
    )


@pytest.mark.slow
@pytest.mark.parametrize("name", ["duke", "ella", "thelonious", "eartha"])
def test_device_forward_positive(name, data_dir):
    """Device should be in front of the body (positive Y in Z-up)."""
    verts = _try_load(name, data_dir)
    offset = estimate_device_offset(verts, forward_distance=0.30)
    assert offset[1] > 0.20, f"{name}: device_y={offset[1]:.3f}, expected > 0.20"


@pytest.mark.slow
@pytest.mark.parametrize("name", ["duke", "ella", "thelonious", "eartha"])
def test_device_x_centered(name, data_dir):
    """Device X should be near center (within 10cm of body center)."""
    verts = _try_load(name, data_dir)
    offset = estimate_device_offset(verts, forward_distance=0.30)
    assert abs(offset[0]) < 0.10, f"{name}: device_x={offset[0]:.3f}, expected |x| < 0.10"
