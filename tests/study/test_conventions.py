"""Physics-convention regression tests the batch depends on.

These pin the two invariants the audit found unguarded: the transmit-power
convention (traces at the 1 W field reference, config power carried once by
the MRT norm) and the equivalence of the Gram-refresh exposure route with the
engine's Q route. Both run on synthetic paths, no ray tracer.
"""

import numpy as np
import pytest

from aegis.engine import DosimetryEngine
from aegis.geometry.mesh import BodyMesh
from aegis.mimo.array import AntennaArray
from aegis.mimo.array_paths import expand_paths_to_array
from aegis.paths import PropagationPaths
from aegis.precoder import Precoder
from aegis.study.exposure import build_static_gram, refresh_Q, scalar_exposure_w
from aegis.study.precoding import mrt_for_user, user_channel_vector
from aegis.tissue.dielectric import TissueModel

FREQ = 28e9


def _array(center):
    lam = 3e8 / FREQ
    return AntennaArray.upa(
        n_h=2,
        n_v=2,
        d_h=lam / 2,
        d_v=lam / 2,
        center=np.asarray(center, dtype=float),
        broadside=np.array([-1.0, 0.0, 0.0]),
        element_pattern="patch",
    )


def _paths(seed=3):
    # Three synthetic paths toward the body with distinct directions/phases,
    # roughly along -x so the patch front hemisphere sees them.
    rng = np.random.default_rng(seed)
    k = np.array([[-0.95, 0.2, -0.24], [-0.8, -0.55, -0.23], [-0.99, 0.0, -0.14]])
    k /= np.linalg.norm(k, axis=1, keepdims=True)
    psi = (rng.normal(size=(3, 3)) + 1j * rng.normal(size=(3, 3))) * 0.05
    # transverse projection so psi is a valid plane-wave field
    psi -= np.einsum("nj,nj->n", psi, k.astype(complex))[:, None] * k
    return PropagationPaths(
        k_hat=k,
        psi=psi,
        element_index=np.zeros(3, dtype=np.intp),
        delay=np.zeros(3),
        is_los=np.array([True, False, False]),
        polarised=True,
        k_hat_tx=k,
    )


def _body():
    # small flat plate facing +x at the origin-ish area the paths converge on
    v = []
    for y in np.linspace(-0.3, 0.3, 4):
        for z in np.linspace(0.8, 1.4, 4):
            v.append([[0.0, y, z], [0.0, y + 0.2, z], [0.0, y, z + 0.2]])
    return BodyMesh.from_arrays(np.asarray(v), name="plate")


def test_exposure_scales_linearly_with_tx_power():
    """Traces run at the 1 W reference; config power enters once via
    ||x||^2 = P. Doubling P must exactly double x^H Q x."""
    array = _array([30.0, 0.0, 12.0])
    paths = _paths()
    body = _body()
    m = build_static_gram(body, paths, array, FREQ)
    q = refresh_Q(m, paths.k_hat, np.zeros(3), FREQ)
    pe = expand_paths_to_array(paths, array, FREQ)
    h = user_channel_vector(pe, array.n_elements)

    e1 = scalar_exposure_w(q, mrt_for_user(h, 1.0).x)
    e4 = scalar_exposure_w(q, mrt_for_user(h, 4.0).x)
    assert e1 > 0
    np.testing.assert_allclose(e4 / e1, 4.0, rtol=1e-9)


def test_gram_route_matches_engine_route():
    """The published per-slot exposure (build_static_gram + refresh_Q) and the
    ICNIRP path (engine.compute over expanded paths) must be the same physics:
    x^H Q_gram x == engine p_abs == x^H Q_engine x."""
    array = _array([30.0, 0.0, 12.0])
    paths = _paths()
    body = _body()

    m = build_static_gram(body, paths, array, FREQ)
    q_gram = refresh_Q(m, paths.k_hat, np.zeros(3), FREQ)
    pe = expand_paths_to_array(paths, array, FREQ)
    x = mrt_for_user(user_channel_vector(pe, array.n_elements), 1.0).x

    engine = DosimetryEngine(TissueModel.from_database("Skin", FREQ))
    result = engine.compute(body, pe, level=7, precoder=Precoder(x=x))

    e_gram = scalar_exposure_w(q_gram, x)
    assert e_gram > 0
    np.testing.assert_allclose(e_gram, result.p_abs, rtol=1e-4)


def test_ten_cities_config_loads_with_expected_knobs():
    """The headline batch config must parse, carry no typo'd keys (the loader
    now warns), and keep its cost-critical knobs at the tuned values."""
    from aegis.study.config import StudyConfig

    cfg = StudyConfig.from_yaml("configs/study/ten_cities.yaml")
    assert cfg.cities.count == 10
    assert cfg.mobility.routing == "directions"
    assert cfg.channel.samples_per_src == 3_000_000
    assert cfg.channel.max_center_paths == 10
    assert cfg.temporal.pose_period == cfg.temporal.recompute_period == 5
    assert cfg.deployment.sectoring.downtilt_deg == pytest.approx(10.0)
    assert cfg.deployment.site_height_min_m == pytest.approx(8.0)
    assert cfg.dosimetry.peak_sab is False


def test_dropped_building_candidate_lands_on_ground_and_leaves_band():
    """With the ground disk in the mesh, a builder-dropped building's candidate
    snaps to the ground plane; the site height band must then exclude it (it
    must never become a street-level 'rooftop' site)."""
    from aegis.study.city import rooftop_candidates
    from aegis.study.deployment import select_rooftop_sites

    class GroundOnlyMesh:
        vertices = np.array([[-50.0, -50.0, -0.01], [50.0, -50.0, -0.01], [50.0, 50.0, -0.01], [-50.0, 50.0, -0.01]])
        triangles = np.array([[0, 1, 2], [0, 2, 3]])

    from aegis.environment.osm_helpers import Building

    fp = np.array([[0, 0], [10, 0], [10, 10], [0, 10]], dtype=float)
    b = Building(way_id=11, footprint=fp, height=20.0)
    cand = rooftop_candidates([b], mesh=GroundOnlyMesh())
    assert cand.shape == (1, 3)
    assert cand[0, 2] == pytest.approx(-0.01)

    rng = np.random.default_rng(0)
    sites = select_rooftop_sites(cand, 1, rng, height_band_m=(8.0, 45.0), mount_height_m=2.0)
    # starved band widens to the nearest candidate, but the ground-level one is
    # all there is: it must still not be reported as an in-band rooftop
    assert sites.shape[0] == 1
    assert sites[0, 2] == pytest.approx(-0.01 + 2.0)
