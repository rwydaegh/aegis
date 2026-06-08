import json
from pathlib import Path

import pytest


@pytest.fixture
def client(viewer_app):
    # viewer_app is the shared module-scoped Flask app from tests/conftest.py
    # (Flask-gated, uses the e2e_icosahedron body). Do not build a new app.
    return viewer_app.test_client()


def test_lab_blueprint_registered(client):
    r = client.get("/api/lab/nf-patterns")
    assert r.status_code == 200
    pats = r.get_json()["patterns"]
    ids = [p["id"] for p in pats]
    assert {"isotropic", "dipole", "patch"} <= set(ids)
    assert all(p["synthetic"] for p in pats)  # no GOLIAT env -> synthetic only


def test_nf_patterns_env_set_but_empty(client, tmp_path, monkeypatch):
    monkeypatch.setenv("AEGIS_NEARFIELD_PATTERNS", str(tmp_path))
    r = client.get("/api/lab/nf-patterns")
    ids = {p["id"] for p in r.get_json()["patterns"]}
    assert ids == {"isotropic", "dipole", "patch"}  # empty dir -> still synthetic only


def test_pattern_lobe_returns_grid(client):
    r = client.get("/api/lab/pattern_lobe?id=dipole&n_theta=24&n_phi=48")
    assert r.status_code == 200
    j = r.get_json()
    assert len(j["theta"]) == 24
    assert len(j["phi"]) == 48
    assert len(j["r"]) == 48  # n_phi rows
    assert len(j["r"][0]) == 24  # n_theta cols
    import numpy as np

    assert np.all(np.asarray(j["r"]) >= 0)


def test_pattern_lobe_unknown_id_400(client):
    r = client.get("/api/lab/pattern_lobe?id=nonsense")
    assert r.status_code == 400


def _smplx_available():
    return (Path.home() / ".aegis" / "models" / "smplx" / "SMPLX_NEUTRAL.npz").exists()


smplx_only = pytest.mark.skipif(not _smplx_available(), reason="SMPL-X model not present")


@smplx_only
def test_parametric_body_emits_vertex_hash_and_presets(client):
    r = client.post("/api/parametric-body", json={"preset": "arm_raised_front"})
    assert r.status_code == 200
    meta = json.loads(r.headers["X-Meta"])
    assert "vertex_hash" in meta
    r2 = client.post("/api/parametric-body", json={"preset": "arm_raised_front"})
    assert json.loads(r2.headers["X-Meta"])["vertex_hash"] == meta["vertex_hash"]
    r3 = client.post("/api/parametric-body", json={"preset": "t_pose"})
    assert json.loads(r3.headers["X-Meta"])["vertex_hash"] != meta["vertex_hash"]


@smplx_only
def test_parametric_body_unknown_preset_400(client):
    r = client.post("/api/parametric-body", json={"preset": "nonsense"})
    assert r.status_code == 400


@smplx_only
def test_rig_shapes(client):
    r = client.get("/api/lab/rig?gender=neutral")
    assert r.status_code == 200
    j = r.get_json()
    V = j["n_vertices"]
    J = j["n_joints"]
    assert V == 10475
    assert J == 55
    assert len(j["template"]) == V * 3
    assert len(j["faces"]) % 3 == 0
    assert len(j["lbs_weights"]) == V * J
    assert len(j["rest_joints"]) == J * 3
    assert len(j["parents"]) == J
    assert j["parents"][0] == -1  # pelvis is the kinematic root


@smplx_only
def test_rig_bad_gender_400(client):
    r = client.get("/api/lab/rig?gender=alien")
    assert r.status_code == 400


@smplx_only
def test_lab_compute_near(client):
    near = {
        "gender": "neutral",
        "preset": "arm_raised_front",
        "freq_mhz": 3500,
        "power_w": 1.0,
        "physics": {"diffraction_model": "fock", "self_shadow": True, "fresnel": True},
        "source": {
            "kind": "near",
            "pattern_id": "dipole",
            "position": [0.2, 0.0, 0.3],
            "yaw": 0.0,
            "pitch": 0.0,
            "roll": 0.0,
        },
    }
    r = client.post("/api/lab/compute", json=near)
    assert r.status_code == 200, r.get_data(as_text=True)
    meta = json.loads(r.headers["X-Stats"])
    assert "p_abs" in meta
    assert meta["p_abs"] >= 0
    assert any(a["key"] == "sab" for a in meta["arrays"])
    assert len(r.data) >= 4  # at least the sab float32 buffer


@smplx_only
def test_lab_compute_far(client):
    far = {
        "gender": "neutral",
        "preset": "t_pose",
        "freq_mhz": 3500,
        "power_w": 1.0,
        "physics": {"diffraction_model": "fock", "self_shadow": False, "fresnel": True},
        "source": {"kind": "far", "theta_inc": 1.2, "phi_inc": 0.5, "pol_angle": 0.0},
    }
    r = client.post("/api/lab/compute", json=far)
    assert r.status_code == 200, r.get_data(as_text=True)
    meta = json.loads(r.headers["X-Stats"])
    assert "p_abs" in meta
    assert len(r.data) >= 4
