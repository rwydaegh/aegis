"""Tests for MIMO config defaults."""

from aegis.viewer.config import DEFAULTS


def test_mimo_defaults_present():
    """DEFAULTS has a 'mimo' key with required subkeys."""
    mimo = DEFAULTS["mimo"]
    assert isinstance(mimo["enabled"], bool)
    assert mimo["enabled"] is False
    assert isinstance(mimo["array"], dict)
    assert mimo["array"]["type"] == "upa"
    assert mimo["array"]["n_h"] == 4
    assert mimo["array"]["n_v"] == 4
    assert isinstance(mimo["users"], list)
    assert mimo["precoder"] == "mrt"
    assert isinstance(mimo["max_users"], int)


def test_mimo_array_defaults():
    """Array config has element spacing in wavelength fractions and geometry."""
    arr = DEFAULTS["mimo"]["array"]
    assert arr["d_h_wavelengths"] == 0.5
    assert arr["d_v_wavelengths"] == 0.5
    assert len(arr["position"]) == 3
    assert len(arr["broadside"]) == 3


def test_mimo_default_user():
    """Default user list has one entry with required fields."""
    users = DEFAULTS["mimo"]["users"]
    assert len(users) == 1
    user = users[0]
    assert "id" in user
    assert "phantom" in user
    assert "position" in user
    assert "device_offset" in user
