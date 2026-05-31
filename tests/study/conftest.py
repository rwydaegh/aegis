from pathlib import Path

import pytest

from aegis.geometry.mesh import BodyMesh

_DATA_DIR = Path(__file__).parents[2] / "data"


@pytest.fixture
def duke_mesh():
    stl = _DATA_DIR / "duke.stl"
    if not stl.exists():
        pytest.skip("duke.stl phantom not available")
    return BodyMesh.load(stl, name="duke")
