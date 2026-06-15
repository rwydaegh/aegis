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


def _qpack_present() -> bool:
    from aegis.viewer.routes.studio import studio_data_dir

    return (studio_data_dir() / "qop" / "thelonious_los_bs16_10.npz").is_file()


def _ensemble_present() -> bool:
    from aegis.viewer.routes.studio import studio_data_dir

    return any((studio_data_dir() / "ensemble").glob("thelonious_los_bs16_mrt_28_mean*.npz"))


def _channel_present() -> bool:
    from aegis.viewer.routes.studio import studio_data_dir

    return (studio_data_dir() / "channel" / "thelonious_los_bs16_10_seed0.npz").is_file()


needs_packs = pytest.mark.skipif(not _studio_data_present(), reason="studio data packs not present")
needs_phantom = pytest.mark.skipif(not _phantom_present(), reason="studio phantom pack not present")
needs_qpack = pytest.mark.skipif(not _qpack_present(), reason="studio Q-operator pack not present")
needs_ensemble = pytest.mark.skipif(not _ensemble_present(), reason="studio ensemble packs not present")
needs_channel = pytest.mark.skipif(not _channel_present(), reason="studio field-channel pack not present")


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
    # The studio opens on the live, focus-tracking deposited map so the body
    # recolours as the beam steers. A static default (mrt / floor / ...) is
    # frozen at one focus and reads as "the body map ignores the focus".
    assert scene["bodyMapQuantity"] == "deposited"


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
    # seed 99 has no ray pack on disk for any condition, so this is a genuine miss.
    r = client.get("/api/studio/rays?condition=los&array_n=16&seed=99")
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


def test_slice_unknown_ue_antenna_400(client):
    # The UE receive antenna is validated against the manifest allowlist before
    # any pack is touched, so a bogus kind is a clean 400 (no packs needed).
    r = client.post("/api/studio/slice", json={"ue_antenna": "nope", "frequency_ghz": 10})
    assert r.status_code == 400
    assert "ue_antenna" in r.get_data(as_text=True)


@needs_packs
def test_slice_ue_antenna_shapes_precoder(client):
    # The receive antenna enters the signal channel h via C_R(k)^H psi, so it
    # reshapes the MRT precoder and the field it produces. A directive patch must
    # give a different focal peak than the isotropic reference (the matched filter
    # reweights paths by the receive gain), and both must be valid positive peaks.
    def peak(ue):
        body = {
            "condition": "los",
            "array_n": 16,
            "seed": 0,
            "beam": "mrt",
            "focus_xyz": [0.923, -0.005, 0.734],
            "frequency_ghz": 10,
            "plane": {"orientation": "transverse", "extent_m": 0.08, "res": 120},
            "quantity": "S",
            "ue_antenna": ue,
        }
        r = client.post("/api/studio/slice", json=body)
        assert r.status_code == 200, r.get_data(as_text=True)
        return json.loads(r.headers["X-Stats"])["peak_value"]

    iso = peak("isotropic")
    patch = peak("patch")
    assert iso > 0 and patch > 0
    assert abs(patch - iso) / iso > 1e-3


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
    # The contract the frontend slices against: full-resolution mesh (no
    # decimation), N vertices x 3 and M faces x 3, centroids/normals per face.
    n_vertices, vcols = manifest["vertices"]["shape"]
    n_faces, fcols = manifest["faces"]["shape"]
    assert vcols == 3
    assert fcols == 3
    assert n_vertices > 0
    assert n_faces > 0
    assert manifest["vertices"]["dtype"] == "float32"
    assert manifest["faces"]["dtype"] == "int32"
    assert {"centroids", "normals"} <= set(manifest)
    assert manifest["centroids"]["shape"] == [n_faces, 3]
    assert manifest["normals"]["shape"] == [n_faces, 3]
    assert stats["n_vertices"] == n_vertices
    assert stats["n_faces"] == n_faces
    # Each array slices out of the binary body at its declared offset/shape.
    data = r.data
    verts = manifest["vertices"]
    v = np.frombuffer(data, dtype=np.float32, count=verts["length"], offset=verts["offset"])
    assert v.reshape(verts["shape"]).shape == (n_vertices, 3)
    faces = manifest["faces"]
    f = np.frombuffer(data, dtype=np.int32, count=faces["length"], offset=faces["offset"])
    assert f.reshape(faces["shape"]).shape == (n_faces, 3)
    assert int(f.max()) < n_vertices  # face indices stay inside the vertex soup


def test_phantom_unknown_mesh_404(client):
    # No packs needed: the unknown mesh is rejected before any disk access.
    r = client.get("/api/studio/phantom?mesh=nope")
    assert r.status_code == 404
    assert "error" in r.get_json()


def _slice_post(client, beam, quantity="S", frequency_ghz=10, res=160):
    body = {
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "beam": beam,
        "focus_xyz": [0.923, -0.005, 0.734],
        "frequency_ghz": frequency_ghz,
        "plane": {"orientation": "transverse", "extent_m": 0.08, "res": res},
        "quantity": quantity,
    }
    return client.post("/api/studio/slice", json=body)


@needs_phantom
def test_slice_focus_mode_at_skin_snaps_to_body(client):
    # focus_mode="at-skin" snaps the steering focus onto the nearest body-surface
    # centroid. A focus set off the body (well inside free space) must produce a
    # different field than the same focus in free-space mode, since the precoder
    # now steers at the snapped skin point.
    off_body = [0.923, -0.4, 0.734]  # 40 cm in front of the chest
    common = {
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "beam": "mrt",
        "focus_xyz": off_body,
        "frequency_ghz": 10,
        "plane": {"orientation": "transverse", "extent_m": 0.08, "res": 160},
        "quantity": "S",
    }
    r_free = client.post("/api/studio/slice", json={**common, "focus_mode": "free-space"})
    r_skin = client.post("/api/studio/slice", json={**common, "focus_mode": "at-skin"})
    assert r_free.status_code == 200, r_free.get_data(as_text=True)
    assert r_skin.status_code == 200, r_skin.get_data(as_text=True)
    # Snapping moves the slice plane center (and the steered field), so the bytes
    # differ from the free-space request.
    assert r_free.data != r_skin.data


@needs_packs
def test_slice_decohered_destroys_focus(client):
    # The decohered baseline scrambles inter-direction phase after collapse: it
    # preserves the angular power spectrum (matched illumination) but destroys
    # the coherent focus, so its peak sits well below MRT yet far above the
    # fully random-phase unfocused floor.
    mrt = _slice_peak(client, "mrt")
    decohered = _slice_peak(client, "decohered")
    unfocused = _slice_peak(client, "unfocused")
    assert mrt["peak_value"] > decohered["peak_value"] * 1.5  # focus destroyed
    assert decohered["peak_value"] > unfocused["peak_value"] * 2.0  # matched illumination floor


@needs_packs
def test_slice_decohered_reproducible(client):
    # Fixed scramble seed -> identical bytes across requests.
    r1 = _slice_post(client, "decohered")
    r2 = _slice_post(client, "decohered")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.data == r2.data


@needs_packs
def test_slice_decohered_preserves_total_power(client):
    # decohere_weights preserves sum_u ||w_u||^2 exactly, so the matched-power
    # property holds: the decohered weight source carries the same total power
    # as the MRT collapse it was built from.
    from aegis.hotspot import collapse_paths
    from aegis.viewer.routes.studio import _paths, _precoders, _slice

    paths = _paths.load_paths("los", 16, 0)
    focus = [0.923, -0.005, 0.734]
    freq_hz = 10e9
    x_mrt = _precoders.build_precoder("mrt", paths, focus, freq_hz)
    _ku, w = collapse_paths(paths[0], paths[1], paths[2], x_mrt)
    _ku2, w_dec = _slice.decohered_field_source(paths, x_mrt)
    assert np.allclose(np.sum(np.abs(w) ** 2), np.sum(np.abs(w_dec) ** 2))


@needs_packs
@needs_qpack
def test_slice_ecbf_via_q_is_fast(client):
    # ECBF loads the precomputed Q operator and runs a 256x256 QCQP solve, never
    # the ~8 min full-body channel build. The whole request must be well under a
    # second of compute, and the exposure-reducing trade must lower the focal
    # peak below MRT.
    import time

    t0 = time.perf_counter()
    r = _slice_post(client, "ecbf")
    dt = time.perf_counter() - t0
    assert r.status_code == 200, r.get_data(as_text=True)
    assert dt < 5.0, f"ecbf slice took {dt:.2f}s (expected a fast Q-pack solve)"
    ecbf = json.loads(r.headers["X-Stats"])
    mrt = _slice_peak(client, "mrt")
    assert ecbf["peak_value"] < mrt["peak_value"]  # trades signal for lower exposure


@needs_packs
def test_slice_ecbf_missing_q_409(client):
    # No Q pack for this frequency: the endpoint returns the not-precomputed
    # sentinel, never the multi-minute full-body build.
    r = _slice_post(client, "ecbf", frequency_ghz=99)
    assert r.status_code == 409, r.get_data(as_text=True)
    j = r.get_json()
    assert j["not_precomputed"] is True
    assert "error" in j


def _volume_post(client, beam, res=20, frequency_ghz=10, extent_m=0.16):
    body = {
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "beam": beam,
        "focus_xyz": [0.923, -0.005, 0.734],
        "frequency_ghz": frequency_ghz,
        "extent_m": extent_m,
        "res": res,
    }
    return client.post("/api/studio/volume", json=body)


@needs_packs
def test_volume_returns_3d_grid(client):
    # The volume endpoint reconstructs power density on a res^3 box and ships it
    # as a float32 buffer with box geometry (origin + spacing) in the X-Stats.
    res = 20
    r = _volume_post(client, "mrt", res=res)
    assert r.status_code == 200, r.get_data(as_text=True)
    stats = json.loads(r.headers["X-Stats"])
    assert stats["shape"] == [res, res, res]
    arr = np.frombuffer(r.data, dtype=np.float32)
    assert arr.size == res**3
    assert np.all(np.isfinite(arr))
    assert float(arr.min()) >= 0.0  # power density is non-negative
    # origin is the min corner: centre - extent/2 on each axis.
    assert stats["origin"][0] == pytest.approx(0.923 - 0.16 / 2, abs=1e-6)
    assert stats["spacing"] == pytest.approx(0.16 / (res - 1), abs=1e-9)
    assert stats["peak_value"] == pytest.approx(float(arr.max()), rel=0, abs=0)


@needs_packs
def test_volume_resolution_is_clamped(client):
    # An unbounded res would allocate res^3 points and OOM; the box clamps to 48.
    r = _volume_post(client, "mrt", res=4096)
    assert r.status_code == 200, r.get_data(as_text=True)
    stats = json.loads(r.headers["X-Stats"])
    assert stats["shape"] == [48, 48, 48]


@needs_packs
@needs_qpack
def test_volume_ecbf_peak_below_mrt(client):
    # The volume honours the beam: ECBF trades focal intensity for lower dose, so
    # its box peak sits below MRT's, mirroring the slice.
    mrt = json.loads(_volume_post(client, "mrt").headers["X-Stats"])
    ecbf = json.loads(_volume_post(client, "ecbf").headers["X-Stats"])
    assert ecbf["peak_value"] < mrt["peak_value"]


@needs_packs
def test_volume_ecbf_missing_q_409(client):
    r = _volume_post(client, "ecbf", frequency_ghz=99)
    assert r.status_code == 409, r.get_data(as_text=True)
    assert r.get_json()["not_precomputed"] is True


@needs_packs
@pytest.mark.parametrize("quantity", ["absH", "ReEx", "ReEy", "ReEz"])
def test_slice_field_quantities(client, quantity):
    r = _slice_post(client, "mrt", quantity=quantity)
    assert r.status_code == 200, r.get_data(as_text=True)
    stats = json.loads(r.headers["X-Stats"])
    arr = np.frombuffer(r.data, dtype=np.float32)
    assert np.all(np.isfinite(arr))
    if quantity == "absH":
        assert stats["units"] == "A/m"
        assert float(arr.min()) >= 0.0  # magnitudes are non-negative
        assert stats["vmax"] > 0.0
    else:
        assert stats["units"] == "V/m"
        # real E components are signed: the diverging colormap handles vmin < 0.
        assert np.any(arr < 0.0) or np.any(arr > 0.0)


@needs_packs
def test_slice_poynting_consistent_with_S(client):
    # Both are non-negative and finite, and in this near-LOS region the Poynting
    # magnitude and S = |E|^2/2Z0 agree to within a modest factor (they are not
    # identical in multipath).
    rs = _slice_post(client, "mrt", quantity="S")
    rp = _slice_post(client, "mrt", quantity="poynting")
    assert rs.status_code == 200
    assert rp.status_code == 200
    s_peak = json.loads(rs.headers["X-Stats"])["peak_value"]
    p_peak = json.loads(rp.headers["X-Stats"])["peak_value"]
    p_arr = np.frombuffer(rp.data, dtype=np.float32)
    assert np.all(np.isfinite(p_arr))
    assert float(p_arr.min()) >= 0.0
    assert s_peak > 0.0
    assert p_peak > 0.0
    assert 0.2 < (p_peak / s_peak) < 5.0


@needs_packs
def test_slice_sab_deferred_400(client):
    # Sab on a free-space slice needs body-intersection machinery; it is
    # deferred and surfaces as a clean 400 the frontend greys out.
    r = _slice_post(client, "mrt", quantity="Sab")
    assert r.status_code == 400
    assert "Sab" in r.get_json()["error"]


@needs_packs
def test_bodymap_worstcase(client):
    r = client.get("/api/studio/bodymap?condition=los&array_n=16&beam=worstcase&quantity=worstcase&frequency_ghz=28")
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    # One value per phantom face: the body map must align to the full-resolution
    # phantom mesh the geometry endpoint serves.
    ph = client.get("/api/studio/phantom?mesh=thelonious")
    n_faces = json.loads(ph.headers["X-Stats"])["n_faces"]
    assert len(j["values"]) == n_faces
    assert j["vmax"] >= j["vmin"]
    assert "provenance" in j


@needs_packs
def test_bodymap_ensemble_statistic_is_los_only(client):
    # The ensemble statistics are computed over LOS seeds only, so an NLOS mean /
    # p95 request must miss cleanly with the not-precomputed sentinel.
    r = client.get("/api/studio/bodymap?condition=nlos&array_n=16&quantity=mrt&frequency_ghz=28&statistic=p95")
    assert r.status_code == 409
    assert r.get_json()["not_precomputed"] is True


@needs_ensemble
def test_bodymap_ensemble_mean_and_p95_served(client):
    # When the ensemble packs are present, mean and p95 serve one value per face
    # and differ from each other (p95 >= mean elementwise for a non-degenerate
    # ensemble, so at least their peaks differ).
    ph = client.get("/api/studio/phantom?mesh=thelonious")
    n_faces = json.loads(ph.headers["X-Stats"])["n_faces"]
    base = "/api/studio/bodymap?condition=los&array_n=16&quantity=mrt&frequency_ghz=28"
    r_mean = client.get(base + "&statistic=mean")
    r_p95 = client.get(base + "&statistic=p95")
    assert r_mean.status_code == 200, r_mean.get_data(as_text=True)
    assert r_p95.status_code == 200, r_p95.get_data(as_text=True)
    vm = np.asarray(r_mean.get_json()["values"])
    vp = np.asarray(r_p95.get_json()["values"])
    assert len(vm) == n_faces
    assert len(vp) == n_faces
    # p95 is an upper tail of the same ensemble, so its peak is at least the mean's.
    assert vp.max() >= vm.max()


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


def _live_bodymap_post(client, beam="mrt", focus_xyz=(0.923, -0.005, 0.734), frequency_ghz=10):
    body = {
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "beam": beam,
        "focus_xyz": list(focus_xyz),
        "focus_mode": "free-space",
        "frequency_ghz": frequency_ghz,
    }
    return client.post("/api/studio/bodymap-live", json=body)


@needs_channel
def test_live_bodymap_tracks_focus(client):
    # The core of the fix: the live deposited map applies the live precoder to the
    # stored field channel, so moving the focus must change the per-triangle map
    # (the precomputed packs were focus-frozen, which is the bug Robin reported).
    near_chest = _live_bodymap_post(client, focus_xyz=(0.923, -0.005, 0.734))
    near_head = _live_bodymap_post(client, focus_xyz=(0.85, -0.02, 1.45))
    assert near_chest.status_code == 200, near_chest.get_data(as_text=True)
    assert near_head.status_code == 200, near_head.get_data(as_text=True)
    va = np.asarray(near_chest.get_json()["values"])
    vb = np.asarray(near_head.get_json()["values"])
    assert not np.array_equal(va, vb)


@needs_channel
def test_live_bodymap_per_triangle(client):
    # One finite, non-negative value per phantom face: the live map aligns to the
    # same full-resolution mesh the geometry endpoint serves.
    r = _live_bodymap_post(client)
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    ph = client.get("/api/studio/phantom?mesh=thelonious")
    n_faces = json.loads(ph.headers["X-Stats"])["n_faces"]
    v = np.asarray(j["values"])
    assert len(v) == n_faces
    assert np.all(np.isfinite(v))
    assert v.min() >= 0.0
    assert j["quantity"] == "deposited"
    assert "provenance" in j


@needs_channel
def test_live_bodymap_decohered_409(client):
    # The decohered baseline is a field-domain weight source, not a per-element
    # precoder, so it does not compose with the field channel: clean 409.
    r = _live_bodymap_post(client, beam="decohered")
    assert r.status_code == 409
    assert r.get_json()["not_precomputed"] is True


@needs_channel
def test_live_bodymap_missing_channel_409(client):
    # A frequency with no channel pack misses cleanly with the sentinel the
    # frontend greys out on.
    r = _live_bodymap_post(client, frequency_ghz=99)
    assert r.status_code == 409
    assert r.get_json()["not_precomputed"] is True
