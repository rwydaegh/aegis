"""Base-station fidelity tier + JSON summary helpers."""

from __future__ import annotations

_PROVENANCE_FIELDS = [
    "Power",
    "Frequency",
    "Azimuth",
    "CenterHeight",
    "Gain",
    "Electrical_Tilt",
    "Mechanical_Tilt",
    "Horizontal_Beamwidth",
    "Vertical_Beamwidth",
    "FrequencyBand",
]

_COLUMN_TO_FIELD = {
    "Power": "eirp_dbm",
    "Frequency": "freq_mhz",
    "Azimuth": "azimuth_deg",
    "CenterHeight": "height_m",
    "Gain": "gain_dbi",
    "Electrical_Tilt": "electrical_tilt_deg",
    "Mechanical_Tilt": "mechanical_tilt_deg",
    "Horizontal_Beamwidth": "horizontal_beamwidth_deg",
    "Vertical_Beamwidth": "vertical_beamwidth_deg",
    "FrequencyBand": "frequency_band",
}


def _compute_fidelity_tier(prov_origins: dict[str, str], pattern_source: str) -> str:
    """Compute fidelity readiness tier from provenance origin strings."""

    def is_confident(field: str) -> bool:
        src = prov_origins.get(field, "missing")
        return src != "missing" and not src.startswith("est:")

    def is_available(field: str) -> bool:
        src = prov_origins.get(field, "missing")
        return src != "missing"

    if (
        is_confident("Power")
        and is_confident("Frequency")
        and is_confident("Azimuth")
        and is_confident("CenterHeight")
        and is_confident("Gain")
        and is_available("Electrical_Tilt")
        and is_available("Mechanical_Tilt")
        and is_available("Horizontal_Beamwidth")
        and is_available("Vertical_Beamwidth")
    ):
        if pattern_source and pattern_source not in ("", "synthetic:gaussian"):
            return "full"
        return "spatial"

    if is_confident("Power") and is_confident("Frequency") and is_confident("Azimuth") and is_confident("CenterHeight"):
        return "geometric"

    if is_available("Power") and is_available("Frequency"):
        return "bound"

    return "location_only"


def _build_provenance_origins(bs) -> dict[str, str]:
    """Extract provenance-origin strings keyed by column name for one base station."""
    prov_dict = bs.provenance_dict
    prov_origins: dict[str, str] = {}
    for col_name in _PROVENANCE_FIELDS:
        field_name = _COLUMN_TO_FIELD.get(col_name, col_name)
        fs = prov_dict.get(field_name)
        prov_origins[col_name] = fs.origin if fs else "missing"
    prov_origins["Pattern"] = bs.pattern_source or ""
    return prov_origins


def _flatten_exposure_fields(classification: dict) -> None:
    """Pull dataclass fields from exposure_config into the classification dict."""
    exp = classification.pop("exposure_config")
    classification["duplex_mode"] = exp.duplex_mode
    classification["tdd_dl_ratio"] = exp.tdd_dl_ratio
    classification["power_reduction_factor"] = exp.power_reduction_factor
    classification["traffic_load_factor"] = exp.traffic_load_factor
    classification.pop("beam_config", None)


def _bs_summary(bs) -> dict:
    """Serialize a BaseStation to a JSON-safe dict with classification."""
    from aegis.basestation.classify import classify_basestation
    from aegis.basestation.provenance import aggregate_confidence

    classification = classify_basestation(
        gain_dbi=bs.gain_dbi,
        technology=bs.technology,
        freq_mhz=bs.freq_mhz,
        h_bw=bs.horizontal_beamwidth_deg or 0,
        v_bw=bs.vertical_beamwidth_deg or 0,
    )
    _flatten_exposure_fields(classification)

    prov_origins = _build_provenance_origins(bs)
    fidelity_tier = _compute_fidelity_tier(prov_origins, bs.pattern_source or "")

    prov_dict = bs.provenance_dict
    return {
        "site_code": bs.site_code,
        "antenna_label": bs.antenna_label,
        "operator": bs.operator,
        "technology": bs.technology,
        "latitude": bs.latitude,
        "longitude": bs.longitude,
        "height_m": bs.height_m,
        "eirp_dbm": bs.eirp_dbm,
        "gain_dbi": bs.gain_dbi,
        "freq_mhz": bs.freq_mhz,
        "azimuth_deg": bs.azimuth_deg,
        "total_tilt_deg": bs.total_tilt_deg,
        "has_pattern": bs.pattern is not None,
        "horizontal_beamwidth_deg": bs.horizontal_beamwidth_deg,
        "vertical_beamwidth_deg": bs.vertical_beamwidth_deg,
        "frequency_band": bs.frequency_band,
        "pattern_source": bs.pattern_source,
        "confidence": aggregate_confidence(bs.provenance),
        "fidelity_tier": fidelity_tier,
        "provenance": {k: {"origin": v.origin, "confidence": v.confidence} for k, v in prov_dict.items()},
        "provenance_sources": prov_origins,
        **classification,
    }
