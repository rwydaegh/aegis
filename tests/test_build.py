"""Smoke tests for the build CLI."""

import subprocess
import sys


def test_build_cli_help():
    """Verify the build CLI is importable and has expected subcommands."""
    result = subprocess.run(
        [sys.executable, "-m", "aegis.basestation.build", "--help"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "extract" in result.stdout
    assert "merge" in result.stdout
    assert "validate" in result.stdout
    assert "report" in result.stdout


def test_extract_mastedatabasen_function_exists():
    """Verify _extract_mastedatabasen is callable."""
    from aegis.basestation.build import _extract_mastedatabasen

    assert callable(_extract_mastedatabasen)


def test_extract_opencellid_function_exists():
    """Verify _extract_opencellid is callable."""
    from aegis.basestation.build import _extract_opencellid

    assert callable(_extract_opencellid)


def test_australia_adapter_importable():
    """Verify Australia adapter can be imported."""
    from basestationLib.Countries.Australia.basestations import BaseStations

    bs = BaseStations(bounding_box=[150.9, 151.4, -34.0, -33.7])
    assert hasattr(bs, "extract_antennas")


def test_germany_adapter_importable():
    """Verify Germany adapter can be imported."""
    from basestationLib.Countries.Germany.basestations import BaseStations

    bs = BaseStations(bounding_box=[13.38, 13.42, 52.50, 52.52])
    assert hasattr(bs, "extract_antennas")


def test_regions_yaml_has_new_regions():
    """Verify Netherlands and Austria are configured in regions.yaml."""
    import yaml

    with open("data/basestations/regions.yaml") as f:
        cfg = yaml.safe_load(f)
    regions = cfg.get("regions", {})
    assert "netherlands" in regions
    assert "austria" in regions
    for name in ["netherlands", "austria"]:
        sources = regions[name].get("sources", [])
        assert any(s.get("type") == "basestationlib" for s in sources), f"{name} missing basestationlib source"
