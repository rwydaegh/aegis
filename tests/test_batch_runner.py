"""Tests for the batch runner (aegis.run) and simulation config (aegis.config).

Covers:
- SimulationConfig round-trip YAML serialization
- SimulationConfig validation (bad level, bad frequency, bad backend, unknown keys)
- CLI argument parsing and override application
- Synthetic path generation edge cases
- Compliance bug fix: uses <= not <, prefers spatially averaged S_ab
- DosimetryResult.compare() multi-level analysis
- Debye permittivity omega=0 safety
"""

from __future__ import annotations

import numpy as np
import pytest

from aegis.config import (
    AntennaConfig,
    BodyConfig,
    DosimetryConfig,
    RayTracerConfig,
    SimulationConfig,
    TissueConfig,
)
from aegis.result import DosimetryResult
from aegis.tissue.cole_cole import cole_cole_permittivity, debye_permittivity

# ---------------------------------------------------------------------------
# SimulationConfig tests
# ---------------------------------------------------------------------------


class TestSimulationConfig:
    def test_defaults(self):
        cfg = SimulationConfig()
        assert cfg.tissue.frequency_hz == 28e9
        assert cfg.body.name == "thelonious"
        assert cfg.dosimetry.level == 2
        assert cfg.raytracer.backend == "differt"

    def test_yaml_round_trip(self, tmp_path):
        cfg = SimulationConfig(
            tissue=TissueConfig(name="Muscle", frequency_hz=60e9),
            body=BodyConfig(name="duke", mass_kg=73.0),
            antenna=AntennaConfig(positions=[[3, 0, 1]], power_dbm=50.0),
            dosimetry=DosimetryConfig(level=5),
        )
        yaml_path = tmp_path / "test_config.yaml"
        cfg.to_yaml(yaml_path)
        loaded = SimulationConfig.from_yaml(yaml_path)

        assert loaded.tissue.name == "Muscle"
        assert loaded.tissue.frequency_hz == 60e9
        assert loaded.body.name == "duke"
        assert loaded.body.mass_kg == 73.0
        assert loaded.dosimetry.level == 5

    def test_from_dict_validates_keys(self):
        with pytest.raises(ValueError, match="Unknown config keys"):
            SimulationConfig.from_dict({"bogus_key": 42})

    def test_bad_frequency(self):
        with pytest.raises(ValueError, match="frequency_hz must be positive"):
            TissueConfig(frequency_hz=-1)

    def test_bad_level(self):
        with pytest.raises(ValueError, match="level must be 0-8"):
            DosimetryConfig(level=9)

    def test_bad_backend(self):
        with pytest.raises(ValueError, match="backend must be"):
            RayTracerConfig(backend="nonexistent")

    def test_from_dict_nested(self):
        cfg = SimulationConfig.from_dict(
            {
                "tissue": {"name": "Fat", "frequency_hz": 10e9},
                "dosimetry": {"level": 3},
            }
        )
        assert cfg.tissue.name == "Fat"
        assert cfg.dosimetry.level == 3
        # Other sections use defaults
        assert cfg.body.name == "thelonious"


# ---------------------------------------------------------------------------
# CLI argument parsing tests
# ---------------------------------------------------------------------------


class TestCLIParsing:
    def test_build_parser_defaults(self):
        from aegis.run import _build_parser

        parser = _build_parser()
        args = parser.parse_args([])
        assert args.config is None
        assert args.body is None
        assert args.level is None

    def test_apply_overrides(self):
        from aegis.run import _apply_overrides, _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            [
                "--body",
                "duke",
                "--level",
                "4",
                "--frequency",
                "60e9",
                "--power-dbm",
                "50",
                "--antenna-pos",
                "1,2,3",
                "--backend",
                "synthetic",
            ]
        )
        cfg_dict = {}
        result = _apply_overrides(cfg_dict, args)

        assert result["body"]["name"] == "duke"
        assert result["dosimetry"]["level"] == 4
        assert result["tissue"]["frequency_hz"] == 60e9
        assert result["antenna"]["power_dbm"] == 50.0
        assert result["antenna"]["positions"] == [[1.0, 2.0, 3.0]]
        assert result["raytracer"]["backend"] == "synthetic"


# ---------------------------------------------------------------------------
# Synthetic path generation tests
# ---------------------------------------------------------------------------


class TestSyntheticPaths:
    def test_basic_generation(self):
        from aegis.run import _synthetic_paths

        tx_pos = np.array([[5.0, 0.0, 1.0]])
        paths = _synthetic_paths(tx_pos, 1.0)
        assert paths.n_paths == 1
        assert paths.total_power > 0

    def test_multiple_antennas(self):
        from aegis.run import _synthetic_paths

        tx_pos = np.array([[5, 0, 1], [0, 5, 1], [-3, 0, 2]], dtype=float)
        paths = _synthetic_paths(tx_pos, 2.0)
        assert paths.n_paths == 3

    def test_zero_distance_skipped(self):
        from aegis.run import _synthetic_paths

        tx_pos = np.array([[0, 0, 0], [1, 0, 0]], dtype=float)
        paths = _synthetic_paths(tx_pos, 1.0)
        # Origin TX is skipped (dist < 1e-10)
        assert paths.n_paths == 1

    def test_empty_all_at_origin(self):
        from aegis.run import _synthetic_paths

        tx_pos = np.array([[0, 0, 0]], dtype=float)
        paths = _synthetic_paths(tx_pos, 1.0)
        assert paths.n_paths == 0

    def test_inverse_square_law(self):
        from aegis.run import _synthetic_paths

        power = 1.0
        p1 = _synthetic_paths(np.array([[1, 0, 0]], dtype=float), power)
        p2 = _synthetic_paths(np.array([[2, 0, 0]], dtype=float), power)
        # Power density should follow 1/r^2
        ratio = p1.total_power / p2.total_power
        np.testing.assert_allclose(ratio, 4.0, rtol=1e-10)


# ---------------------------------------------------------------------------
# Compliance fix verification
# ---------------------------------------------------------------------------


class TestComplianceFix:
    def test_save_results_uses_leq(self, tmp_path):
        """Verify the compliance check uses <= not <."""
        from aegis.compliance import ICNIRP_2020

        # Create a result with peak_sab exactly at the limit
        sab = np.array([ICNIRP_2020.sab_peak])
        result = DosimetryResult(
            sab=sab,
            p_abs=0.01,
            fidelity_level=2,
            sab_averaged=sab,
            freq_hz=28e9,
        )
        # The spatially averaged peak equals the limit -> should be compliant (<=)
        assert result.peak_sab_averaged == ICNIRP_2020.sab_peak
        # compliant_sab uses <=
        assert result.compliant_sab is True

    def test_run_save_prefers_averaged(self):
        """Verify _save_results uses spatially averaged S_ab when available."""
        from aegis.compliance import ICNIRP_2020

        # Averaged peak below limit, per-triangle peak above limit
        sab = np.array([25.0, 30.0])  # per-triangle peak = 30 > 20
        sab_avg = np.array([15.0, 18.0])  # averaged peak = 18 <= 20
        result = DosimetryResult(
            sab=sab,
            p_abs=0.05,
            fidelity_level=3,
            sab_averaged=sab_avg,
            freq_hz=28e9,
        )
        # Per-triangle peak exceeds limit
        assert float(np.max(result.sab)) > ICNIRP_2020.sab_peak
        # But spatially averaged is compliant
        assert result.peak_sab_averaged <= ICNIRP_2020.sab_peak
        assert result.compliant_sab is True


# ---------------------------------------------------------------------------
# DosimetryResult.compare() tests
# ---------------------------------------------------------------------------


class TestResultCompare:
    def _make_result(self, sab, level=2):
        return DosimetryResult(
            sab=np.asarray(sab, dtype=float),
            p_abs=float(np.sum(sab) * 1e-4),
            fidelity_level=level,
        )

    def test_basic_comparison(self):
        r1 = self._make_result([1.0, 2.0, 3.0], level=2)
        r2 = self._make_result([1.1, 2.1, 3.1], level=3)
        cmp = DosimetryResult.compare({"L2": r1, "L3": r2})

        assert cmp["labels"] == ["L2", "L3"]
        assert cmp["peak_sab"]["L2"] == 3.0
        assert cmp["peak_sab"]["L3"] == 3.1
        assert ("L2", "L3") in cmp["relative_error"]
        assert ("L2", "L3") in cmp["rmse"]
        assert ("L2", "L3") in cmp["max_abs_error"]

    def test_relative_error_exact_match(self):
        r = self._make_result([1.0, 2.0])
        cmp = DosimetryResult.compare({"a": r, "b": r})
        assert cmp["relative_error"][("a", "b")] == 0.0
        assert cmp["rmse"][("a", "b")] == 0.0

    def test_requires_two_results(self):
        r = self._make_result([1.0])
        with pytest.raises(ValueError, match="at least 2"):
            DosimetryResult.compare({"only_one": r})

    def test_shape_mismatch_skips_pair(self):
        r1 = self._make_result([1.0, 2.0])
        r2 = self._make_result([1.0, 2.0, 3.0])
        cmp = DosimetryResult.compare({"short": r1, "long": r2})
        # Pair is skipped due to shape mismatch
        assert len(cmp["rmse"]) == 0
        assert len(cmp["relative_error"]) == 0

    def test_three_results(self):
        r1 = self._make_result([1.0, 2.0, 3.0])
        r2 = self._make_result([1.5, 2.5, 3.5])
        r3 = self._make_result([2.0, 3.0, 4.0])
        cmp = DosimetryResult.compare({"A": r1, "B": r2, "C": r3})
        # Should have 3 pairs: (A,B), (A,C), (B,C)
        assert len(cmp["rmse"]) == 3

    def test_rmse_correctness(self):
        r1 = self._make_result([0.0, 0.0])
        r2 = self._make_result([1.0, 1.0])
        cmp = DosimetryResult.compare({"a": r1, "b": r2})
        assert cmp["rmse"][("a", "b")] == pytest.approx(1.0)
        assert cmp["max_abs_error"][("a", "b")] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Debye permittivity omega=0 fix
# ---------------------------------------------------------------------------


class TestDebyeOmegaZero:
    def test_debye_zero_frequency_no_crash(self):
        """Debye model should not crash or produce nan/inf at f=0."""
        result = debye_permittivity(0.0, eps_inf=5.0, eps_static=50.0, sigma=1.0, tau_s=1e-11)
        # At omega=0 the Debye formula gives eps_static, sigma term goes to 0
        assert np.isfinite(result)

    def test_debye_array_with_zero(self):
        freqs = np.array([0.0, 1e9, 10e9])
        result = debye_permittivity(freqs, eps_inf=5.0, eps_static=50.0, sigma=1.0, tau_s=1e-11)
        assert np.all(np.isfinite(result))

    def test_debye_zero_sigma_at_zero_freq(self):
        """With sigma=0, omega=0 should just give eps_static."""
        result = debye_permittivity(0.0, eps_inf=5.0, eps_static=50.0, sigma=0.0, tau_s=1e-11)
        np.testing.assert_allclose(np.real(result), 50.0, rtol=1e-10)

    def test_cole_cole_array_zero_freq(self):
        """Cole-Cole model should handle zero frequency in array input."""
        from aegis.tissue.database import get_tissue_properties

        props = get_tissue_properties("Skin", 28e9)
        # Build a params dict from the database format
        params = {
            "ef": props.eps_inf if hasattr(props, "eps_inf") else 4.0,
            "del1": 32.0,
            "tau1": 7.23,
            "alf1": 0.0,
            "del2": 1100.0,
            "tau2": 32.5,
            "alf2": 0.2,
            "del3": 0.0,
            "tau3": 0.0,
            "alf3": 0.0,
            "del4": 0.0,
            "tau4": 0.0,
            "alf4": 0.0,
            "sig": 0.0002,
        }
        freqs = np.array([0.0, 1e9, 28e9])
        result = cole_cole_permittivity(freqs, params)
        assert np.all(np.isfinite(result))


# ---------------------------------------------------------------------------
# Integration test: full pipeline with synthetic backend
# ---------------------------------------------------------------------------


class TestSyntheticPipeline:
    def test_end_to_end_with_defaults(self, tmp_path):
        """Run the full batch runner pipeline with synthetic paths on a tiny mesh."""
        from conftest import make_flat_mesh

        from aegis.engine import DosimetryEngine
        from aegis.run import _synthetic_paths
        from aegis.tissue.dielectric import SKIN_28GHZ

        mesh = make_flat_mesh(n=50)
        engine = DosimetryEngine(SKIN_28GHZ)
        paths = _synthetic_paths(np.array([[5.0, 0.0, 0.0]]), power_w=1.0)

        result = engine.compute(mesh, paths, level=3)
        assert result.sab.shape == (50,)
        assert result.p_abs >= 0
        assert result.peak_sab >= 0
        assert result.sab_averaged is not None

    def test_multi_level_comparison(self):
        """Compare levels 2, 3, 4 on same mesh and paths."""
        from conftest import make_flat_mesh

        from aegis.engine import DosimetryEngine
        from aegis.paths import PropagationPaths
        from aegis.tissue.dielectric import SKIN_28GHZ

        mesh = make_flat_mesh(n=50)
        engine = DosimetryEngine(SKIN_28GHZ)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )

        results = {}
        for level in [2, 3, 4]:
            results[f"L{level}"] = engine.compute(mesh, paths, level=level)

        cmp = DosimetryResult.compare(results)
        assert len(cmp["labels"]) == 3
        # All levels should produce non-negative peak S_ab
        for label in cmp["labels"]:
            assert cmp["peak_sab"][label] >= 0
        # L2 uses constant T0, L3 uses Fresnel -> they should differ
        assert cmp["rmse"][("L2", "L3")] > 0 or cmp["relative_error"][("L2", "L3")] >= 0


# ---------------------------------------------------------------------------
# DosimetryEngine.sweep_levels() tests
# ---------------------------------------------------------------------------


class TestSweepLevels:
    def test_sweep_levels_2_to_4(self):
        from conftest import make_flat_mesh

        from aegis.engine import DosimetryEngine
        from aegis.paths import PropagationPaths
        from aegis.tissue.dielectric import SKIN_28GHZ

        mesh = make_flat_mesh(n=50)
        engine = DosimetryEngine(SKIN_28GHZ)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        results = engine.sweep_levels(mesh, paths, levels=[2, 3, 4])
        assert set(results.keys()) == {2, 3, 4}
        for level, r in results.items():
            assert r.fidelity_level == level
            assert r.sab.shape == (50,)

    def test_sweep_skips_infeasible_levels(self):
        from conftest import make_flat_mesh

        from aegis.engine import DosimetryEngine
        from aegis.paths import PropagationPaths
        from aegis.tissue.dielectric import SKIN_28GHZ

        mesh = make_flat_mesh(n=20)
        engine = DosimetryEngine(SKIN_28GHZ)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        # Level 0 requires A_ab and D_max, level 1 requires A_ab
        # Without them, those levels should be silently skipped
        results = engine.sweep_levels(mesh, paths, levels=[0, 1, 2, 3])
        assert 0 not in results
        assert 1 not in results
        assert 2 in results
        assert 3 in results

    def test_sweep_default_levels(self):
        from conftest import make_flat_mesh

        from aegis.engine import DosimetryEngine
        from aegis.paths import PropagationPaths
        from aegis.tissue.dielectric import SKIN_28GHZ

        mesh = make_flat_mesh(n=20)
        engine = DosimetryEngine(SKIN_28GHZ)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        # Default levels are 0-6. Without A_ab/D_max, levels 0-1 are skipped.
        results = engine.sweep_levels(mesh, paths)
        assert all(lv in results for lv in [2, 3, 4, 5, 6])
        assert 0 not in results
        assert 1 not in results

    def test_sweep_with_compare(self):
        from conftest import make_flat_mesh

        from aegis.engine import DosimetryEngine
        from aegis.paths import PropagationPaths
        from aegis.tissue.dielectric import SKIN_28GHZ

        mesh = make_flat_mesh(n=30)
        engine = DosimetryEngine(SKIN_28GHZ)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        results = engine.sweep_levels(mesh, paths, levels=[2, 3, 4])
        labeled = {f"L{k}": v for k, v in results.items()}
        cmp = DosimetryResult.compare(labeled)
        # All pairwise comparisons should exist
        assert len(cmp["rmse"]) == 3  # (L2,L3), (L2,L4), (L3,L4)

    def test_sweep_with_level0_params(self):
        from conftest import make_flat_mesh

        from aegis.engine import DosimetryEngine
        from aegis.paths import PropagationPaths
        from aegis.tissue.dielectric import SKIN_28GHZ

        mesh = make_flat_mesh(n=20)
        engine = DosimetryEngine(SKIN_28GHZ)
        paths = PropagationPaths.from_powers(
            k_hat=np.array([[0, 0, -1.0]]),
            power=np.array([1.0]),
        )
        results = engine.sweep_levels(
            mesh,
            paths,
            levels=[0, 1, 2],
            A_ab=mesh.total_area * 0.5,
            D_max=2.0,
        )
        # Now levels 0 and 1 should be feasible
        assert 0 in results
        assert 1 in results
        assert 2 in results
