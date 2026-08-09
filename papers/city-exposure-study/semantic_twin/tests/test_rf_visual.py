from __future__ import annotations

import pathlib

import pytest
from PIL import Image

from semantic_twin.vision.rf_visual import render_hit_evidence


def test_render_hit_evidence_preserves_exact_pixel_and_adds_zoom(tmp_path: pathlib.Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "evidence.png"
    image = Image.new("RGB", (40, 30), (10, 20, 30))
    image.putpixel((20, 15), (101, 102, 103))
    image.save(source)

    render_hit_evidence(source, output, x=20, y=15, footprint_radius_px=3, zoom_radius_px=5)

    rendered = Image.open(output)
    assert rendered.size == (70, 60)
    assert rendered.getpixel((20, 45)) == (101, 102, 103)
    assert output.is_file()


def test_render_hit_evidence_rejects_out_of_bounds_hit(tmp_path: pathlib.Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (8, 8)).save(source)

    with pytest.raises(ValueError, match="outside"):
        render_hit_evidence(source, tmp_path / "out.png", x=8, y=3)
