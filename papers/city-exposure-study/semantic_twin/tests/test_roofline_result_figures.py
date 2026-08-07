"""Focused checks for the publication roofline result exports."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from semantic_twin.report.roofline_campaign_comparison import REPORT_SCHEMA_VERSION
from semantic_twin.report.roofline_result_figures import (
    CampaignPair,
    build_plot_data,
    write_publication_results,
)


def _report() -> dict:
    looks = {}
    for look in (4, 8, 12, 16):
        looks[str(look)] = {
            "linear_db_differences": {
                "raw_transfer": {
                    "direct": {"iid_linear": [1.0, 2.0], "rotated_fibonacci_linear": [1.0, 2.0]},
                    "total": {"iid_linear": [2.0, 4.0], "rotated_fibonacci_linear": [2.2, 4.4]},
                },
                "body_metrics": {
                    "total": {
                        metric: {
                            "iid_linear": values,
                            "rotated_fibonacci_linear": [value * 1.1 for value in values],
                        }
                        for metric, values in {
                            "peak_sab_w_m2": [0.1, 0.2],
                            "mean_sab_w_m2": [0.05, 0.1],
                            "absorbed_power_w": [0.02, 0.04],
                            "sar_wb_w_kg": [0.01, 0.02],
                        }.items()
                    }
                },
            },
            "across_seed_variance_ratios": {
                "total_raw_transfer": {"total": {"summary": {"q50": 0.7}}},
                "body_metrics": {
                    "total": {
                        metric: {"summary": {"q50": 0.8}}
                        for metric in ("mean_sab_w_m2", "absorbed_power_w", "sar_wb_w_kg")
                    }
                },
            },
        }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "looks": looks,
        "within_mode_convergence": {
            sampler: {
                "standard_error": {
                    str(look): {
                        "total_transfer": {
                            "replicas": look,
                            "p90_db_delta_approximation": 0.25 / look,
                            "maximum_db_delta_approximation": 0.5 / look,
                        }
                    }
                    for look in (4, 8, 12, 16)
                }
            }
            for sampler in ("iid", "rotated_fibonacci")
        },
    }


def test_build_plot_data_has_normalized_metadata_and_peak_sab_table() -> None:
    data = build_plot_data({"fixture": _report()})

    assert data["metadata"]["normalization"] == "per unit rho_A P_EIRP"
    assert "one-reflection" in data["metadata"]["caption"]
    assert data["cities"]["fixture"]["surplus_cdf"]["iid"]["x"] == pytest.approx([3.0103, 3.0103])
    peak = data["cities"]["fixture"]["table"]["iid"]["peak_sab_w_m2"]
    assert peak["unit"] == "1"
    assert peak["route_median"] == pytest.approx(0.15)
    json.dumps(data, allow_nan=False)


def test_write_publication_results_writes_all_artifacts_without_absolute_wording(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "semantic_twin.report.roofline_result_figures.compare_campaigns",
        lambda *_args, **_kwargs: _report(),
    )
    pair = CampaignPair("fixture", tmp_path / "iid", tmp_path / "fibonacci")
    artifacts = write_publication_results([pair], tmp_path / "paper" / "results")

    for path in (artifacts.pdf, artifacts.png, artifacts.json, artifacts.csv, artifacts.latex):
        assert path.is_file()
        assert path.stat().st_size > 0
    payload = json.loads(artifacts.json.read_text(encoding="utf-8"))
    assert payload["cities"]["fixture"]["table"]["iid"]["peak_sab_w_m2"]["unit"] == "1"
    assert "deployment-absolute" not in artifacts.latex.read_text(encoding="utf-8")
    assert "not deployment values" in artifacts.latex.read_text(encoding="utf-8")

    def assert_finite(value: object) -> None:
        if isinstance(value, float):
            assert not math.isnan(value)
        elif isinstance(value, dict):
            for nested in value.values():
                assert_finite(nested)
        elif isinstance(value, list):
            for nested in value:
                assert_finite(nested)

    assert_finite(payload)
