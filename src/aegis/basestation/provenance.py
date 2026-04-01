"""Per-field provenance tracking and confidence scoring for base station data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldSource:
    """Provenance of a single field value on a BaseStation."""

    origin: str  # e.g. "gov:brussels", "est:tech+band", "missing"
    confidence: float  # 0.0-1.0, field-level only


# Confidence by source type
CONFIDENCE_SCORES: dict[str, float] = {
    "gov_direct": 1.0,
    "gov_report": 0.8,
    "crowdsourced": 0.5,
    "est_same_dataset": 0.3,
    "est_reference": 0.2,
    "missing": 0.0,
}

# Dosimetric impact weights, keyed by BaseStation field name
DOSIMETRIC_WEIGHTS: dict[str, int] = {
    "eirp_dbm": 5,
    "azimuth_deg": 4,
    "height_m": 3,
    "freq_mhz": 3,
    "gain_dbi": 2,
    "electrical_tilt_deg": 1,
    "mechanical_tilt_deg": 1,
    "horizontal_beamwidth_deg": 1,
    "vertical_beamwidth_deg": 1,
}

# DataFrame column name -> BaseStation field name
COLUMN_TO_FIELD: dict[str, str] = {
    "Power": "eirp_dbm",
    "CenterHeight": "height_m",
    "Frequency": "freq_mhz",
    "Azimuth": "azimuth_deg",
    "Electrical_Tilt": "electrical_tilt_deg",
    "Mechanical_Tilt": "mechanical_tilt_deg",
    "Gain": "gain_dbi",
    "Horizontal_Beamwidth": "horizontal_beamwidth_deg",
    "Vertical_Beamwidth": "vertical_beamwidth_deg",
    "FrequencyBand": "frequency_band",
}

FIELD_TO_COLUMN: dict[str, str] = {v: k for k, v in COLUMN_TO_FIELD.items()}


def aggregate_confidence(
    provenance: tuple[tuple[str, FieldSource], ...],
) -> float:
    """Compute weighted aggregate confidence from per-field provenance."""
    if not provenance:
        return 0.0
    total_weight = 0
    weighted_sum = 0.0
    for field_name, source in provenance:
        w = DOSIMETRIC_WEIGHTS.get(field_name, 0)
        if w > 0:
            weighted_sum += w * source.confidence
            total_weight += w
    return weighted_sum / total_weight if total_weight > 0 else 0.0
