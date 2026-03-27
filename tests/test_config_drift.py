"""Verify DEFAULTS and default.json produce identical merged config."""

from pathlib import Path

from aegis.viewer.config import load_config


def _find_diffs(a, b, path=""):
    diffs = []
    all_keys = set(list(a.keys()) + list(b.keys())) if isinstance(a, dict) and isinstance(b, dict) else set()
    for key in sorted(all_keys):
        p = f"{path}.{key}" if path else key
        if key not in a:
            diffs.append(f"{p}: missing from DEFAULTS")
        elif key not in b:
            diffs.append(f"{p}: missing from JSON")
        elif isinstance(a[key], dict) and isinstance(b[key], dict):
            diffs.extend(_find_diffs(a[key], b[key], p))
        elif a[key] != b[key]:
            diffs.append(f"{p}: DEFAULTS={a[key]!r} vs merged={b[key]!r}")
    return diffs


def test_defaults_match_merged():
    """load_config(None) should equal load_config('configs/default.json')."""
    bare = load_config(None)
    merged = load_config(Path("configs/default.json"))
    diffs = _find_diffs(bare, merged)
    assert not diffs, "Config drift detected:\n" + "\n".join(diffs)
