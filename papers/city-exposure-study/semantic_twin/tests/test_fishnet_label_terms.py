from __future__ import annotations

from semantic_twin.scene.fishnet_build import NON_SURFACE_WORDS, TRANSIENT_WORDS, _contains_label_term


def test_transient_term_matches_a_vehicle_class() -> None:
    assert _contains_label_term("parked passenger car", TRANSIENT_WORDS)


def test_transient_term_does_not_match_carved_stone() -> None:
    assert not _contains_label_term("pale carved stone decorative window lintel", TRANSIENT_WORDS)


def test_non_surface_phrase_matches_as_a_phrase() -> None:
    assert _contains_label_term("ornate street light fixture", NON_SURFACE_WORDS)
