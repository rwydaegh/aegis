import json

import numpy as np
import pytest


@pytest.fixture
def client(viewer_app):
    # viewer_app is the shared module-scoped Flask app from tests/conftest.py.
    return viewer_app.test_client()


def _studio_data_present() -> bool:
    from aegis.viewer.routes.studio import studio_data_dir

    root = studio_data_dir()
    return (root / "rays" / "bs16_los_seed0.npz").is_file()


def _phantom_present() -> bool:
    from aegis.viewer.routes.studio import studio_data_dir

    return (studio_data_dir() / "phantom" / "thelonious.npz").is_file()


needs_packs = pytest.mark.skipif(not _studio_data_present(), reason="studio data packs not present")
needs_phantom = pytest.mark.skipif(not _phantom_present(), reason="studio phantom pack not present")


def test_manifest_returns_default_tuple(client):
    r = client.get("/api/studio/manifest")
    assert r.status_code == 200
    m = r.get_json()
    assert m["conditions"]  # non-empty
    assert m["frequencies"]  # non-empty
    scene = m["default_scene"]
    assert scene["condition"] == "los"
    assert scene["array_n"] == 16
    assert scene["seed"] == 0
    assert scene["beam"] == "mrt"
    assert scene["frequency_ghz"] == 10
    assert scene["plane"]["orientation"] == "transverse"
    assert scene["fieldQuantity"] == "S"
    assert scene["bodyMapQuantity"] == "mrt"


@needs_packs
def test_rays_returns_directions_and_power(client):
    r = client.get("/api/studio/rays?condition=los&array_n=16&seed=0&top_k=50")
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert len(j["directions"]) == 50
    assert len(j["power"]) == 50
    assert len(j["k_hat"]) == 50
    assert len(j["directions"][0]) == 3
    # power is sorted descending
    p = np.asarray(j["power"])
    assert np.all(p[:-1] >= p[1:])


@needs_packs
def test_rays_missing_pack_404(client):
    r = client.get("/api/studio/rays?condition=nlos&array_n=16&seed=0")
    assert r.status_code == 404


@needs_packs
def test_slice_default_state(client):
    body = {
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "beam": "mrt",
        "focus_xyz": [0.923, -0.005, 0.734],
        "frequency_ghz": 10,
        "plane": {"orientation": "transverse", "extent_m": 0.08, "res": 160},
        "quantity": "S",
    }
    r = client.post("/api/studio/slice", json=body)
    assert r.status_code == 200, r.get_data(as_text=True)
    stats = json.loads(r.headers["X-Stats"])
    assert stats["shape"] == [160, 160]
    assert "world" in stats
    assert {"center", "e1", "e2", "extent"} <= set(stats["world"])
    assert stats["peak_value"] > 0
    # buffer is parseable float32 of the right length
    arr = np.frombuffer(r.data, dtype=np.float32)
    assert arr.shape[0] == 160 * 160
    assert float(arr.max()) == pytest.approx(stats["peak_value"], rel=1e-5)


def _slice_peak(client, beam):
    body = {
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "beam": beam,
        "focus_xyz": [0.923, -0.005, 0.734],
        "frequency_ghz": 10,
        "plane": {"orientation": "transverse", "extent_m": 0.08, "res": 160},
        "quantity": "S",
    }
    r = client.post("/api/studio/slice", json=body)
    assert r.status_code == 200, r.get_data(as_text=True)
    stats = json.loads(r.headers["X-Stats"])
    return stats


@needs_packs
def test_slice_default_peak_matches_focusing(client):
    # Correctness: the matched-power MRT precoder produces the e11 coherent
    # focusing gain. The MRT focal peak must (a) land within ~one wavelength of
    # the focus, (b) tower over the same-power unfocused (random-phase) peak by
    # the e11 focused/unfocused gain (52-168x), and (c) sit at or below the
    # worstcase envelope (the precoder-independent lambda_max).
    mrt = _slice_peak(client, "mrt")
    unfocused = _slice_peak(client, "unfocused")
    worstcase = _slice_peak(client, "worstcase")

    peak = np.asarray(mrt["peak_xyz"])
    center = np.asarray(mrt["world"]["center"])
    wavelength = 3e8 / 10e9
    assert np.linalg.norm(peak - center) < wavelength

    gain = mrt["peak_value"] / unfocused["peak_value"]
    assert gain > 20.0  # comfortably inside the 52-168x e11 regime

    # worstcase is the envelope: MRT cannot exceed it (allow a sliver of slack).
    assert mrt["peak_value"] <= worstcase["peak_value"] * 1.02


@pytest.mark.parametrize("body", [{"array_n": "abc"}, {"plane": 5}])
def test_slice_malformed_body_400(client, body):
    # Malformed client fields must be coerced inside the try block so they map
    # to a clean 400, not a 500. int("abc") raises ValueError, dict(5) raises
    # TypeError; both are caught. No packs needed (the cast fails first).
    r = client.post("/api/studio/slice", json=body)
    assert r.status_code == 400, r.get_data(as_text=True)
    assert "error" in r.get_json()


@needs_packs
def test_slice_res_is_clamped(client):
    # An unbounded res allocates (res, res, 3) and OOMs the server. The endpoint
    # must clamp res to <= 512 and still succeed (no 500/OOM).
    body = {
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "beam": "mrt",
        "focus_xyz": [0.923, -0.005, 0.734],
        "frequency_ghz": 10,
        "plane": {"orientation": "transverse", "extent_m": 0.08, "res": 99999},
        "quantity": "S",
    }
    r = client.post("/api/studio/slice", json=body)
    assert r.status_code == 200, r.get_data(as_text=True)
    stats = json.loads(r.headers["X-Stats"])
    assert stats["shape"] == [512, 512]
    arr = np.frombuffer(r.data, dtype=np.float32)
    assert arr.shape[0] == 512 * 512
    # X-Stats agrees exactly with the shipped float32 payload.
    assert float(arr.max()) == pytest.approx(stats["peak_value"], rel=0, abs=0)


@needs_phantom
def test_phantom_returns_geometry_buffer(client):
    r = client.get("/api/studio/phantom?mesh=thelonious")
    assert r.status_code == 200, r.get_data(as_text=True)
    stats = json.loads(r.headers["X-Stats"])
    assert stats["mesh"] == "thelonious"
    manifest = {a["name"]: a for a in stats["arrays"]}
    # The contract the frontend slices against.
    assert manifest["vertices"]["shape"] == [24000, 3]
    assert manifest["vertices"]["dtype"] == "float32"
    assert manifest["faces"]["shape"] == [8000, 3]
    assert manifest["faces"]["dtype"] == "int32"
    assert {"centroids", "normals"} <= set(manifest)
    # Each array slices out of the binary body at its declared offset/shape.
    data = r.data
    verts = manifest["vertices"]
    v = np.frombuffer(data, dtype=np.float32, count=verts["length"], offset=verts["offset"])
    assert v.reshape(verts["shape"]).shape == (24000, 3)
    faces = manifest["faces"]
    f = np.frombuffer(data, dtype=np.int32, count=faces["length"], offset=faces["offset"])
    assert f.reshape(faces["shape"]).shape == (8000, 3)
    assert int(f.max()) < 24000  # face indices stay inside the vertex soup


def test_phantom_unknown_mesh_404(client):
    # No packs needed: the unknown mesh is rejected before any disk access.
    r = client.get("/api/studio/phantom?mesh=nope")
    assert r.status_code == 404
    assert "error" in r.get_json()


@needs_packs
def test_bodymap_worstcase(client):
    r = client.get("/api/studio/bodymap?condition=los&array_n=16&beam=worstcase&quantity=worstcase&frequency_ghz=28")
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert len(j["values"]) == 8000
    assert j["vmax"] >= j["vmin"]
    assert "provenance" in j


@needs_packs
def test_bodymap_worstcase_is_beam_independent(client):
    # worstcase is a precoder-independent envelope: the served pack must be the
    # same regardless of the beam query param.
    base = "/api/studio/bodymap?condition=los&array_n=16&quantity=worstcase&frequency_ghz=28"
    r_a = client.get(base + "&beam=mrt")
    r_b = client.get(base + "&beam=ecbf")
    assert r_a.status_code == 200
    assert r_b.status_code == 200
    va = np.asarray(r_a.get_json()["values"])
    vb = np.asarray(r_b.get_json()["values"])
    assert np.array_equal(va, vb)


@needs_packs
def test_bodymap_missing_pack_409(client):
    r = client.get("/api/studio/bodymap?condition=nlos&array_n=16&beam=mrt&quantity=mrt&frequency_ghz=99")
    assert r.status_code == 409
    j = r.get_json()
    assert j["not_precomputed"] is True
    assert "error" in j
