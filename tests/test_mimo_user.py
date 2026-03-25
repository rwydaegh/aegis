"""Tests for UserConfig and UserState data model."""

import numpy as np
import pytest


def test_user_config_frozen():
    """UserConfig is immutable."""
    from aegis.mimo.user import UserConfig

    cfg = UserConfig(
        user_id="u1",
        phantom_name="thelonious",
        position=np.zeros(3),
        orientation=0.0,
        device_position=np.array([0.25, 0.0, 1.4]),
        device_orientation=np.array([0.0, 0.0, 1.0]),
    )
    with pytest.raises(AttributeError):
        cfg.phantom_name = "duke"


def test_user_config_validation():
    """UserConfig rejects bad shapes."""
    from aegis.mimo.user import UserConfig

    with pytest.raises(ValueError, match="position"):
        UserConfig(
            user_id="u1",
            phantom_name="thelonious",
            position=np.zeros(2),
            orientation=0.0,
            device_position=np.zeros(3),
            device_orientation=np.array([0.0, 0.0, 1.0]),
        )


def test_user_state_initial():
    """UserState starts with all computed fields as None."""
    from aegis.mimo.user import UserConfig, UserState

    cfg = UserConfig(
        user_id="u1",
        phantom_name="thelonious",
        position=np.zeros(3),
        orientation=0.0,
        device_position=np.array([0.25, 0.0, 1.4]),
        device_orientation=np.array([0.0, 0.0, 1.0]),
    )
    state = UserState(config=cfg)
    assert state.body is None
    assert state.paths is None
    assert state.h is None
    assert state.G_tilde is None
    assert state.Q is None
    assert state.result is None


def test_user_state_mutable():
    """UserState computed fields can be set."""
    from aegis.mimo.user import UserConfig, UserState

    cfg = UserConfig(
        user_id="u1",
        phantom_name="thelonious",
        position=np.zeros(3),
        orientation=0.0,
        device_position=np.array([0.25, 0.0, 1.4]),
        device_orientation=np.array([0.0, 0.0, 1.0]),
    )
    state = UserState(config=cfg)
    state.h = np.ones(4, dtype=complex)
    assert state.h is not None


def test_device_orientation_normalized():
    """UserConfig normalizes device_orientation to unit vector."""
    from aegis.mimo.user import UserConfig

    cfg = UserConfig(
        user_id="u1",
        phantom_name="thelonious",
        position=np.zeros(3),
        orientation=0.0,
        device_position=np.zeros(3),
        device_orientation=np.array([0.0, 0.0, 2.0]),
    )
    np.testing.assert_allclose(
        np.linalg.norm(cfg.device_orientation),
        1.0,
        atol=1e-14,
    )
