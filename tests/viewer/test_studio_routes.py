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
    assert scene["beam"] == "ecbf"
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
    assert iso > 0
    assert patch > 0
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


def _scene_present() -> bool:
    from aegis.viewer.routes.studio import studio_data_dir

    return (studio_data_dir() / "scene" / "nlos_seed0.json").is_file()


needs_scene = pytest.mark.skipif(not _scene_present(), reason="studio scene packs not present")


def test_get_scene_reads_pack(monkeypatch, tmp_path):
    from aegis.viewer.routes.studio import _scene

    monkeypatch.setenv("AEGIS_STUDIO_PATHS", str(tmp_path))
    scene_dir = tmp_path / "scene"
    scene_dir.mkdir()
    payload = {
        "room_dims": [40, 20, 5],
        "blocker": {"center": [-8, 0, 2.5], "size": [0.5, 2, 4.98]},
        "scatterers": [{"center": [1, 2, 1], "size": [2, 0.5, 2], "yaw_rad": 0.1}],
    }
    (scene_dir / "nlos_seed0.json").write_text(json.dumps(payload))
    out = _scene.get_scene("nlos", 0)
    assert out["blocker"]["center"] == [-8, 0, 2.5]
    assert len(out["scatterers"]) == 1
    assert "provenance" in out
    assert not out.get("not_precomputed")


def test_get_scene_nlos_collapses_to_seed0(monkeypatch, tmp_path):
    from aegis.viewer.routes.studio import _scene

    monkeypatch.setenv("AEGIS_STUDIO_PATHS", str(tmp_path))
    scene_dir = tmp_path / "scene"
    scene_dir.mkdir()
    (scene_dir / "nlos_seed0.json").write_text(json.dumps({"scatterers": [], "blocker": None}))
    # Any NLOS seed resolves to the single NLOS realisation (seed 0).
    out = _scene.get_scene("nlos", 5)
    assert not out.get("not_precomputed")
    assert out["provenance"].endswith("nlos seed0")


def test_get_scene_missing_returns_sentinel(monkeypatch, tmp_path):
    from aegis.viewer.routes.studio import _scene

    monkeypatch.setenv("AEGIS_STUDIO_PATHS", str(tmp_path))
    out = _scene.get_scene("los", 0)
    assert out["not_precomputed"] is True
    assert out["stem"] == "los_seed0"


@needs_scene
def test_scene_route_hit_and_miss(client):
    r = client.get("/api/studio/scene?condition=nlos&seed=0")
    assert r.status_code == 200
    d = r.get_json()
    assert d["blocker"] is not None
    assert d["scatterers"]
    miss = client.get("/api/studio/scene?condition=los&seed=99")
    assert miss.status_code == 409
    assert miss.get_json()["not_precomputed"] is True


def _precoder_post(client, beam, frequency_ghz=28, array_n=16):
    body = {
        "condition": "los",
        "array_n": array_n,
        "seed": 0,
        "beam": beam,
        "focus_xyz": [0.923, -0.005, 0.734],
        "focus_mode": "free-space",
        "frequency_ghz": frequency_ghz,
        "ue_idx": 4,
    }
    return client.post("/api/studio/precoder", json=body)


@needs_packs
def test_precoder_mrt_returns_weights_and_geometry(client):
    # The MRT precoder feeds the live transmit radiation lobe: a matched-power
    # per-element vector (||x||^2 == 1) paired with the physical URA geometry it
    # is indexed against, so the frontend can draw the realised beam.
    r = _precoder_post(client, "mrt", frequency_ghz=28)
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["available"] is True
    assert d["n_h"] == 16
    assert d["n_v"] == 16
    assert len(d["real"]) == 256
    assert len(d["imag"]) == 256
    x = np.asarray(d["real"]) + 1j * np.asarray(d["imag"])
    assert np.isclose(np.sum(np.abs(x) ** 2), 1.0, atol=1e-3)
    # Panel axes: horizontal e_y and panel-up e_zp tilted 10 deg down, plus the
    # half-wave spacing and the design (dosimetry) frequency k0 must match.
    assert np.allclose(d["axis_h"], [0.0, 1.0, 0.0])
    assert np.allclose(d["axis_v"], [np.sin(np.deg2rad(10)), 0.0, np.cos(np.deg2rad(10))], atol=1e-6)
    assert np.isclose(d["spacing_m"], 0.5 * 299792458.0 / 28e9)
    assert np.isclose(d["freq_hz"], 28e9)


@needs_packs
def test_precoder_design_frequency_follows_request(client):
    # x is synthesised at the dosimetry frequency, so the array-factor k0 the lobe
    # uses must follow the requested frequency (not the fixed 28 GHz panel carrier).
    r = _precoder_post(client, "mrt", frequency_ghz=10)
    assert r.status_code == 200
    assert np.isclose(r.get_json()["freq_hz"], 10e9)


@needs_packs
def test_precoder_decohered_unavailable(client):
    # The decohered baseline scrambles inter-direction phase after collapse and is
    # not a per-element precoder, so it reports available=false (the lobe falls
    # back to the uniform-excitation pattern) rather than erroring.
    r = _precoder_post(client, "decohered")
    assert r.status_code == 200
    assert r.get_json()["available"] is False


# --- GEP precoder + compliance scalars ------------------------------------------


def test_build_gep_reduces_to_mrt_when_q_is_identity():
    # With Q = I the exposure operator imposes no preference, so the
    # signal-per-absorbed-power optimum x propto Q^{-1} conj(h) collapses onto the
    # matched filter x propto conj(h). This pins the GEP eigen-math independent of
    # any pack: same h, same normalisation, so the two precoders must coincide.
    from aegis.viewer.routes.studio._precoders import build_gep_from_q, build_precoder

    rng = np.random.default_rng(0)
    n_elements = 4
    n_paths = 6
    k_hat = rng.normal(size=(n_paths, 3))
    k_hat /= np.linalg.norm(k_hat, axis=1, keepdims=True)
    psi = rng.normal(size=(n_paths, 3)) + 1j * rng.normal(size=(n_paths, 3))
    element_index = np.array([0, 1, 2, 3, 0, 1], dtype=np.int64)
    paths = (k_hat, psi, element_index, n_elements)
    focus = [0.9, 0.0, 0.7]
    freq_hz = 28e9

    q = np.eye(n_elements, dtype=complex)
    x_gep = build_gep_from_q(paths, focus, freq_hz, q, power=1.0)
    x_mrt = build_precoder("mrt", paths, focus, freq_hz, power=1.0)
    assert np.allclose(x_gep, x_mrt, atol=1e-10)
    # Unit transmit power.
    assert np.isclose(np.vdot(x_gep, x_gep).real, 1.0, atol=1e-10)


def test_compute_scalars_math_is_self_consistent():
    # Deterministic check of the scalar definitions with an identity averaging
    # matrix (so psSAR = peak per-triangle Sab) and x == x_mrt (so signal_rel = 1).
    from scipy import sparse

    from aegis.viewer.routes.studio._compliance import compute_scalars

    n_tri, n_ant = 5, 3
    rng = np.random.default_rng(1)
    g_tilde = rng.normal(size=(n_tri, 3, n_ant)) + 1j * rng.normal(size=(n_tri, 3, n_ant))
    areas = np.full(n_tri, 2.0)
    x = rng.normal(size=n_ant) + 1j * rng.normal(size=n_ant)
    h = rng.normal(size=n_ant) + 1j * rng.normal(size=n_ant)
    g_avg = sparse.eye(n_tri, format="csr")

    out = compute_scalars(g_tilde, areas, x, h, x, g_avg, body_mass=70.0)

    sab = (np.abs(np.einsum("tim,m->ti", g_tilde, x)) ** 2).sum(axis=1)
    assert np.isclose(out["p_abs_w"], float((sab * areas).sum()))
    assert np.isclose(out["pssar_4cm2"], float(sab.max()))  # identity averaging
    assert np.isclose(out["peak_sab"], float(sab.max()))
    assert np.isclose(out["mean_sab"], out["p_abs_w"] / areas.sum())
    assert np.isclose(out["eta_4cm2"], out["pssar_4cm2"] / out["mean_sab"])
    assert np.isclose(out["sar_wb"], out["p_abs_w"] / 70.0)
    # x_mrt == x, so the beam delivers exactly the reference signal.
    assert np.isclose(out["signal_rel"], 1.0)
    # No SNR anchor requested: spectral efficiency is left undefined.
    assert out["spectral_efficiency_bps_hz"] is None


def test_spectral_efficiency_anchors_to_snr():
    # The studio runs in normalised units, so the served rate is only defined
    # relative to MRT via an SNR anchor: R = log2(1 + SNR_mrt * signal_rel). At
    # the MRT operating point (signal_rel = 1) it is exactly log2(1 + SNR_mrt).
    from scipy import sparse

    from aegis.viewer.routes.studio._compliance import compute_scalars

    rng = np.random.default_rng(2)
    n_tri, n_ant = 4, 3
    g_tilde = rng.normal(size=(n_tri, 3, n_ant)) + 1j * rng.normal(size=(n_tri, 3, n_ant))
    areas = np.full(n_tri, 1.0)
    h = rng.normal(size=n_ant) + 1j * rng.normal(size=n_ant)
    g_avg = sparse.eye(n_tri, format="csr")

    # x == x_mrt -> signal_rel == 1 -> R == log2(1 + SNR_mrt).
    mrt = compute_scalars(g_tilde, areas, h, h, h, g_avg, body_mass=None, snr_mrt_db=20.0)
    assert mrt["snr_mrt_db"] == pytest.approx(20.0)
    assert mrt["spectral_efficiency_bps_hz"] == pytest.approx(np.log2(1.0 + 100.0))

    # A weaker beam (half the field) keeps signal_rel = 0.25 and the rate follows.
    x_half = 0.5 * h
    weak = compute_scalars(g_tilde, areas, x_half, h, h, g_avg, body_mass=None, snr_mrt_db=20.0)
    assert weak["signal_rel"] == pytest.approx(0.25)
    assert weak["spectral_efficiency_bps_hz"] == pytest.approx(np.log2(1.0 + 100.0 * 0.25))


def test_compute_scalars_is_homogeneous_in_transmit_power():
    # The whole pipeline is quadratic in the precoder x, so scaling x by c (i.e.
    # transmit power by c^2) scales every absorbed-power density / power by c^2
    # while signal_rel and eta (ratios) stay invariant. This is what licenses the
    # frontend to rescale absolute readouts by a single power factor client-side.
    from scipy import sparse

    from aegis.viewer.routes.studio._compliance import compute_scalars

    rng = np.random.default_rng(3)
    n_tri, n_ant = 6, 4
    g_tilde = rng.normal(size=(n_tri, 3, n_ant)) + 1j * rng.normal(size=(n_tri, 3, n_ant))
    areas = rng.uniform(0.5, 2.0, n_tri)
    x = rng.normal(size=n_ant) + 1j * rng.normal(size=n_ant)
    h = rng.normal(size=n_ant) + 1j * rng.normal(size=n_ant)
    x_mrt = rng.normal(size=n_ant) + 1j * rng.normal(size=n_ant)
    g_avg = sparse.eye(n_tri, format="csr")

    c = 1.7  # field scale; transmit power scales by c^2
    base = compute_scalars(g_tilde, areas, x, h, x_mrt, g_avg, body_mass=70.0, snr_mrt_db=20.0)
    # Scale BOTH x and x_mrt so signal_rel stays a true ratio (as the routes do).
    scaled = compute_scalars(g_tilde, areas, c * x, h, c * x_mrt, g_avg, body_mass=70.0, snr_mrt_db=20.0)

    for key in ("p_abs_w", "sar_wb", "pssar_4cm2", "peak_sab", "mean_sab"):
        assert scaled[key] == pytest.approx(base[key] * c**2, rel=1e-9), key
    # Ratios and the SNR-anchored rate are invariant to transmit power.
    assert scaled["signal_rel"] == pytest.approx(base["signal_rel"], rel=1e-9)
    assert scaled["eta_4cm2"] == pytest.approx(base["eta_4cm2"], rel=1e-9)
    assert scaled["spectral_efficiency_bps_hz"] == pytest.approx(base["spectral_efficiency_bps_hz"], rel=1e-9)


def test_manifest_exposes_calibration_power(client):
    j = client.get("/api/studio/manifest").get_json()
    assert j["calibration_tx_power_dbm"] == pytest.approx(25.0)
    # 25 dBm = 10^((25-30)/10) W = 0.31623 W total.
    assert j["calibration_power_w"] == pytest.approx(10 ** ((25.0 - 30.0) / 10.0), rel=1e-9)


def test_body_mass_kg_reads_phantoms_yaml():
    from aegis.viewer.routes.studio._compliance import body_mass_kg

    assert body_mass_kg("thelonious") == pytest.approx(17.4)
    assert body_mass_kg("duke") == pytest.approx(72.4)
    assert body_mass_kg("nope") is None


def _compliance_post(client, beam="mrt", frequency_ghz=10, ecbf_budget_frac=0.5, focus_xyz=(0.923, -0.005, 0.734)):
    body = {
        "mesh": "thelonious",
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "beam": beam,
        "focus_xyz": list(focus_xyz),
        "focus_mode": "free-space",
        "frequency_ghz": frequency_ghz,
        "ecbf_budget_frac": ecbf_budget_frac,
    }
    return client.post("/api/studio/compliance", json=body)


@needs_channel
def test_compliance_mrt_scalars(client):
    r = _compliance_post(client, beam="mrt")
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    for key in ("p_abs_w", "sar_wb", "pssar_4cm2", "eta_4cm2", "signal_rel"):
        assert key in j
    assert np.isfinite(j["p_abs_w"])
    assert j["p_abs_w"] > 0
    assert np.isfinite(j["sar_wb"])
    assert j["sar_wb"] > 0
    # SAR_wb = P_abs / body mass (thelonious = 17.4 kg from phantoms.yaml).
    assert j["sar_wb"] == pytest.approx(j["p_abs_w"] / 17.4, rel=1e-6)
    # psSAR (4 cm^2 averaged peak) cannot exceed the raw per-triangle peak.
    assert j["pssar_4cm2"] <= j["peak_sab"] + 1e-12
    # eta = psSAR / mean Sab >= 1 (the peak averaged density beats the mean).
    assert j["eta_4cm2"] >= 1.0
    # The MRT beam is its own reference, so it delivers exactly the MRT signal.
    assert j["signal_rel"] == pytest.approx(1.0, abs=1e-6)
    assert j["averaging_area_cm2"] == pytest.approx(4.0)


@needs_channel
@needs_qpack
def test_compliance_ecbf_trades_signal_for_absorption(client):
    # ECBF at half the MRT absorption budget must absorb less power and deliver
    # less signal than MRT: the compliance trade-off the panel exists to show.
    mrt = _compliance_post(client, beam="mrt").get_json()
    ecbf = _compliance_post(client, beam="ecbf", ecbf_budget_frac=0.5).get_json()
    assert ecbf["p_abs_w"] < mrt["p_abs_w"]
    assert ecbf["signal_rel"] < 1.0
    assert 0.0 < ecbf["signal_rel"] <= 1.0


@needs_channel
@needs_qpack
def test_compliance_gep_is_valid(client):
    r = _compliance_post(client, beam="gep")
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert np.isfinite(j["p_abs_w"])
    assert j["p_abs_w"] > 0
    assert 0.0 < j["signal_rel"] <= 1.0 + 1e-9


@needs_channel
def test_compliance_reports_spectral_efficiency(client):
    # The compliance route anchors a default 20 dB MRT SNR, so MRT (signal_rel = 1)
    # reports exactly log2(1 + 100) bit/s/Hz.
    j = _compliance_post(client, beam="mrt").get_json()
    assert j["snr_mrt_db"] == pytest.approx(20.0)
    assert j["spectral_efficiency_bps_hz"] == pytest.approx(np.log2(101.0), rel=1e-6)


@needs_channel
@needs_qpack
def test_compliance_sweep_traces_pareto_front(client):
    # The budget sweep re-solves ECBF across the absorbed-power budget. P_abs must
    # be non-decreasing in the budget (a looser cap can only raise absorption) and
    # the served signal rises with it: the exposure/signal trade the chart shows.
    body = {
        "mesh": "thelonious",
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "focus_xyz": [0.923, -0.005, 0.734],
        "focus_mode": "free-space",
        "frequency_ghz": 10,
        "n_points": 12,
        "snr_mrt_db": 20.0,
    }
    r = client.post("/api/studio/compliance-sweep", json=body)
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    fracs = j["budget_frac"]
    assert len(fracs) == 12
    assert fracs[0] == pytest.approx(0.05)
    assert fracs[-1] == pytest.approx(1.0)

    p_abs = np.asarray(j["series"]["p_abs_w"])
    signal = np.asarray(j["series"]["signal_rel"])
    se = np.asarray(j["series"]["spectral_efficiency_bps_hz"])
    # Monotone (allow a tiny solver tolerance), and signal stays a fraction of MRT.
    assert np.all(np.diff(p_abs) >= -1e-9)
    assert np.all(np.diff(signal) >= -1e-6)
    assert np.all((signal > 0.0) & (signal <= 1.0 + 1e-9))
    # Spectral efficiency tracks signal through the SNR anchor.
    assert np.all(se >= 0.0)
    assert se[-1] == pytest.approx(np.log2(1.0 + 100.0 * signal[-1]), rel=1e-6)


@needs_channel
def test_compliance_sweep_missing_channel_409(client):
    r = client.post("/api/studio/compliance-sweep", json={"frequency_ghz": 99})
    assert r.status_code == 409
    assert r.get_json()["not_precomputed"] is True


@needs_channel
def test_compliance_decohered_409(client):
    # No per-element precoder to score, same sentinel the live body map uses.
    r = _compliance_post(client, beam="decohered")
    assert r.status_code == 409
    assert r.get_json()["not_precomputed"] is True


@needs_channel
def test_compliance_missing_channel_409(client):
    r = _compliance_post(client, frequency_ghz=99)
    assert r.status_code == 409
    assert r.get_json()["not_precomputed"] is True


def _absolute_compliance_post(client, tx_power_w, sar_wb_on=True, peak_sab_on=True):
    body = {
        "mesh": "thelonious",
        "condition": "los",
        "array_n": 16,
        "seed": 0,
        "beam": "ecbf",
        "focus_xyz": [0.923, -0.005, 0.734],
        "focus_mode": "free-space",
        "frequency_ghz": 10,
        "constraint_mode": "absolute",
        "sar_wb_on": sar_wb_on,
        "peak_sab_on": peak_sab_on,
        "tx_power_w": tx_power_w,
    }
    return client.post("/api/studio/compliance", json=body)


@needs_channel
def test_compliance_absolute_reports_regime_and_constraints(client):
    # Absolute mode returns the binding regime and a per-restriction utilisation
    # readout the HUD renders as the regime badge + margin bars.
    r = _absolute_compliance_post(client, tx_power_w=1.0)
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j["constraint_mode"] == "absolute"
    assert j["regime"] in ("free", "sar_wb", "peak_sab", "both", "infeasible")
    names = {c["name"] for c in j["per_constraint"]}
    assert names == {"sar_wb", "peak_sab"}
    for c in j["per_constraint"]:
        assert c["limit"] > 0
        assert c["utilisation"] == pytest.approx(c["value"] / c["limit"], rel=1e-6)
    # The ICNIRP limit values for the current frequency are echoed for the panel.
    assert j["icnirp_limits"]["sar_wb"] == pytest.approx(0.08)
    assert j["icnirp_limits"]["sab_4cm2"] == pytest.approx(20.0)
    assert j["tx_power_w"] == pytest.approx(1.0)


@needs_channel
def test_compliance_absolute_flattens_with_power(client):
    # The core value proposition: at low power nothing binds (the beam is free),
    # but raising transmit power past the knee drives ECBF into a binding regime
    # where the absorbed power stops scaling with power. The knee for the default
    # thelonious / 10 GHz geometry is ~1 kW (whole-body SAR), so straddle it.
    lo = _absolute_compliance_post(client, tx_power_w=10.0).get_json()
    hi = _absolute_compliance_post(client, tx_power_w=4000.0).get_json()
    assert lo["regime"] == "free"
    assert hi["regime"] in ("sar_wb", "peak_sab", "both")
    # MRT absorption would have scaled by 400x with the power; ECBF flattens, so
    # the absorbed power grows far less than linearly past the knee.
    assert hi["p_abs_w"] < 400.0 * lo["p_abs_w"]
    # The whole-body bound caps absorbed power at L_wb * mass.
    if hi["regime"] in ("sar_wb", "both"):
        assert hi["p_abs_w"] == pytest.approx(0.08 * 17.4, rel=1e-2)


@needs_packs
@needs_qpack
def test_slice_gep_computes(client):
    # GEP solves against the same Q pack ECBF uses and returns a valid field.
    # Unlike MRT it is exposure-avoiding (it maximises signal per absorbed power),
    # so its field on the body focus is deliberately low rather than peaked; the
    # signal-efficiency property is checked in the compliance / identity-Q tests.
    gep = _slice_peak(client, "gep")
    assert np.isfinite(gep["peak_value"])
    assert gep["peak_value"] > 0.0


@needs_packs
def test_slice_gep_missing_q_409(client):
    r = _slice_post(client, "gep", frequency_ghz=99)
    assert r.status_code == 409
    assert r.get_json()["not_precomputed"] is True
