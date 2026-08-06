"""The datum estimator and the coverage table it feeds.

Both are small, and both are the kind of small that quietly decides a number in
a published table, so they are pinned here rather than trusted.
"""

from __future__ import annotations

import numpy as np
import pytest

from semantic_twin import paths
from semantic_twin.scene import site_config_build

trimesh = pytest.importorskip("trimesh")
pytest.importorskip("trimesh.ray.ray_pyembree")

from semantic_twin.report.evidence_coverage import markdown, splice  # noqa: E402
from semantic_twin.scene.site_config_build import ground_datum  # noqa: E402


def square_with_a_block(tmp_path, ground_z=10.0, roof_z=30.0, half=90.0, block=40.0):
    """A flat square at ``ground_z`` carrying one central block up to ``roof_z``.

    This is Krakow in miniature: the centroid of the square is the top of a free
    standing building, so a datum measured under the anchor reads the roof and a
    datum measured over the square reads the square.
    """
    plane = trimesh.creation.box(extents=(2 * half, 2 * half, 1.0))
    plane.apply_translation((0.0, 0.0, ground_z - 0.5))
    tower = trimesh.creation.box(extents=(block, block, roof_z - ground_z))
    tower.apply_translation((0.0, 0.0, 0.5 * (roof_z + ground_z)))
    path = tmp_path / "crop.ply"
    trimesh.util.concatenate([plane, tower]).export(path)
    return path


def test_the_datum_is_the_square_and_not_the_roof_above_its_centroid(tmp_path):
    datum = ground_datum(square_with_a_block(tmp_path), radius_m=80.0, samples=4000)
    assert datum["camera_ground_z_m"] == pytest.approx(10.0, abs=0.05)
    assert datum["anchor_topmost_surface_m"] == pytest.approx(30.0, abs=0.05)


def test_the_datum_reports_how_dominant_the_surface_it_chose_is(tmp_path):
    datum = ground_datum(square_with_a_block(tmp_path), radius_m=80.0, samples=4000)
    # The block covers 40 by 40 of a 160 m disc, so most of the disc is square.
    assert 0.6 < datum["modal_share"] < 1.0


def test_a_roof_wider_than_the_square_still_does_not_become_the_datum(tmp_path):
    # The mode is searched below the midpoint of the relief precisely so that a
    # site whose roofs outnumber its open ground cannot invert the answer.
    path = square_with_a_block(tmp_path, block=150.0)
    datum = ground_datum(path, radius_m=80.0, samples=4000)
    assert datum["camera_ground_z_m"] == pytest.approx(10.0, abs=0.05)


def test_an_empty_crop_is_refused_rather_than_guessed(tmp_path):
    far = trimesh.creation.box(extents=(4.0, 4.0, 1.0))
    far.apply_translation((5000.0, 5000.0, 0.0))
    path = tmp_path / "empty.ply"
    far.export(path)
    with pytest.raises(SystemExit, match="no surface under the crop"):
        ground_datum(path, radius_m=80.0, samples=200)


@pytest.mark.parametrize(("site", "crop_m"), (("korenmarkt", 130), ("milan_duomo", 170)))
@pytest.mark.local_data
def test_a_rebuilt_config_records_the_acquisition_mesh_not_the_preferred_trace_mesh(monkeypatch, site, crop_m):
    datum = {
        "camera_ground_z_m": 1.0,
        "method": "fixture",
        "modal_share": 1.0,
        "band_spread_m": 0.0,
        "relief_m": [1.0, 1.0],
        "anchor_topmost_surface_m": 1.0,
    }
    monkeypatch.setattr(site_config_build, "ground_datum", lambda *_args, **_kwargs: datum)

    document = site_config_build.build(
        site,
        crop_m=crop_m,
        screening=paths.screening(),
        walk_date=None,
        radius_m=80.0,
    )

    recorded = paths.root() / document["source_mesh"]
    recorded_manifest = paths.root() / document["source_mesh_manifest"]
    assert recorded.name == f"inhouse_leaf_{crop_m}m.ply"
    assert recorded_manifest == paths.mesh_manifest(recorded)
    assert recorded != paths.site_mesh(site, crop_m)


ROW = {
    "site": "madrid_plazamayor",
    "panoramas": 10,
    "registered": 10,
    "residual_deg": {"median": 0.4, "max": 2.92},
    "position_sigma_m": {"median": 0.26, "max": 1.1},
    "poses_at_altitude_bound": 5,
    "poses_inside_the_geometry": 4,
    "poses_inside_and_passing_the_residual_gate": 1,
    "poses_admitted": 6,
    "semantics_backend": ["mask2former"],
    "sam3_material_axis": False,
    "panoramas_with_sam3_material_axis": 0,
    "fishnet": {"views": 0, "faces": 0, "surface_area_m2": 0.0, "layout": "none"},
    "semantic_coverage": None,
    "fishnet_panoramas": None,
    "fishnet_panoramas_admitted": None,
    "bindings": {"130m": None, "250m": {"stations": 6, "covered_fraction_by_area": 0.0512}},
    "materially_bound_run_possible": {"130m": False, "250m": True},
}

#: A site whose fishnet was cut per panorama, so each view can be traced back to
#: the pose behind it.
BOUND_FISHNET = {
    "semantic_coverage": {
        "mesh": "inhouse_leaf_130m.ply",
        "views": 24,
        "covered_fraction_by_face": 0.1131,
        "covered_fraction_by_area": 0.1865,
    },
    "fishnet_panoramas": ["pano_00_a", "pano_01_b", "pano_02_c"],
    "fishnet_panoramas_admitted": ["pano_00_a", "pano_02_c"],
}


def test_the_table_says_no_when_no_crop_radius_has_a_binding():
    row = ROW | {
        "bindings": {"130m": None, "250m": None},
        "materially_bound_run_possible": {"130m": False, "250m": False},
    }
    assert markdown([row], (130, 250)).strip().endswith("| no |")


def test_the_table_names_the_crop_radii_a_bound_run_is_possible_at():
    body = markdown([ROW], (130, 250)).strip().splitlines()[-1]
    assert body.endswith("| walk at 250 m |")
    assert "5.1% (6 stations)" in body


def test_a_fishnet_is_a_second_route_to_a_bound_run_and_is_named_as_one():
    # The walk binding and the fishnet binding are different evidence with
    # different failure modes, so the cell says which one is available.
    body = markdown([ROW | BOUND_FISHNET], (130, 250)).strip().splitlines()[-1]
    assert body.endswith("| walk at 250 m, semantic at 130m |")


def test_the_fishnet_column_says_how_much_of_it_rests_on_an_admitted_pose():
    body = markdown([ROW | BOUND_FISHNET], (250,))
    assert "18.6% (24 views) from 2 of 3 admitted poses" in body


def test_a_fishnet_cut_entirely_from_refused_poses_is_not_a_bound_run():
    # Times Square has 8 views covering 6.5 % of the area, cut from two cameras
    # the sky conflict test places inside the buildings they are looking at.
    row = ROW | BOUND_FISHNET | {"fishnet_panoramas_admitted": []}
    body = markdown([row], (130, 250)).strip().splitlines()[-1]
    assert "semantic" not in body
    assert "from 0 of 3 admitted poses" in body


def test_a_single_panorama_site_says_its_poses_are_unattributed():
    # Korenmarkt and Milan wrote their views with no panorama in the name, so
    # the table declines to guess which camera they came from.
    row = ROW | BOUND_FISHNET | {"fishnet_panoramas": None, "fishnet_panoramas_admitted": None}
    body = markdown([row], (130, 250)).strip().splitlines()[-1]
    assert "poses unattributed" in body
    assert body.endswith("| walk at 250 m, semantic at 130m |")


def test_a_fishnet_covering_nothing_is_not_a_route():
    coverage = BOUND_FISHNET["semantic_coverage"] | {"covered_fraction_by_area": 0.0}
    row = ROW | BOUND_FISHNET | {"semantic_coverage": coverage}
    assert markdown([row], (130, 250)).strip().endswith("| walk at 250 m |")


def test_a_binding_without_a_recorded_area_is_not_reported_as_zero():
    row = ROW | {"bindings": ROW["bindings"] | {"130m": {"stations": 8, "covered_fraction_by_area": None}}}
    assert "8 stations, area not recorded" in markdown([row], (130, 250))


def test_the_header_has_one_divider_per_column():
    header, divider, _ = markdown([ROW], (130, 250)).strip().splitlines()
    assert divider.count("---") == header.count("|") - 1


def test_splicing_replaces_the_previous_table_rather_than_appending():
    document = "before\n<!-- COVERAGE_TABLE -->\n\nold table\n\n<!-- END_COVERAGE_TABLE -->\nafter\n"
    spliced = splice(document, "new table")
    assert "old table" not in spliced
    assert "new table" in spliced
    assert spliced.startswith("before")
    assert spliced.endswith("after\n")


def test_splicing_a_document_without_the_marker_is_refused():
    with pytest.raises(SystemExit, match="COVERAGE_TABLE"):
        splice("nothing to write into\n", "new table")


def test_splicing_is_idempotent():
    document = "head\n<!-- COVERAGE_TABLE -->\n\nold\n\n<!-- END_COVERAGE_TABLE -->\ntail\n"
    once = splice(document, "table")
    assert splice(once, "table") == once


def test_the_fishnet_column_says_none_rather_than_zero_faces():
    assert "| none |" in markdown([ROW], (130,))


def test_the_material_axis_column_is_a_count_out_of_the_panoramas_acquired():
    row = ROW | {"panoramas": 13, "panoramas_with_sam3_material_axis": 11}
    assert "11 of 13" in markdown([row], (250,))


def test_a_site_with_no_panoramas_reads_none_rather_than_zero_of_zero():
    row = ROW | {"panoramas": 0, "panoramas_with_sam3_material_axis": 0}
    assert "0 of 0" not in markdown([row], (250,))


def test_every_numeric_column_survives_a_site_with_nothing_registered():
    row = ROW | {
        "panoramas": 0,
        "registered": 0,
        "residual_deg": {"median": None, "max": None},
        "position_sigma_m": {"median": None, "max": None},
    }
    body = markdown([row], (130, 250)).strip().splitlines()[-1]
    assert body.count("n/a") == 3
    assert not np.any([cell.strip() == "" for cell in body.split("|")[1:-1]])


def test_a_flat_fishnet_reports_its_face_count():
    row = ROW | {"fishnet": {"views": 4, "faces": 10534, "surface_area_m2": 900.0, "layout": "flat"}}
    assert "| 10534 |" in markdown([row], (250,))


def test_a_nested_fishnet_is_counted_and_marked_as_unreachable():
    entry = {"views": 8, "faces": 2048, "surface_area_m2": 400.0, "layout": "nested, unreachable by bind"}
    assert "| 2048 nested |" in markdown([ROW | {"fishnet": entry}], (250,))
