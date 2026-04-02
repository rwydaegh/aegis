"""Tests for placement grid search optimizer."""

import numpy as np


class TestPlacementSetup:
    def test_setup_returns_grid_points(self):
        from aegis.optim.placement import setup

        state = setup(
            center=np.array([5.0, 0.0, 3.0]),
            grid_size=3,
            grid_spacing=2.0,
            constraint_axis="y",
            constraint_value=0.0,
        )
        assert state["grid_points"].shape == (9, 3)
        assert all(state["grid_points"][:, 1] == 0.0)

    def test_setup_5x5_grid(self):
        from aegis.optim.placement import setup

        state = setup(
            center=np.array([0.0, 0.0, 3.0]),
            grid_size=5,
            grid_spacing=1.0,
        )
        assert state["grid_points"].shape == (25, 3)


class TestPlacementStep:
    def test_step_evaluates_next_point(self):
        from aegis.optim.placement import setup, step

        state = setup(
            center=np.array([5.0, 0.0, 3.0]),
            grid_size=3,
            grid_spacing=2.0,
        )
        state["evaluate_fn"] = lambda pos: {
            "peak_sab": float(np.linalg.norm(pos)),
            "sab": np.ones(10, dtype=np.float32),
            "stats": {"peak_sab": float(np.linalg.norm(pos))},
        }

        state, result = step(state)
        assert result["iter"] == 1
        assert "antenna_pos" in result["params"]
        assert "sab" in result

    def test_grid_search_finds_minimum(self):
        from aegis.optim.placement import setup, step

        state = setup(
            center=np.array([0.0, 0.0, 3.0]),
            grid_size=3,
            grid_spacing=2.0,
        )
        # Peak exposure decreases with distance from origin
        state["evaluate_fn"] = lambda pos: {
            "peak_sab": 1.0 / (np.linalg.norm(pos) + 0.1),
            "sab": np.ones(10, dtype=np.float32) / (np.linalg.norm(pos) + 0.1),
            "stats": {"peak_sab": 1.0 / (np.linalg.norm(pos) + 0.1)},
        }

        for _ in range(9):
            state, result = step(state)

        assert result["done"]
        assert "best" in result
        # Best should be the farthest from origin (lowest 1/distance)
        best_pos = np.array(result["best"]["antenna_pos"])
        assert np.linalg.norm(best_pos) > 2.0  # must be a corner point

    def test_done_after_all_points(self):
        from aegis.optim.placement import setup, step

        state = setup(
            center=np.array([0.0, 0.0, 0.0]),
            grid_size=3,
            grid_spacing=1.0,
        )
        state["evaluate_fn"] = lambda pos: {
            "peak_sab": 1.0,
            "sab": np.ones(5, dtype=np.float32),
            "stats": {"peak_sab": 1.0},
        }

        done_count = 0
        for _ in range(20):
            state, result = step(state)
            if result.get("done"):
                done_count += 1
                break

        assert done_count == 1
        assert result["iter"] == 9  # 3x3 grid
