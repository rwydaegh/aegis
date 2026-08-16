"""Focused tests for the dependency-free manuscript claims helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "claims" / "current_results.py"
SPEC = importlib.util.spec_from_file_location("paper_current_results_claims", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
CLAIMS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLAIMS)


def test_linear_quantile_matches_known_even_and_odd_cases() -> None:
    assert CLAIMS._quantile([0.0, 1.0, 2.0, 3.0], 0.5) == 1.5
    assert CLAIMS._quantile([3.0, 1.0, 2.0], 0.5) == 2.0
    assert CLAIMS._quantile(list(range(11)), 0.1) == 1.0


def test_standard_library_npy_reader_recovers_current_raw_shape() -> None:
    root = CLAIMS._campaign_directory("Korenmarkt")
    shard = root / "checkpoint" / "replicas" / "seed_0000000007.npz"
    shape, values = CLAIMS._read_npy_f64(shard, "raw_transfer.npy")
    assert shape == (10, 4)
    assert len(values) == 40


def test_all_claim_functions_pass_against_authenticated_outputs() -> None:
    functions = (
        CLAIMS.current_campaign_contract,
        CLAIMS.five_city_wbsar_route_quantiles,
        CLAIMS.route_median_contrast_factor,
        CLAIMS.six_shadowed_standpoints,
        CLAIMS.raw_component_closure,
        CLAIMS.pooled_median_wbsar_component_shares,
        CLAIMS.directional_component_representation,
        CLAIMS.replica_convergence_12_to_16,
        CLAIMS.replica_convergence_48_to_64,
        CLAIMS.controlled_depth1_validation,
        CLAIMS.paired_material_evidence_control,
        CLAIMS.ray_reached_evidence_coverage,
        CLAIMS.roofline_budget_sensitivity,
        CLAIMS.geometric_fixed_grid_diagnostic,
    )
    for function in functions:
        assert function()


def test_geometric_fixed_grid_claim_uses_authenticated_report() -> None:
    result = CLAIMS.geometric_fixed_grid_diagnostic()
    assert result["contract"]["site_count"] == 10
    assert {name: round(value, 2) for name, value in result["quantile_span_factors"].items()} == {
        "q10": 2.02,
        "q50": 2.01,
        "q90": 2.23,
    }
    assert max(result["eight_to_sixteen_seed_max_abs_db"].values()) < 0.004
    assert max(result["thirty_two_to_sixty_four_point_max_abs_db"].values()) > 1.3


def test_budget_sensitivity_claim_passes_against_authenticated_report() -> None:
    result = CLAIMS.roofline_budget_sensitivity()
    assert result["production_budget"] == {"rays": 200_000, "cells": 4096}
    assert result["migration_recommended"] is False
    assert result["ray_25000_estimator_wall_time_ratio_range"] == {
        "minimum": 0.9912406567927025,
        "maximum": 1.0638558906935487,
    }
    assert result["baseline_specular_seconds_range"] == {
        "minimum": 8.058428761999494,
        "maximum": 23.785232650004218,
    }
    assert result["baseline_stochastic_trace_seconds_range"] == {
        "minimum": 1.1504173969979092,
        "maximum": 2.3965218109888156,
    }
    assert result["minimum_ray_reduced_q90_variance_time_ratio"] == 3.1598358725295483


def test_si_table_claims_return_every_published_cell() -> None:
    coverage = CLAIMS.ray_reached_evidence_coverage()
    assert coverage["table_rows"] == {
        "order_1_specular": {
            "panorama_informed": 0.806433729576005,
            "no_panorama_evidence": 0.08774141679005237,
            "host_incompatible": 0.10530373486292556,
            "other_fallback": 0.0005211187710170229,
        },
        "first_diffuse": {
            "panorama_informed": 0.13336718410343135,
            "no_panorama_evidence": 0.44345147385166056,
            "host_incompatible": 0.42313964955266,
            "other_fallback": 0.00004169249224817807,
        },
        "combined_non_direct": {
            "panorama_informed": 0.7590277699014926,
            "no_panorama_evidence": 0.11279507119363207,
            "host_incompatible": 0.12768980746784794,
            "other_fallback": 0.0004873514370273951,
        },
    }
    convergence = CLAIMS.replica_convergence_48_to_64()
    assert convergence["lower_tail_status"]["Korenmarkt"] == {
        "q10_change_db": 0.00007229028053766959,
        "shadow_point_max_change_db": None,
        "q10_bootstrap_95_width_db": 0.00022232758404101718,
    }
    assert convergence["lower_tail_status"]["Prague"] == {
        "q10_change_db": 0.00002027887149130285,
        "shadow_point_max_change_db": None,
        "q10_bootstrap_95_width_db": 0.00021814219482941877,
    }
    assert convergence["lower_tail_status"]["Madrid"] == {
        "q10_change_db": 0.000006147006725693227,
        "shadow_point_max_change_db": None,
        "q10_bootstrap_95_width_db": 0.00037805244663012116,
    }
    assert convergence["lower_tail_status"]["Mexico"] == {
        "q10_change_db": 0.0034408407908050015,
        "shadow_point_max_change_db": 0.012484950417289281,
        "q10_bootstrap_95_width_db": 0.3638279391681467,
    }
    assert convergence["lower_tail_status"]["Tokyo"] == {
        "q10_change_db": 0.004914586580220958,
        "shadow_point_max_change_db": 0.010443295223947286,
        "q10_bootstrap_95_width_db": 0.05379368852716219,
    }
