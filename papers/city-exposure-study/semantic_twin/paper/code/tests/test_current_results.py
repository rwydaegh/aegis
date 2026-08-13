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
        CLAIMS.controlled_depth1_validation,
        CLAIMS.paired_material_evidence_control,
    )
    for function in functions:
        assert function()
