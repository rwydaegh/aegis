from __future__ import annotations

import pathlib

import download_inhouse_tiles as legacy_command
from semantic_twin.acquire import tiles as tile_acquisition
from semantic_twin.cli import tiles as tiles_cli


def test_tile_parser_preserves_the_historical_defaults() -> None:
    args = tiles_cli.arguments(["--lat", "51.055", "--lon", "3.722", "--radius-m", "100", "--out", "tiles"])

    assert vars(args) == {
        "lat": 51.055,
        "lon": 3.722,
        "radius_m": 100.0,
        "vertical_half_extent_m": tile_acquisition.DEFAULT_VERTICAL_HALF_EXTENT_M,
        "site_height_m": None,
        "geometric_error_cutoff_m": 0.0,
        "max_requests": tile_acquisition.DEFAULT_MAX_REQUESTS,
        "max_bytes": tile_acquisition.DEFAULT_MAX_BYTES,
        "out": pathlib.Path("tiles"),
    }


def test_tile_parser_keeps_the_short_option_aliases() -> None:
    args = tiles_cli.arguments(["--lat", "51", "--lon", "3", "--radius", "12", "--cutoff", "1.5", "--out", "tiles"])

    assert args.radius_m == 12.0
    assert args.geometric_error_cutoff_m == 1.5


def test_historical_command_reexports_the_new_cli_boundary() -> None:
    assert legacy_command.arguments is tiles_cli.arguments
    assert legacy_command.main is tiles_cli.main
    assert legacy_command.api_key is tiles_cli.api_key


def test_google_key_prefers_the_maps_name_and_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "fallback")
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    assert tile_acquisition.google_api_key() == "fallback"

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "preferred")
    assert tile_acquisition.google_api_key() == "preferred"


def test_cli_main_forwards_a_typed_config_without_network(monkeypatch, tmp_path, capsys) -> None:
    received: list[tile_acquisition.TilesAcquireConfig] = []

    def fake_acquire(config: tile_acquisition.TilesAcquireConfig) -> dict[str, object]:
        received.append(config)
        return {"tiles": [{"file": "tile_0000.glb"}], "reused_from_disk": 0, "requests": 1, "total_bytes": 1024}

    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "secret")
    monkeypatch.setattr(tiles_cli, "acquire_tiles", fake_acquire)
    out_dir = tmp_path / "tiles"

    assert (
        tiles_cli.main(
            [
                "--lat",
                "51.055",
                "--lon",
                "3.722",
                "--radius-m",
                "100",
                "--vertical-half-extent-m",
                "1200",
                "--site-height-m",
                "42",
                "--geometric-error-cutoff-m",
                "0.5",
                "--max-requests",
                "9",
                "--max-bytes",
                "10000",
                "--out",
                str(out_dir),
            ]
        )
        == 0
    )

    assert received == [
        tile_acquisition.TilesAcquireConfig(
            api_key="secret",
            lat=51.055,
            lon=3.722,
            radius_m=100.0,
            geometric_error_cutoff_m=0.5,
            out=out_dir,
            vertical_half_extent_m=1200.0,
            site_height_m=42.0,
            max_requests=9,
            max_bytes=10000,
        )
    ]
    assert "[done] 1 tiles, 0 kept from a previous run, 1 requests, 0.0 MB" in capsys.readouterr().out


def test_cli_main_reports_a_missing_key_without_constructing_a_downloader(monkeypatch, capsys) -> None:
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    result = tiles_cli.main(["--lat", "51", "--lon", "3", "--radius-m", "10", "--out", "tiles"])

    assert result == 2
    assert "Set GOOGLE_MAPS_API_KEY or GOOGLE_API_KEY" in capsys.readouterr().err


def test_acquire_tiles_resolves_the_key_and_constructs_the_downloader(monkeypatch, tmp_path) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    class FakeDownloader:
        def __init__(self, key: str, **kwargs: object) -> None:
            calls.append((key, kwargs))

        def run(self) -> dict[str, object]:
            return {"tiles": []}

    monkeypatch.setattr(tile_acquisition, "GoogleTilesDownloader", FakeDownloader)
    monkeypatch.setenv("GOOGLE_API_KEY", "fallback")
    config = tile_acquisition.TilesAcquireConfig(
        lat=51.0,
        lon=3.0,
        radius_m=10.0,
        geometric_error_cutoff_m=0.0,
        out=tmp_path,
    )

    assert tile_acquisition.acquire_tiles(config) == {"tiles": []}
    assert calls == [
        (
            "fallback",
            {
                "lat": 51.0,
                "lon": 3.0,
                "radius_m": 10.0,
                "geometric_error_cutoff_m": 0.0,
                "out_dir": tmp_path,
                "vertical_half_extent_m": tile_acquisition.DEFAULT_VERTICAL_HALF_EXTENT_M,
                "site_ellipsoid_height_m": None,
                "max_requests": tile_acquisition.DEFAULT_MAX_REQUESTS,
                "max_bytes": tile_acquisition.DEFAULT_MAX_BYTES,
            },
        )
    ]
