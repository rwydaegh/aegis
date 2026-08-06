"""The per site census of what a panorama route can be built from.

Built against a repository laid out on a temporary path rather than against the
shipped one, so the test says what the reader is entitled to conclude from a
given set of files rather than restating today's eleven sites.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from semantic_twin.report.panorama_routes import build_report, link_spacing_m, on_disk, site_row, table, write_report
from semantic_twin.walk.links import link_graph_from_screening


def lay_out_site(
    root: pathlib.Path,
    site: str,
    *,
    panoramas: list[tuple[str, float, float]],
    admitted: list[str],
    links: dict[str, list[str]],
) -> None:
    """One site's panorama directories, screening row and admitted station report."""
    base = root / "data" / "panoramas" / site
    for name, east, north in panoramas:
        folder = base / name
        (folder / "alignment").mkdir(parents=True, exist_ok=True)
        (folder / "metadata.json").write_text(json.dumps({"panoId": name, "date": "2024-07"}))
        (folder / "alignment" / "pose_aligned.json").write_text(json.dumps({"position_enu_m": [east, north, 2.5]}))

    screening = root / "outputs" / "city_screening"
    screening.mkdir(parents=True, exist_ok=True)
    rows = []
    if (screening / "screening.json").exists():
        rows = json.loads((screening / "screening.json").read_text())["rows"]
    rows.append(
        {
            "key": site,
            "panoramas": [
                {"pano_id": name, "east_m": east, "north_m": north, "links": links.get(name, [])}
                for name, east, north in panoramas
            ],
        }
    )
    (screening / "screening.json").write_text(json.dumps({"rows": rows}))

    report = root / "outputs" / "site_semantics" / site
    report.mkdir(parents=True, exist_ok=True)
    (report / "walk_semantic_250m.json").write_text(
        json.dumps(
            {
                "stations_admitted": [
                    {
                        "station": name,
                        "folder": str(base / name),
                        "position_enu_m": [east, north, 2.5],
                        "residual_deg": 1.0,
                    }
                    for name, east, north in panoramas
                    if name in admitted
                ]
            }
        )
    )


@pytest.fixture
def one_street(tmp_path: pathlib.Path) -> pathlib.Path:
    lay_out_site(
        tmp_path,
        "somewhere",
        panoramas=[
            ("pano_a", 0.0, 0.0),
            ("pano_b", 20.0, 0.0),
            ("pano_c", 40.0, 0.0),
            ("pano_d", 300.0, 0.0),
        ],
        admitted=["pano_a", "pano_b", "pano_c", "pano_d"],
        links={"pano_a": ["pano_b"], "pano_b": ["pano_c"]},
    )
    return tmp_path


def test_the_census_reports_the_chain_and_the_fragment_it_left_behind(one_street: pathlib.Path):
    row = site_row("somewhere", one_street)
    assert row["panoramas_on_disk"] == 4
    assert row["registered"] == 4
    assert row["admitted"] == 4
    assert row["fragments"] == [3, 1]
    assert row["chain_stations"] == 3
    assert row["chain_road_length_m"] == pytest.approx(40.0)
    assert row["road_leg_median_m"] == pytest.approx(20.0)
    assert row["end_to_end_m"] == pytest.approx(40.0)
    assert row["order"] == ["pano_a", "pano_b", "pano_c"]


def test_a_site_with_no_admitted_station_report_says_so_rather_than_reporting_zero_quietly(
    tmp_path: pathlib.Path,
):
    (tmp_path / "outputs" / "city_screening").mkdir(parents=True)
    (tmp_path / "outputs" / "city_screening" / "screening.json").write_text(json.dumps({"rows": []}))
    row = site_row("nowhere", tmp_path)
    assert row["admitted"] == 0
    assert "build_site_semantics.py" in row["note"]


def test_counting_what_is_on_disk_separates_registered_from_present(tmp_path: pathlib.Path):
    base = tmp_path / "data" / "panoramas" / "somewhere"
    (base / "pano_00" / "alignment").mkdir(parents=True)
    (base / "pano_00" / "alignment" / "pose_aligned.json").write_text("{}")
    (base / "pano_01").mkdir(parents=True)
    assert on_disk("somewhere", tmp_path) == (2, 1)


def test_counting_uses_the_registry_for_companion_walks(tmp_path: pathlib.Path):
    station = tmp_path / "data" / "panoramas" / "korenmarkt" / "alignment"
    station.mkdir(parents=True)
    (station / "pose_aligned.json").write_text("{}")
    walk = tmp_path / "data" / "panoramas" / "korenmarkt_walk" / "walk_00" / "alignment"
    walk.mkdir(parents=True)
    (walk / "pose_aligned.json").write_text("{}")
    reconstruction = tmp_path / "data" / "panoramas" / "korenmarkt_mapillary" / "view_00" / "alignment"
    reconstruction.mkdir(parents=True)
    (reconstruction / "pose_aligned.json").write_text("{}")

    assert on_disk("korenmarkt", tmp_path) == (2, 2)


def test_link_spacing_is_the_median_over_links_and_not_over_pairs():
    row = {
        "key": "somewhere",
        "panoramas": [
            {"pano_id": "a", "east_m": 0.0, "north_m": 0.0, "links": ["b"]},
            {"pano_id": "b", "east_m": 4.0, "north_m": 0.0, "links": ["c"]},
            {"pano_id": "c", "east_m": 100.0, "north_m": 0.0, "links": []},
        ],
    }
    assert link_spacing_m(link_graph_from_screening(row)) == pytest.approx(50.0)


def test_the_table_holds_a_line_per_site_and_a_header(one_street: pathlib.Path):
    rendered = table([site_row("somewhere", one_street)])
    lines = rendered.splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("| site |")
    assert "somewhere" in lines[2]


def test_report_builder_and_writer_preserve_both_output_contracts(one_street: pathlib.Path, tmp_path: pathlib.Path):
    rows, rendered = build_report(["somewhere"], one_street)
    output = tmp_path / "report"

    write_report(rows, rendered, output)

    json_text = (output / "panorama_routes.json").read_text()
    assert not json_text.endswith("\n")
    assert json.loads(json_text) == rows
    assert (output / "panorama_routes.md").read_text() == rendered + "\n"
