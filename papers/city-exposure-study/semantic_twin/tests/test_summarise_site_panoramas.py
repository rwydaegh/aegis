from __future__ import annotations

import json
import pathlib

from semantic_twin.report.panorama_registration import markdown, panorama_rows, summarise, write_summary


def write_panorama(
    site: pathlib.Path,
    name: str,
    *,
    residual: float | None = 1.0,
    at_bound: bool = False,
    aligned: bool = True,
    date: str = "2014-06",
    initial_z: float = 10.0,
    final_z: float = 10.5,
    orientation: str = "map tiles streetview metadata tilt and roll",
) -> None:
    pano = site / name
    pano.mkdir(parents=True, exist_ok=True)
    (pano / "metadata.json").write_text(json.dumps({"panoId": name.upper(), "date": date}))
    (pano / "pose_initial.json").write_text(json.dumps({"position_enu_m": [0.0, 0.0, initial_z]}))
    if not aligned:
        return
    (pano / "alignment").mkdir(exist_ok=True)
    (pano / "alignment" / "pose_aligned.json").write_text(
        json.dumps(
            {
                "position_enu_m": [0.0, 0.0, final_z],
                "skyline_score_mean_deg": residual,
                "skyline_signed_residual_median_deg": -0.2,
                "skyline_dz_at_bound": at_bound,
                "n_observed_structural_skyline_samples": 900,
                "orientation_source": orientation,
                "provenance": {"ground_minus_scene_constant_m": 0.01, "ground_spread_m": 0.02},
            }
        )
    )


def test_an_unregistered_panorama_is_counted_but_not_scored(tmp_path):
    site = tmp_path / "prague"
    write_panorama(site, "pano_00_a", residual=0.8)
    write_panorama(site, "pano_01_b", aligned=False)
    summary = summarise(site)
    assert summary["panoramas"] == 2
    assert summary["registered"] == 1
    assert summary["residual_deg"]["median"] == 0.8


def test_residual_spread_is_reported_over_the_site(tmp_path):
    site = tmp_path / "zocalo"
    for index, residual in enumerate([0.5, 1.5, 2.5]):
        write_panorama(site, f"pano_{index:02d}_x", residual=residual)
    summary = summarise(site)
    assert summary["residual_deg"] == {"median": 1.5, "min": 0.5, "max": 2.5}


def test_poses_pinned_to_their_altitude_bound_are_counted(tmp_path):
    site = tmp_path / "madrid"
    write_panorama(site, "pano_00_a", at_bound=True)
    write_panorama(site, "pano_01_b", at_bound=True)
    write_panorama(site, "pano_02_c", at_bound=False)
    assert summarise(site)["poses_at_altitude_bound"] == 2


def test_a_capture_with_no_orientation_solution_is_counted(tmp_path):
    site = tmp_path / "site"
    write_panorama(site, "pano_00_a", orientation="degenerate: tilt is exactly 90 and roll exactly 0")
    write_panorama(site, "pano_01_b")
    assert summarise(site)["poses_without_measured_orientation"] == 1


def test_pose_correction_is_the_distance_registration_moved_the_camera(tmp_path):
    site = tmp_path / "site"
    write_panorama(site, "pano_00_a", initial_z=10.0, final_z=13.0)
    assert summarise(site)["pose_correction_m"]["max"] == 3.0


def test_rows_survive_a_site_with_no_panoramas(tmp_path):
    site = tmp_path / "empty"
    site.mkdir()
    assert panorama_rows(site) == []
    summary = summarise(site)
    assert summary["registered"] == 0
    assert summary["residual_deg"]["median"] is None


def test_markdown_does_not_print_none_for_a_site_with_nothing_registered(tmp_path):
    site = tmp_path / "empty"
    site.mkdir()
    table = markdown([summarise(site)])
    assert "n/a" in table
    assert "None" not in table


def test_writer_preserves_the_json_and_markdown_contract(tmp_path):
    site = tmp_path / "prague"
    write_panorama(site, "pano_00_a", residual=0.8)
    output = tmp_path / "report"

    rendered = write_summary([site], output)

    assert (output / "panorama_registration.md").read_text() == rendered
    json_text = (output / "panorama_registration.json").read_text()
    assert json_text.endswith("\n")
    assert json.loads(json_text) == [summarise(site)]
