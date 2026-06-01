"""The scene map renders from a run's scene.json, and the disk sampler stays in
bounds."""

import json

import numpy as np

from aegis.study.run import _sample_xy_in_disk
from aegis.study.viz import plot_scene


def test_sample_xy_in_disk_within_radius():
    rng = np.random.default_rng(0)
    R = 50.0
    pts = np.array([_sample_xy_in_disk(rng, R) for _ in range(500)])
    assert np.all(np.linalg.norm(pts, axis=1) <= R + 1e-9)


def test_plot_scene_writes_png(tmp_path):
    scene = {
        "sites": [
            {
                "position": [0.0, 0.0, 15.0],
                "sectors": [
                    {"boresight_az_deg": 0.0, "az_coverage_deg": 120.0, "max_range_m": 150.0, "m_ant": 64},
                    {"boresight_az_deg": 120.0, "az_coverage_deg": 120.0, "max_range_m": 150.0, "m_ant": 64},
                ],
            }
        ],
        "agents": [
            {
                "agent_id": 0,
                "is_user": True,
                "exposure_w": 1.2e-6,
                "positions": [[-50.0, -20.0], [-10.0, 5.0], [30.0, 25.0]],
            },
            {
                "agent_id": 1,
                "is_user": False,
                "exposure_w": 3.4e-9,
                "positions": [[40.0, -40.0], [10.0, -10.0]],
            },
        ],
    }
    (tmp_path / "scene.json").write_text(json.dumps(scene))
    out = plot_scene(tmp_path, tmp_path / "scene_map.png")
    assert out.exists()
    assert out.stat().st_size > 0
