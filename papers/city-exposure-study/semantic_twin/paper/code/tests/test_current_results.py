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
        CLAIMS.ten_route_wbsar_route_quantiles,
        CLAIMS.ten_route_median_contrast_factor,
        CLAIMS.ten_route_component_dominance,
        CLAIMS.ten_route_pooled_median_wbsar_component_shares,
        CLAIMS.five_route_replica_convergence_48_to_64,
        CLAIMS.ten_route_replica_convergence_48_to_64,
        CLAIMS.controlled_depth1_validation,
        CLAIMS.paired_material_evidence_control,
        CLAIMS.five_route_ray_reached_evidence_coverage,
        CLAIMS.roofline_budget_sensitivity,
        CLAIMS.geometric_fixed_grid_diagnostic,
        CLAIMS.ten_route_production_results,
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


def test_ten_route_claim_uses_authenticated_report() -> None:
    result = CLAIMS.ten_route_production_results()
    assert result["routes"] == 10
    assert result["standpoints"] == 163
    assert result["replicas_per_route"] == 64
    assert result["seed_range_inclusive"] == [7, 70]
    assert result["point_replica_fields"] == 10_432
    assert result["primary_rays"] == 2_086_400_000
    assert result["q50_span_factor"] == 14.314818947320367
    assert result["final_48_to_64_route_quantile_change_max_db"] == {
        "q10": 0.004914586580220958,
        "q50": 0.00015714191667892853,
        "q90": 0.0000761602380400701,
    }


def test_promoted_campaign_contract_is_ten_route_and_64_seed() -> None:
    result = CLAIMS.current_campaign_contract()
    assert result["routes"] == 10
    assert result["standpoints"] == 163
    assert result["replicas_per_route"] == 64
    assert result["seed_range_inclusive"] == [7, 70]
    assert result["seeds"] == list(range(7, 71))
    assert result["point_replica_fields"] == 10_432
    assert result["primary_rays"] == 2_086_400_000


def test_ten_route_quantile_table_and_exact_median_contrast() -> None:
    quantiles = CLAIMS.ten_route_wbsar_route_quantiles()
    assert quantiles["standpoints"] == 163
    assert quantiles["cities"] == CLAIMS.EXPECTED_TEN_ROUTE_WBSAR_QUANTILES
    contrast = CLAIMS.ten_route_median_contrast_factor()
    assert contrast == {
        "factor": 14.314818947320367,
        "reported_factor": 14.31,
        "largest_route_median": "Mexico City",
        "largest_route_median_value": 0.12906056842948704,
        "smallest_route_median": "Milan",
        "smallest_route_median_value": 0.009015871517791447,
        "unit": "m^2 kg^-1 per unit rho_A P_EIRP",
        "scope": "contrast among ten selected routes, not a city ranking",
    }


def test_ten_route_component_dominance_and_pooled_medians() -> None:
    dominance = CLAIMS.ten_route_component_dominance()
    assert dominance["line_of_sight_points"] == 157
    assert dominance["shadowed_points"] == 6
    assert dominance["largest_component_counts"] == {
        "direct": 156,
        "all_specular": 1,
        "first_diffuse": 6,
    }
    assert dominance["specular_largest_locations"] == [{"city": "Brussels", "standpoint": 2}]
    pooled = CLAIMS.ten_route_pooled_median_wbsar_component_shares()
    assert pooled["standpoints"] == 163
    assert pooled["share_percent"] == {
        "direct": 78.05583488137367,
        "all_specular": 20.230565408540063,
        "first_diffuse": 0.49973569313391336,
    }
    assert pooled["reported_share_percent"] == {
        "direct": 78.056,
        "all_specular": 20.231,
        "first_diffuse": 0.500,
    }


def test_ten_route_48_to_64_convergence_table() -> None:
    result = CLAIMS.ten_route_replica_convergence_48_to_64()
    assert result["routes"] == 10
    assert result["replicas"] == [48, 64]
    assert result["seed_range_at_64_inclusive"] == [7, 70]
    assert result["route_quantile_abs_change_db"] == CLAIMS.EXPECTED_TEN_ROUTE_48_TO_64_QUANTILE_CHANGE_DB
    assert result["route_quantile_abs_change_db"]["Mexico City"] == {
        "q10": 0.0034408407908050015,
        "q50": 0.0000026480606425963504,
        "q90": 0.000034050079323794956,
    }
    assert result["route_quantile_abs_change_db"]["Tokyo Hachiko"] == {
        "q10": 0.004914586580220958,
        "q50": 0.00002240790221443757,
        "q90": 0.000020120923639985872,
    }
    assert result["maximum_route_quantile_abs_change_db"] == {
        "q10": 0.004914586580220958,
        "q50": 0.00015714191667892853,
        "q90": 0.0000761602380400701,
    }


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
    coverage = CLAIMS.five_route_ray_reached_evidence_coverage()
    assert coverage["scope"] == "five routes and 73 standpoints only"
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
    convergence = CLAIMS.five_route_replica_convergence_48_to_64()
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
