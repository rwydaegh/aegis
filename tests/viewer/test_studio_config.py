"""Tests for the Coherent Exposure Studio data-layer config."""

from __future__ import annotations

from pathlib import Path

from aegis.viewer.routes.studio import _config


def test_studio_paths_override_is_honoured(monkeypatch, tmp_path):
    monkeypatch.setenv("AEGIS_STUDIO_PATHS", str(tmp_path))
    # The override must win even when AEGIS_DATA_DIR is also set.
    monkeypatch.setenv("AEGIS_DATA_DIR", str(tmp_path / "other"))
    assert _config.studio_data_dir() == tmp_path


def test_data_dir_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("AEGIS_STUDIO_PATHS", raising=False)
    monkeypatch.setenv("AEGIS_DATA_DIR", str(tmp_path))
    assert _config.studio_data_dir() == tmp_path / "studio"


def test_available_packs_missing_dir_returns_empty(monkeypatch, tmp_path):
    missing = tmp_path / "does_not_exist"
    monkeypatch.setenv("AEGIS_STUDIO_PATHS", str(missing))
    packs = _config.available_packs()
    assert packs == {"rays": [], "phantom": [], "bodymaps": [], "ensemble": [], "qop": [], "channel": []}


def test_available_packs_lists_stems(monkeypatch, tmp_path):
    monkeypatch.setenv("AEGIS_STUDIO_PATHS", str(tmp_path))
    (tmp_path / "rays").mkdir()
    (tmp_path / "rays" / "bs16_los_seed0.npz").write_bytes(b"")
    (tmp_path / "bodymaps").mkdir()
    (tmp_path / "bodymaps" / "los_bs16_floor_28.npz").write_bytes(b"")
    (tmp_path / "qop").mkdir()
    (tmp_path / "qop" / "los_bs16_10.npz").write_bytes(b"")
    packs = _config.available_packs()
    assert packs["rays"] == ["bs16_los_seed0"]
    assert packs["bodymaps"] == ["los_bs16_floor_28"]
    assert packs["qop"] == ["los_bs16_10"]
    assert packs["phantom"] == []


def test_register_adds_studio_routes():
    # register() wires the studio endpoints onto the Flask app.
    import threading

    from flask import Flask

    from aegis.viewer.routes import studio

    app = Flask(__name__)
    studio.register(app, {}, threading.Lock())
    rules = {r.rule for r in app.url_map.iter_rules()}
    assert "/api/studio/manifest" in rules
    assert "/api/studio/slice" in rules
    assert "/api/studio/bodymap" in rules


def test_paper_fork_paths_dir_type():
    result = _config.paper_fork_paths_dir()
    assert result is None or isinstance(result, Path)
