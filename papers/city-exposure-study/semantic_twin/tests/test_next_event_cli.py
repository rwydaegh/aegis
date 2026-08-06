from __future__ import annotations

from semantic_twin.cli import next_event
from semantic_twin.exposure.next_event_study import NextEventStudyConfig


def test_defaults_match_the_historical_next_event_command() -> None:
    args = next_event.arguments([])
    assert vars(args) == {
        "sites": ["korenmarkt", "brussels_grandplace"],
        "crop_m": 250,
        "rays": 200_000,
        "builders": 128,
        "held_out": 16,
        "azimuths": 1440,
        "elevations": 600,
        "cell_m": 1.0,
        "dims": 3,
        "site_lift_m": 0.5,
        "connections": 1,
        "frequency_hz": 15.0e9,
        "max_bounces": 3,
        "walk_radius_m": 90.0,
        "head_height_m": 1.5,
        "walk": "route",
        "walk_path": "links",
        "walk_stride_m": 6.0,
        "drop_clutter": False,
        "seed": 7,
        "variant": "llvm_ad_rgb",
        "tag": "next_event",
    }


def test_cli_dispatches_a_typed_config(monkeypatch) -> None:
    calls: list[NextEventStudyConfig] = []
    monkeypatch.setattr(next_event, "run_next_event_study", calls.append)

    status = next_event.main(
        [
            "--sites",
            "one",
            "two",
            "--crop-m",
            "90",
            "--rays",
            "10",
            "--builders",
            "4",
            "--held-out",
            "3",
            "--azimuths",
            "20",
            "--elevations",
            "10",
            "--cell-m",
            "2",
            "--dims",
            "2",
            "--site-lift-m",
            "1.25",
            "--connections",
            "5",
            "--frequency-hz",
            "2e9",
            "--max-bounces",
            "2",
            "--walk-radius-m",
            "30",
            "--head-height-m",
            "1.7",
            "--walk",
            "grid",
            "--walk-path",
            "closest",
            "--walk-stride-m",
            "2.5",
            "--drop-clutter",
            "--seed",
            "19",
            "--variant",
            "scalar_rgb",
            "--tag",
            "trial",
        ]
    )

    assert status == 0
    assert calls == [
        NextEventStudyConfig(
            sites=("one", "two"),
            crop_m=90,
            rays=10,
            builders=4,
            held_out=3,
            azimuths=20,
            elevations=10,
            cell_m=2.0,
            dims=2,
            site_lift_m=1.25,
            connections=5,
            frequency_hz=2.0e9,
            max_bounces=2,
            walk_radius_m=30.0,
            head_height_m=1.7,
            walk="grid",
            walk_path="closest",
            walk_stride_m=2.5,
            drop_clutter=True,
            seed=19,
            variant="scalar_rgb",
            tag="trial",
        )
    ]


def test_compatibility_facade_forwards_its_historical_hook(monkeypatch) -> None:
    import run_next_event

    calls: list[NextEventStudyConfig] = []
    monkeypatch.setattr(run_next_event, "run_next_event_study", calls.append)
    assert run_next_event.main(["--sites", "one"]) == 0
    assert calls and calls[0].sites == ("one",)
