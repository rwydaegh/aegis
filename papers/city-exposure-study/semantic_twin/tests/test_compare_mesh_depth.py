from __future__ import annotations

import json
import sys

import numpy as np
import pytest

from compare_mesh_depth import BLOCKER_Z, DECISIONS, classify, fit_log_scale, main, scale_plausibility


def test_depth_conflict_labels_closer_ml_surface_as_front_blocker() -> None:
    mesh = np.full((20, 20), 20.0, dtype=np.float32)
    ml = np.full((20, 20), 5.0, dtype=np.float32)
    labels = np.full((20, 20), 1, dtype=np.uint8)
    error = np.full((20, 20), 0.05, dtype=np.float32)
    decision, _ = classify(mesh, ml, error, labels, scale=1.0)
    assert np.all(decision == DECISIONS["front_blocker"])


def test_scale_fit_recovers_known_metric_factor() -> None:
    labels = np.full((20, 20), 1, dtype=np.uint8)
    error = np.full((20, 20), 0.1, dtype=np.float32)
    assert fit_log_scale(np.full((20, 20), 12.0), np.full((20, 20), 3.0), error, labels) == 4.0


def test_second_opinion_inflates_uncertainty_instead_of_creating_false_blocker() -> None:
    mesh = np.full((20, 20), 20.0, dtype=np.float32)
    ml = np.full((20, 20), 5.0, dtype=np.float32)
    labels = np.full((20, 20), 1, dtype=np.uint8)
    error = np.full((20, 20), 0.05, dtype=np.float32)
    decision, _ = classify(
        mesh, ml, error, labels, scale=1.0, second_opinion_range=np.full((20, 20), 1000.0), second_opinion_scale=1.0
    )
    assert np.all(decision != DECISIONS["front_blocker"])


def _pair(mesh: float, first: float, second: float, *, log_sigma: float = 0.05):
    return classify(
        np.full((8, 8), mesh, dtype=np.float32),
        np.full((8, 8), first, dtype=np.float32),
        np.full((8, 8), log_sigma, dtype=np.float32),
        np.full((8, 8), 1, dtype=np.uint8),
        scale=1.0,
        second_opinion_range=np.full((8, 8), second, dtype=np.float32),
        second_opinion_scale=1.0,
    )


def test_a_dissenting_model_leaves_the_pixel_uncertain_rather_than_agreed() -> None:
    # One model puts a surface at a quarter of the mesh range, the other lands on
    # the mesh. Folding the gap into sigma alone would report that as agreement,
    # which paints the pixel as if nothing had objected.
    decision, _ = _pair(20.0, 5.0, 20.0)

    assert np.all(decision == DECISIONS["uncertain"])


def test_a_blocker_needs_every_model_and_reports_the_weakest_claim() -> None:
    together, consensus = _pair(20.0, 4.0, 5.0)
    # The second model still sees something nearer than the mesh, but only half
    # as near. That is not a three-sigma claim it supports, so the louder model
    # must not be able to carry it.
    half_agreed, weaker = _pair(20.0, 4.0, 8.0)
    _alone, single = classify(
        np.full((8, 8), 20.0, dtype=np.float32),
        np.full((8, 8), 4.0, dtype=np.float32),
        np.full((8, 8), 0.05, dtype=np.float32),
        np.full((8, 8), 1, dtype=np.uint8),
        scale=1.0,
    )

    assert np.all(together == DECISIONS["front_blocker"])
    assert np.all(half_agreed == DECISIONS["uncertain"])
    assert np.all(weaker < BLOCKER_Z)
    assert np.all(consensus < single)


def test_the_mesh_conflict_verdict_also_needs_every_model() -> None:
    agreed, _ = _pair(2.0, 40.0, 45.0)
    # One model says the mesh is twenty times too near, the other says it is
    # exactly right. Widening sigma until that fits inside the agreement band
    # would report a flat contradiction as agreement.
    split, _ = _pair(2.0, 40.0, 2.0)

    assert np.all(agreed == DECISIONS["mesh_or_pose_blocker"])
    assert np.all(split == DECISIONS["uncertain"])


def test_withheld_depth_evidence_blocks_nothing_but_still_flags_people() -> None:
    mesh = np.full((8, 8), 20.0, dtype=np.float32)
    mesh[0] = np.nan
    labels = np.full((8, 8), 1, dtype=np.uint8)
    labels[7] = 9

    decision, consensus = classify(
        mesh,
        np.full((8, 8), 1.0, dtype=np.float32),
        np.full((8, 8), 0.05, dtype=np.float32),
        labels,
        scale=1.0,
        depth_evidence=False,
    )

    assert np.all(decision[1:7] == DECISIONS["no_depth_evidence"])
    assert np.all(decision[0] == DECISIONS["no_mesh"])
    assert np.all(decision[7] == DECISIONS["dynamic_object"])
    assert not np.any(np.isin(decision, [DECISIONS["front_blocker"], DECISIONS["mesh_or_pose_blocker"]]))
    assert np.all(consensus == 0.0)


def test_the_shipped_korenmarkt_scales_are_rejected_as_implausible() -> None:
    # The four crops of one Korenmarkt panorama, from
    # outputs/korenmarkt_depth_consistency_two_models/manifest.json.
    report = scale_plausibility(
        {"h+00_000": 0.41417384, "h+00_090": 0.70559335, "h+00_180": 0.45860624, "h+00_270": 0.04506236}
    )

    assert not report["ok"]
    assert report["cross_view_spread"] > 15.0
    assert any("plausible band" in problem for problem in report["problems"])
    assert any("disagree" in problem for problem in report["problems"])


def test_a_consistent_metric_fit_passes_the_plausibility_gate() -> None:
    report = scale_plausibility({"h+00_000": 0.98, "h+00_090": 1.04, "h+00_180": 1.01})

    assert report["ok"]
    assert report["problems"] == []
    assert report["cross_view_spread"] == pytest.approx(1.04 / 0.98)


def test_a_view_that_could_not_be_calibrated_is_a_problem_not_a_pass() -> None:
    report = scale_plausibility({"h+00_000": 1.0}, uncalibrated={"h+00_090": "not enough reliable static pixels"})

    assert not report["ok"]
    assert report["problems"] == ["h+00_090: not enough reliable static pixels"]


def _fixture(tmp_path, *, unidepth_range: float, yaws=(0, 90), depth_anything_range: float | None = None) -> list[str]:
    from PIL import Image

    names = [f"h+00_{yaw:03d}" for yaw in yaws]
    for folder in ("views", "mesh_depth", "unidepth", "sam_labels"):
        (tmp_path / folder).mkdir()
    if depth_anything_range is not None:
        (tmp_path / "depth_anything").mkdir()
    for name in names:
        Image.fromarray(np.zeros((32, 32, 3), dtype=np.uint8)).save(tmp_path / "views" / f"{name}.jpg")
        np.savez(tmp_path / "mesh_depth" / f"{name}.npz", range_m=np.full((32, 32), 4.0, dtype=np.float32))
        np.savez(
            tmp_path / "unidepth" / f"{name}.npz",
            range_m=np.full((32, 32), unidepth_range, dtype=np.float32),
            relative_error=np.full((32, 32), 0.5, dtype=np.float32),
        )
        if depth_anything_range is not None:
            np.savez(
                tmp_path / "depth_anything" / f"{name}.npz",
                range_m=np.full((32, 32), depth_anything_range, dtype=np.float32),
            )
        np.save(tmp_path / "sam_labels" / f"{name}_labels.npy", np.full((32, 32), 1, dtype=np.uint8))
    return names


def _run(tmp_path, monkeypatch, names, *, extra: list[str] | None = None) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "compare_mesh_depth.py",
            "--views",
            str(tmp_path / "views"),
            "--mesh-depth",
            str(tmp_path / "mesh_depth"),
            "--unidepth",
            str(tmp_path / "unidepth"),
            "--sam-labels",
            str(tmp_path / "sam_labels"),
            "--out",
            str(tmp_path / "out"),
            "--yaws",
            *[name[-3:].lstrip("0") or "0" for name in names],
            *(extra or []),
        ],
    )
    main()


def test_a_registration_error_stops_the_run_instead_of_reporting_agreement(tmp_path, monkeypatch) -> None:
    names = _fixture(tmp_path, unidepth_range=60.0)

    with pytest.raises(SystemExit):
        _run(tmp_path, monkeypatch, names)

    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text())
    assert manifest["status"] == "rejected"
    assert manifest["views"] == []
    assert not list((tmp_path / "out").glob("h+00_*.npz"))
    assert not list((tmp_path / "out").glob("*_decisions_overlay.jpg"))


def test_a_plausible_registration_still_classifies_and_reports(tmp_path, monkeypatch) -> None:
    names = _fixture(tmp_path, unidepth_range=4.0)

    _run(tmp_path, monkeypatch, names)

    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text())
    assert manifest["status"] == "ok"
    assert [view["view"] for view in manifest["views"]] == names
    assert manifest["views"][0]["counts"]["agree"] == 32 * 32
    assert (tmp_path / "out" / f"{names[0]}.npz").exists()


def test_a_broken_second_opinion_is_gated_too_rather_than_trusted(tmp_path, monkeypatch) -> None:
    # UniDepth lands on the mesh, so the old gate saw nothing wrong. The second
    # opinion is six times long, which is not a metric claim either.
    names = _fixture(tmp_path, unidepth_range=4.0, depth_anything_range=24.0)

    with pytest.raises(SystemExit):
        _run(tmp_path, monkeypatch, names, extra=["--depth-anything", str(tmp_path / "depth_anything")])

    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text())
    assert manifest["status"] == "rejected"
    assert any("depth_anything" in problem for problem in manifest["scale_plausibility"]["problems"])
    assert not any("unidepth" in problem for problem in manifest["scale_plausibility"]["problems"])


def test_degrading_withholds_the_distance_test_instead_of_stopping(tmp_path, monkeypatch) -> None:
    names = _fixture(tmp_path, unidepth_range=60.0)

    _run(tmp_path, monkeypatch, names, extra=["--on-implausible-scale", "degrade"])

    manifest = json.loads((tmp_path / "out" / "manifest.json").read_text())
    assert manifest["status"] == "implausible_scale_degrade"
    assert not manifest["scale_plausibility"]["ok"]
    for view in manifest["views"]:
        assert view["counts"]["no_depth_evidence"] == 32 * 32
        assert view["counts"]["front_blocker"] == 0
        assert view["counts"]["agree"] == 0
    with np.load(tmp_path / "out" / f"{names[0]}.npz") as document:
        assert not bool(document["depth_evidence"])
