import math

from aegis.study.spike import measure, recommend_cadences


def test_measure_returns_positive_timings():
    calls = {"t": 0, "s": 0, "q": 0}

    def trace():
        calls["t"] += 1

    def sab():
        calls["s"] += 1

    def qref():
        calls["q"] += 1

    timings = measure(trace, sab, qref, n_reps=2)
    assert set(timings) == {"raytrace_s", "dosimetry_s", "q_refresh_s"}
    for v in timings.values():
        assert v >= 0.0
        assert math.isfinite(v)
    # one warm-up + n_reps measured = 3 each
    assert calls == {"t": 3, "s": 3, "q": 3}


def test_recommend_cadences_scales_with_raytrace_cost():
    # expensive ray trace -> coarse recompute period
    slow = recommend_cadences(
        {"raytrace_s": 5.0, "dosimetry_s": 0.1, "q_refresh_s": 0.001},
        budget_s_per_agent=30.0,
        n_slots=60,
    )
    # cheap ray trace -> finer recompute period
    fast = recommend_cadences(
        {"raytrace_s": 0.05, "dosimetry_s": 0.1, "q_refresh_s": 0.001},
        budget_s_per_agent=30.0,
        n_slots=60,
    )
    assert slow["recompute_period"] >= fast["recompute_period"]
    assert slow["recompute_period"] >= 1
    assert slow["dt_s"] == 1.0
    assert slow["pose_period"] == slow["recompute_period"]


def test_recommend_cadences_never_zero():
    c = recommend_cadences(
        {"raytrace_s": 1e6, "dosimetry_s": 1.0, "q_refresh_s": 1.0},
        budget_s_per_agent=1.0,
        n_slots=60,
    )
    assert c["recompute_period"] >= 1


def test_measure_times_gram_when_supplied():
    calls = {"t": 0, "s": 0, "q": 0, "g": 0}
    timings = measure(
        lambda: calls.__setitem__("t", calls["t"] + 1),
        lambda: calls.__setitem__("s", calls["s"] + 1),
        lambda: calls.__setitem__("q", calls["q"] + 1),
        gram_thunk=lambda: calls.__setitem__("g", calls["g"] + 1),
        n_reps=2,
    )
    assert "gram_s" in timings
    assert calls == {"t": 3, "s": 3, "q": 3, "g": 3}


def test_recompute_cost_dominated_by_dosimetry_not_raytrace():
    # Measured real-mesh regime (Ghent core, duke 56k tris, CPU): cheap trace and
    # gram, expensive per-triangle Sab map. The recompute period must reflect the
    # dosimetry cost, not the (negligible) ray trace.
    timings = {"raytrace_s": 0.12, "gram_s": 5.6, "dosimetry_s": 105.0, "q_refresh_s": 0.007}
    c = recommend_cadences(timings, budget_s_per_agent=30.0, n_slots=60)
    # one recompute (~111 s) already blows a 30 s budget, so it can only afford
    # the single mandatory recompute -> coarsest period.
    assert c["recompute_period"] == 60

    # ignoring the gram/dosimetry (the old ray-trace-only model) would wrongly
    # allow a recompute every slot.
    raytrace_only = recommend_cadences({"raytrace_s": 0.12, "q_refresh_s": 0.007}, budget_s_per_agent=30.0, n_slots=60)
    assert raytrace_only["recompute_period"] < c["recompute_period"]
