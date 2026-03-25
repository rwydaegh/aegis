"""Tests for MIMOScene data container."""

import numpy as np
import pytest

from aegis.tissue.dielectric import SKIN_28GHZ


def _make_scene(n_users=2):
    """Helper: create a MIMOScene with n_users."""
    from aegis.mimo.array import AntennaArray
    from aegis.mimo.scene import MIMOScene
    from aegis.mimo.user import UserConfig, UserState

    arr = AntennaArray.upa(
        n_h=4,
        n_v=4,
        d_h=0.005,
        d_v=0.005,
        center=np.array([5.0, 0.0, 3.0]),
        broadside=np.array([-1.0, 0.0, 0.0]),
    )
    users = []
    for i in range(n_users):
        cfg = UserConfig(
            user_id=f"user_{i}",
            phantom_name="thelonious",
            position=np.array([0.0, float(i), 0.0]),
            orientation=0.0,
            device_position=np.array([0.25, float(i), 1.4]),
            device_orientation=np.array([0.0, 0.0, 1.0]),
        )
        users.append(UserState(config=cfg))

    return MIMOScene(
        array=arr,
        users=users,
        freq_hz=28e9,
        total_power=1.0,
        tissue=SKIN_28GHZ,
    )


def test_scene_n_users():
    """Scene reports correct number of users."""
    scene = _make_scene(3)
    assert scene.n_users == 3


def test_scene_get_user():
    """Can retrieve user by ID."""
    scene = _make_scene(2)
    user = scene.get_user("user_0")
    assert user.config.user_id == "user_0"


def test_scene_get_user_missing():
    """KeyError for nonexistent user ID."""
    scene = _make_scene(2)
    with pytest.raises(KeyError):
        scene.get_user("nonexistent")


def test_scene_user_ids():
    """user_ids returns all IDs in order."""
    scene = _make_scene(3)
    assert scene.user_ids == ["user_0", "user_1", "user_2"]


def test_scene_all_Q_populated():
    """all_Q returns Q matrices when all users have them."""
    scene = _make_scene(2)
    Q_fake = np.eye(16, dtype=complex)
    scene.users[0].Q = Q_fake
    scene.users[1].Q = Q_fake * 2
    qs = scene.all_Q()
    assert len(qs) == 2
    np.testing.assert_allclose(qs[0], Q_fake)


def test_scene_all_Q_incomplete():
    """all_Q raises if any user lacks Q."""
    scene = _make_scene(2)
    scene.users[0].Q = np.eye(16, dtype=complex)
    with pytest.raises(ValueError, match="user_1"):
        scene.all_Q()


def test_scene_all_h():
    """all_h returns stacked channel matrix H."""
    scene = _make_scene(2)
    M = scene.array.n_elements
    scene.users[0].h = np.ones(M, dtype=complex)
    scene.users[1].h = np.ones(M, dtype=complex) * 2
    H = scene.all_h()
    assert H.shape == (2, M)
    np.testing.assert_allclose(H[1], 2.0)


def test_scene_all_h_incomplete():
    """all_h raises if any user lacks a channel vector."""
    scene = _make_scene(2)
    scene.users[0].h = np.ones(16, dtype=complex)
    with pytest.raises(ValueError, match="user_1"):
        scene.all_h()


def test_scene_zero_users():
    """Scene with zero users is valid."""
    from aegis.mimo.array import AntennaArray
    from aegis.mimo.scene import MIMOScene

    arr = AntennaArray.upa(
        n_h=4,
        n_v=4,
        d_h=0.005,
        d_v=0.005,
        center=np.zeros(3),
        broadside=np.array([1.0, 0, 0]),
    )
    scene = MIMOScene(
        array=arr,
        users=[],
        freq_hz=28e9,
        total_power=1.0,
        tissue=SKIN_28GHZ,
    )
    assert scene.n_users == 0
    assert scene.user_ids == []
