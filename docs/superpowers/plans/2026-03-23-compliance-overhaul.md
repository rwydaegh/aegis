# Compliance overhaul implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the ICNIRP 2020 compliance module with correct limits, add S_inc pipeline, precomputed averaging matrix, frequency parameter, five heatmap modes, compliance panel, peak indicator, and report export.

**Architecture:** The compliance module becomes a self-contained data model (ExposureScenario, ICNIRPLimits, ComplianceResult). A precomputed sparse averaging matrix G replaces the iterative KD-tree loop. The engine always computes spatially-averaged S_ab, S_inc, and a ComplianceResult. The viewer exposes all data through updated API responses. The React frontend adds frequency input, scenario toggle, display mode selector, and a structured compliance panel.

**Tech Stack:** Python 3.12 (NumPy, SciPy sparse, dataclasses), React + TypeScript (Zustand stores, Three.js/R3F), Flask REST API

**Spec:** `docs/superpowers/specs/2026-03-23-compliance-overhaul-design.md`

---

## Phase 1: Core compliance backend

### Task 1: Rewrite compliance module with correct ICNIRP 2020 limits

**Files:**
- Rewrite: `src/aegis/compliance/__init__.py`
- Rewrite: `tests/test_compliance.py`
- Modify: `src/aegis/result.py` (update imports to new compliance API)
- Modify: `src/aegis/viewer/routes/compute.py` (update imports)
- Modify: `src/aegis/viz/dashboard.py` (update imports)

**IMPORTANT:** This task must also update all files that import from the old
compliance module (`ICNIRP_2020`, `is_compliant_sab`, etc.) to prevent broken
imports. Every commit on master must be a clean, passing state.

- [ ] **Step 1: Write failing tests for the new compliance data model**

```python
# tests/test_compliance.py
"""Tests for ICNIRP 2020 compliance module."""
from __future__ import annotations

import math
import pytest
from aegis.compliance import (
    ExposureScenario,
    icnirp_limits,
    ComplianceCheck,
    evaluate_compliance,
    margin_db,
)


class TestICNIRPLimits:
    """Verify all ICNIRP 2020 Table 2, 5, 6 values."""

    def test_general_public_sab_4cm2(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28e9)
        assert lim.sab_4cm2 == 20.0

    def test_occupational_sab_4cm2(self) -> None:
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, 28e9)
        assert lim.sab_4cm2 == 100.0

    def test_general_public_sar_wb(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28e9)
        assert lim.sar_wb == 0.08

    def test_occupational_sar_wb(self) -> None:
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, 28e9)
        assert lim.sar_wb == 0.4

    def test_general_public_sinc_whole_body(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28e9)
        assert lim.sinc_whole_body == 10.0

    def test_occupational_sinc_whole_body(self) -> None:
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, 28e9)
        assert lim.sinc_whole_body == 50.0

    def test_sinc_local_frequency_dependent_28ghz(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28e9)
        expected = 55.0 / (28.0 ** 0.177)
        assert lim.sinc_local == pytest.approx(expected, rel=1e-6)

    def test_sinc_local_frequency_dependent_60ghz(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 60e9)
        expected = 55.0 / (60.0 ** 0.177)
        assert lim.sinc_local == pytest.approx(expected, rel=1e-6)

    def test_sinc_local_occupational_28ghz(self) -> None:
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, 28e9)
        expected = 275.0 / (28.0 ** 0.177)
        assert lim.sinc_local == pytest.approx(expected, rel=1e-6)

    def test_sab_1cm2_none_below_30ghz(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 28e9)
        assert lim.sab_1cm2 is None

    def test_sab_1cm2_general_public_above_30ghz(self) -> None:
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 60e9)
        assert lim.sab_1cm2 == 40.0  # 2x the 4cm2 limit

    def test_sab_1cm2_occupational_above_30ghz(self) -> None:
        lim = icnirp_limits(ExposureScenario.OCCUPATIONAL, 60e9)
        assert lim.sab_1cm2 == 200.0

    def test_frequency_below_6ghz_raises(self) -> None:
        with pytest.raises(ValueError, match="above 6 GHz"):
            icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 3.5e9)

    def test_frequency_above_300ghz_raises(self) -> None:
        with pytest.raises(ValueError, match="above 6 GHz"):
            icnirp_limits(ExposureScenario.GENERAL_PUBLIC, 400e9)


class TestComplianceCheck:
    def test_pass_when_below_limit(self) -> None:
        c = ComplianceCheck(value=15.0, limit=20.0, unit="W/m^2", label="S_ab (4 cm²)")
        assert c.compliant is True

    def test_pass_when_at_limit(self) -> None:
        c = ComplianceCheck(value=20.0, limit=20.0, unit="W/m^2", label="S_ab (4 cm²)")
        assert c.compliant is True  # <= not <

    def test_fail_when_above_limit(self) -> None:
        c = ComplianceCheck(value=21.0, limit=20.0, unit="W/m^2", label="S_ab (4 cm²)")
        assert c.compliant is False

    def test_margin_db_positive_when_compliant(self) -> None:
        c = ComplianceCheck(value=10.0, limit=20.0, unit="W/m^2", label="test")
        assert c.margin_db == pytest.approx(10.0 * math.log10(2.0))

    def test_margin_db_negative_when_exceeding(self) -> None:
        c = ComplianceCheck(value=40.0, limit=20.0, unit="W/m^2", label="test")
        assert c.margin_db == pytest.approx(10.0 * math.log10(0.5))


class TestEvaluateCompliance:
    def test_overall_pass_all_below(self) -> None:
        result = evaluate_compliance(
            scenario=ExposureScenario.GENERAL_PUBLIC,
            freq_hz=28e9,
            peak_sab_4cm2=10.0,
            peak_sinc_local=20.0,
            sinc_whole_body=5.0,
            sar_wb=0.04,
        )
        assert result.overall_pass is True

    def test_overall_fail_sab_exceeds(self) -> None:
        result = evaluate_compliance(
            scenario=ExposureScenario.GENERAL_PUBLIC,
            freq_hz=28e9,
            peak_sab_4cm2=25.0,
            peak_sinc_local=20.0,
            sinc_whole_body=5.0,
        )
        assert result.overall_pass is False
        assert result.sab_4cm2.compliant is False

    def test_1cm2_included_above_30ghz(self) -> None:
        result = evaluate_compliance(
            scenario=ExposureScenario.GENERAL_PUBLIC,
            freq_hz=60e9,
            peak_sab_4cm2=10.0,
            peak_sab_1cm2=50.0,  # exceeds 40 limit
            peak_sinc_local=20.0,
            sinc_whole_body=5.0,
        )
        assert result.overall_pass is False
        assert result.sab_1cm2 is not None
        assert result.sab_1cm2.compliant is False

    def test_margin_db_is_tightest(self) -> None:
        result = evaluate_compliance(
            scenario=ExposureScenario.GENERAL_PUBLIC,
            freq_hz=28e9,
            peak_sab_4cm2=19.0,  # tightest: 10*log10(20/19) = 0.22 dB
            peak_sinc_local=10.0,
            sinc_whole_body=5.0,
            sar_wb=0.04,
        )
        expected = 10.0 * math.log10(20.0 / 19.0)
        assert result.margin_db == pytest.approx(expected, rel=1e-3)


class TestMarginDb:
    def test_positive_margin(self) -> None:
        assert margin_db(5.0, 20.0) == pytest.approx(10.0 * math.log10(4.0))

    def test_zero_margin(self) -> None:
        assert margin_db(20.0, 20.0) == pytest.approx(0.0)

    def test_negative_margin(self) -> None:
        assert margin_db(40.0, 20.0) == pytest.approx(10.0 * math.log10(0.5))

    def test_zero_value_raises(self) -> None:
        with pytest.raises(ValueError):
            margin_db(0.0, 20.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_compliance.py -v`
Expected: FAIL (imports not found)

- [ ] **Step 3: Implement the compliance module**

```python
# src/aegis/compliance/__init__.py
"""ICNIRP 2020 compliance limits for EMF exposure >6 GHz to 300 GHz.

Source: ICNIRP, "Guidelines for Limiting Exposure to Electromagnetic
Fields (100 kHz to 300 GHz)," Health Physics, vol. 118, no. 5, 2020.
See theory/ICNIRPrfgdl2020.pdf.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "ExposureScenario",
    "ICNIRPLimits",
    "ComplianceCheck",
    "ComplianceResult",
    "icnirp_limits",
    "evaluate_compliance",
    "margin_db",
]


class ExposureScenario(Enum):
    GENERAL_PUBLIC = "general_public"
    OCCUPATIONAL = "occupational"


@dataclass(frozen=True)
class ICNIRPLimits:
    """ICNIRP 2020 limits for a given scenario and frequency.

    All S_ab limits from Table 2 (basic restrictions, >= 6 min).
    All S_inc limits from Tables 5 and 6 (reference levels).
    """

    scenario: ExposureScenario
    freq_hz: float
    sab_4cm2: float
    sab_1cm2: float | None  # only >30 GHz
    sar_wb: float
    sinc_local: float  # Table 6, frequency-dependent
    sinc_whole_body: float  # Table 5


@dataclass(frozen=True)
class ComplianceCheck:
    """Single compliance check: value vs limit."""

    value: float
    limit: float
    unit: str
    label: str

    @property
    def compliant(self) -> bool:
        return self.value <= self.limit

    @property
    def margin_db(self) -> float:
        if self.value <= 0:
            raise ValueError("value must be positive for dB margin")
        return 10.0 * math.log10(self.limit / self.value)

    @property
    def ratio(self) -> float:
        return self.value / self.limit if self.limit > 0 else float("inf")


@dataclass(frozen=True)
class ComplianceResult:
    """Full compliance assessment."""

    scenario: ExposureScenario
    freq_hz: float
    sab_4cm2: ComplianceCheck
    sab_1cm2: ComplianceCheck | None
    sar_wb: ComplianceCheck | None
    sinc_local: ComplianceCheck
    sinc_whole_body: ComplianceCheck | None

    @property
    def overall_pass(self) -> bool:
        checks = [self.sab_4cm2, self.sinc_local]
        if self.sab_1cm2 is not None:
            checks.append(self.sab_1cm2)
        if self.sar_wb is not None:
            checks.append(self.sar_wb)
        if self.sinc_whole_body is not None:
            checks.append(self.sinc_whole_body)
        return all(c.compliant for c in checks)

    @property
    def margin_db(self) -> float:
        checks = [self.sab_4cm2, self.sinc_local]
        if self.sab_1cm2 is not None:
            checks.append(self.sab_1cm2)
        if self.sar_wb is not None:
            checks.append(self.sar_wb)
        if self.sinc_whole_body is not None:
            checks.append(self.sinc_whole_body)
        margins = []
        for c in checks:
            if c.value > 0:
                margins.append(c.margin_db)
        return min(margins) if margins else float("inf")

    @property
    def all_checks(self) -> list[ComplianceCheck]:
        checks = [self.sab_4cm2]
        if self.sab_1cm2 is not None:
            checks.append(self.sab_1cm2)
        if self.sar_wb is not None:
            checks.append(self.sar_wb)
        checks.append(self.sinc_local)
        if self.sinc_whole_body is not None:
            checks.append(self.sinc_whole_body)
        return checks


def icnirp_limits(scenario: ExposureScenario, freq_hz: float) -> ICNIRPLimits:
    """Compute ICNIRP 2020 limits for a given scenario and frequency.

    Supported range: >6 GHz to 300 GHz.
    """
    freq_ghz = freq_hz / 1e9
    if freq_ghz <= 6.0 or freq_ghz > 300.0:
        raise ValueError(
            f"Compliance module supports frequencies above 6 GHz and up to "
            f"300 GHz, got {freq_ghz:.1f} GHz"
        )

    if scenario == ExposureScenario.GENERAL_PUBLIC:
        sab_4cm2 = 20.0
        sar_wb = 0.08
        sinc_local = 55.0 / (freq_ghz ** 0.177)
        sinc_whole_body = 10.0
        sab_1cm2 = 2.0 * sab_4cm2 if freq_ghz > 30.0 else None
    else:
        sab_4cm2 = 100.0
        sar_wb = 0.4
        sinc_local = 275.0 / (freq_ghz ** 0.177)
        sinc_whole_body = 50.0
        sab_1cm2 = 2.0 * sab_4cm2 if freq_ghz > 30.0 else None

    return ICNIRPLimits(
        scenario=scenario,
        freq_hz=freq_hz,
        sab_4cm2=sab_4cm2,
        sab_1cm2=sab_1cm2,
        sar_wb=sar_wb,
        sinc_local=sinc_local,
        sinc_whole_body=sinc_whole_body,
    )


def evaluate_compliance(
    *,
    scenario: ExposureScenario,
    freq_hz: float,
    peak_sab_4cm2: float,
    peak_sinc_local: float,
    sinc_whole_body: float | None = None,
    sar_wb: float | None = None,
    peak_sab_1cm2: float | None = None,
    tx_power_dbm: float | None = None,
) -> ComplianceResult:
    """Evaluate full ICNIRP 2020 compliance."""
    lim = icnirp_limits(scenario, freq_hz)

    sab_4cm2_check = ComplianceCheck(
        value=peak_sab_4cm2, limit=lim.sab_4cm2,
        unit="W/m^2", label="S_ab (4 cm²)",
    )

    sab_1cm2_check = None
    if lim.sab_1cm2 is not None and peak_sab_1cm2 is not None:
        sab_1cm2_check = ComplianceCheck(
            value=peak_sab_1cm2, limit=lim.sab_1cm2,
            unit="W/m^2", label="S_ab (1 cm²)",
        )

    sar_check = None
    if sar_wb is not None:
        sar_check = ComplianceCheck(
            value=sar_wb, limit=lim.sar_wb,
            unit="W/kg", label="SAR_wb",
        )

    sinc_local_check = ComplianceCheck(
        value=peak_sinc_local, limit=lim.sinc_local,
        unit="W/m^2", label="S_inc (local)",
    )

    sinc_wb_check = None
    if sinc_whole_body is not None:
        sinc_wb_check = ComplianceCheck(
            value=sinc_whole_body, limit=lim.sinc_whole_body,
            unit="W/m^2", label="S_inc (whole-body)",
        )

    return ComplianceResult(
        scenario=scenario,
        freq_hz=freq_hz,
        sab_4cm2=sab_4cm2_check,
        sab_1cm2=sab_1cm2_check,
        sar_wb=sar_check,
        sinc_local=sinc_local_check,
        sinc_whole_body=sinc_wb_check,
    )


def margin_db(value: float, limit: float) -> float:
    """Compliance margin in dB: 10 * log10(limit / value)."""
    if value <= 0:
        raise ValueError("value must be positive")
    return float(10.0 * math.log10(limit / value))


def summary_text(
    compliance_result: ComplianceResult,
    tx_power_dbm: float | None = None,
) -> str:
    """Human-readable compliance summary."""
    lines = [
        f"ICNIRP 2020 compliance ({compliance_result.scenario.value})",
        f"Frequency: {compliance_result.freq_hz / 1e9:.1f} GHz",
        "",
    ]
    for c in compliance_result.all_checks:
        status = "PASS" if c.compliant else "FAIL"
        margin = f"{c.margin_db:+.1f} dB" if c.value > 0 else "n/a"
        lines.append(f"  {c.label}: {c.value:.4g} / {c.limit:.4g} {c.unit} [{status}] ({margin})")
    lines.append("")
    lines.append(f"Overall: {'PASS' if compliance_result.overall_pass else 'FAIL'}")
    if compliance_result.margin_db != float("inf"):
        lines.append(f"Margin: {compliance_result.margin_db:+.1f} dB")
    if tx_power_dbm is not None:
        max_p = tx_power_dbm + compliance_result.margin_db
        lines.append(f"Max compliant TX power: {max_p:.1f} dBm")
    return "\n".join(lines)


# Backward-compatible shim (used by result.py, viewer, dashboard).
# Preserves the old ICNIRPLimits interface (.sab_peak, .sar_wb,
# .averaging_area_cm2) so existing callers don't break.
# The sab_peak is now CORRECT at 20.0 (was 10.0).
# Remove once all callers migrate to the new API.
@dataclass(frozen=True)
class _LegacyLimits:
    sab_peak: float
    sar_wb: float
    averaging_area_cm2: float

ICNIRP_2020 = _LegacyLimits(sab_peak=20.0, sar_wb=0.08, averaging_area_cm2=4.0)


def is_compliant_sab(peak_sab_averaged: float) -> bool:
    return peak_sab_averaged <= ICNIRP_2020.sab_peak


def is_compliant_sar(sar_wb: float) -> bool:
    return sar_wb <= ICNIRP_2020.sar_wb
```

The backward-compat aliases (`ICNIRP_2020`, `is_compliant_sab`, `is_compliant_sar`)
keep existing imports working. They will be removed as callers migrate in later tasks.

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/test_compliance.py -v`
Expected: all PASS

- [ ] **Step 5: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/compliance/ tests/test_compliance.py
py -3.12 -m ruff format src/aegis/compliance/ tests/test_compliance.py
git add src/aegis/compliance/__init__.py tests/test_compliance.py
git commit -m "Rewrite compliance module with correct ICNIRP 2020 limits"
```

---

### Task 2: Precomputed averaging matrix G

**Files:**
- Modify: `src/aegis/geometry/averaging.py`
- Modify: `src/aegis/geometry/__init__.py`
- Create: `tests/test_averaging_matrix.py`

- [ ] **Step 1: Write failing tests for G matrix**

```python
# tests/test_averaging_matrix.py
"""Tests for precomputed spatial averaging matrix."""
from __future__ import annotations

import numpy as np
import pytest
from scipy import sparse

from aegis.geometry.averaging import precompute_averaging_matrix


def _make_flat_grid(n: int = 10, spacing: float = 0.005) -> tuple:
    """Create a flat grid of n x n triangles with given spacing (meters)."""
    centroids = []
    areas = []
    for i in range(n):
        for j in range(n):
            centroids.append([i * spacing, j * spacing, 0.0])
            areas.append(spacing ** 2)
    return np.array(centroids), np.array(areas)


class TestPrecomputeAveragingMatrix:
    def test_returns_sparse_csr(self) -> None:
        centroids, areas = _make_flat_grid(5)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        assert sparse.issparse(G)

    def test_shape_m_by_m(self) -> None:
        centroids, areas = _make_flat_grid(5)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        M = len(centroids)
        assert G.shape == (M, M)

    def test_row_stochastic(self) -> None:
        """Each row sums to 1 (area-weighted average)."""
        centroids, areas = _make_flat_grid(10)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        row_sums = np.array(G.sum(axis=1)).ravel()
        np.testing.assert_allclose(row_sums, 1.0, atol=1e-10)

    def test_uniform_field_unchanged(self) -> None:
        """Averaging a uniform field should return the same value everywhere."""
        centroids, areas = _make_flat_grid(10)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        sab = np.full(len(centroids), 5.0)
        sab_avg = G @ sab
        np.testing.assert_allclose(sab_avg, 5.0, atol=1e-10)

    def test_smooths_point_source(self) -> None:
        """A single hot triangle should be smoothed out."""
        centroids, areas = _make_flat_grid(10)
        sab = np.zeros(len(centroids))
        center = len(centroids) // 2
        sab[center] = 100.0
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        sab_avg = G @ sab
        assert sab_avg[center] < 100.0  # smoothed
        assert sab_avg[center] > 0.0    # not zero

    def test_1cm2_matrix_smaller_neighborhood(self) -> None:
        centroids, areas = _make_flat_grid(10)
        G4 = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        G1 = precompute_averaging_matrix(centroids, areas, target_area_m2=1e-4)
        # 1 cm^2 matrix should have fewer nonzeros per row (smaller neighborhood)
        assert G1.nnz <= G4.nnz

    def test_nonnegative_entries(self) -> None:
        centroids, areas = _make_flat_grid(10)
        G = precompute_averaging_matrix(centroids, areas, target_area_m2=4e-4)
        assert np.all(G.data >= 0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_averaging_matrix.py -v`
Expected: FAIL (import error)

- [ ] **Step 3: Implement precompute_averaging_matrix**

Add to `src/aegis/geometry/averaging.py` (keep existing `apply_spatial_averaging`):

```python
def precompute_averaging_matrix(
    centroids: np.ndarray,
    areas: np.ndarray,
    target_area_m2: float = 4e-4,
) -> sparse.csr_array:
    """Build sparse row-stochastic averaging matrix G.

    G[i, j] = area[j] / sum(area[neighbors_of_i]) for j in neighbors of i,
    where neighbors are accumulated by distance until reaching target_area_m2.

    Parameters
    ----------
    centroids : (M, 3) triangle centroids
    areas : (M,) triangle areas in m^2
    target_area_m2 : averaging area (default 4e-4 = 4 cm^2)

    Returns
    -------
    G : (M, M) sparse CSR matrix, row-stochastic
    """
    from scipy.spatial import cKDTree

    M = len(centroids)
    tree = cKDTree(centroids)
    r_est = np.sqrt(target_area_m2 / np.pi) * 2.5

    rows, cols, vals = [], [], []
    for i in range(M):
        dists, idxs = tree.query(centroids[i], k=min(200, M), distance_upper_bound=r_est)
        valid = np.isfinite(dists)
        idxs = idxs[valid]
        dists = dists[valid]

        order = np.argsort(dists)
        idxs = idxs[order]
        cum_area = np.cumsum(areas[idxs])
        cutoff = max(1, int(np.searchsorted(cum_area, target_area_m2) + 1))
        cutoff = min(cutoff, len(idxs))
        neighbor_idxs = idxs[:cutoff]
        neighbor_areas = areas[neighbor_idxs]
        weights = neighbor_areas / neighbor_areas.sum()

        for j, w in zip(neighbor_idxs, weights):
            rows.append(i)
            cols.append(j)
            vals.append(w)

    G = sparse.csr_array(
        (np.array(vals), (np.array(rows), np.array(cols))),
        shape=(M, M),
    )
    return G
```

Update `src/aegis/geometry/__init__.py` exports to include `precompute_averaging_matrix`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/test_averaging_matrix.py -v`
Expected: all PASS

- [ ] **Step 5: Lint and commit**

```bash
py -3.12 -m ruff check src/aegis/geometry/ tests/test_averaging_matrix.py
py -3.12 -m ruff format src/aegis/geometry/ tests/test_averaging_matrix.py
git add src/aegis/geometry/averaging.py src/aegis/geometry/__init__.py tests/test_averaging_matrix.py
git commit -m "Add precomputed sparse averaging matrix G"
```

---

### Task 3: Add S_inc field and new fields to DosimetryResult

**Files:**
- Modify: `src/aegis/result.py`
- Modify: `tests/test_engine.py` (add assertions for new fields)

- [ ] **Step 1: Write failing test for new result fields**

Add to a new test file or existing test:

```python
# tests/test_result_fields.py
"""Tests for DosimetryResult new fields."""
from __future__ import annotations

import numpy as np
import pytest
from aegis.result import DosimetryResult


def test_sinc_field_exists() -> None:
    r = DosimetryResult(
        sab=np.array([1.0, 2.0]),
        p_abs=0.1,
        fidelity_level=2,
        sinc=np.array([3.0, 4.0]),
    )
    np.testing.assert_array_equal(r.sinc, [3.0, 4.0])


def test_sinc_default_none() -> None:
    r = DosimetryResult(sab=np.array([1.0]), p_abs=0.1, fidelity_level=2)
    assert r.sinc is None


def test_sinc_averaged_field() -> None:
    r = DosimetryResult(
        sab=np.array([1.0]),
        p_abs=0.1,
        fidelity_level=2,
        sinc_averaged=np.array([2.0]),
    )
    np.testing.assert_array_equal(r.sinc_averaged, [2.0])


def test_sab_1cm2_averaged_field() -> None:
    r = DosimetryResult(
        sab=np.array([1.0]),
        p_abs=0.1,
        fidelity_level=2,
        sab_1cm2_averaged=np.array([1.5]),
    )
    np.testing.assert_array_equal(r.sab_1cm2_averaged, [1.5])


def test_freq_hz_field() -> None:
    r = DosimetryResult(
        sab=np.array([1.0]),
        p_abs=0.1,
        fidelity_level=2,
        freq_hz=28e9,
    )
    assert r.freq_hz == 28e9
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_result_fields.py -v`
Expected: FAIL (unexpected keyword arguments)

- [ ] **Step 3: Add new fields to DosimetryResult**

In `src/aegis/result.py`, add these fields to the dataclass (after existing optional fields):

```python
    sinc: np.ndarray | None = None
    sinc_averaged: np.ndarray | None = None
    sab_1cm2_averaged: np.ndarray | None = None
    freq_hz: float | None = None
```

Also fix the compliance properties to use `<=`:

```python
    @property
    def compliant_sab(self) -> bool | None:
        peak = self.peak_sab_averaged
        if peak is None:
            return None
        from aegis.compliance import icnirp_limits, ExposureScenario
        if self.freq_hz is None:
            return None
        lim = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, self.freq_hz)
        return peak <= lim.sab_4cm2
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/test_result_fields.py -v`
Expected: all PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: all PASS (existing tests should not break since new fields default to None)

- [ ] **Step 6: Commit**

```bash
git add src/aegis/result.py tests/test_result_fields.py
git commit -m "Add sinc, sinc_averaged, sab_1cm2_averaged, freq_hz to DosimetryResult"
```

---

### Task 4: S_inc computation in engine

**Files:**
- Modify: `src/aegis/engine.py`
- Create: `tests/test_sinc_pipeline.py`

- [ ] **Step 1: Write failing tests for S_inc pipeline**

```python
# tests/test_sinc_pipeline.py
"""Tests for S_inc computation pipeline."""
from __future__ import annotations

import numpy as np
import pytest
from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.geometry import BodyMesh
from aegis.tissue.dielectric import SKIN_28GHZ


@pytest.fixture
def simple_body() -> BodyMesh:
    """Two-triangle body facing +z."""
    vertices = np.array([
        [[0, 0, 0], [0.02, 0, 0], [0.01, 0.02, 0]],
        [[0.02, 0, 0], [0.04, 0, 0], [0.03, 0.02, 0]],
    ], dtype=float)
    normals = np.array([[0, 0, 1], [0, 0, 1]], dtype=float)
    centroids = vertices.mean(axis=1)
    areas = np.array([0.0002, 0.0002])
    return BodyMesh(vertices=vertices, normals=normals, centroids=centroids, areas=areas, name="test")


@pytest.fixture
def downward_paths() -> PropagationPaths:
    """Single path pointing downward (-z), hitting body facing +z."""
    return PropagationPaths.from_powers(
        k_hat=np.array([[0, 0, -1.0]]),
        power=np.array([10.0]),
    )


class TestSincComputation:
    def test_sinc_field_populated(self, simple_body, downward_paths) -> None:
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(simple_body, downward_paths, mode="spatial")
        assert result.sinc is not None
        assert result.sinc.shape == (2,)

    def test_sinc_no_fresnel_no_relu(self, simple_body, downward_paths) -> None:
        """S_inc should be larger than S_ab (no T0 < 1 and no cos projection)."""
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(simple_body, downward_paths, mode="spatial")
        # S_inc = sum of ray powers, S_ab = S_inc * T0 * cos(theta)
        # For normal incidence cos=1, so S_ab = S_inc * T0
        # Since T0 < 1, S_inc > S_ab
        assert np.all(result.sinc >= result.sab)

    def test_sinc_equals_sab_div_t0_normal_incidence(self, simple_body, downward_paths) -> None:
        """At normal incidence (cos=1), S_inc = S_ab / T0."""
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(
            simple_body, downward_paths, mode="spatial", fresnel=True,
        )
        T0 = SKIN_28GHZ.T0
        # For level with only fresnel, sab = sinc * T0 * cos(theta)
        # At normal incidence, cos = 1, so sinc = sab / T0
        expected_sinc = result.sab / T0
        np.testing.assert_allclose(result.sinc, expected_sinc, rtol=0.01)

    def test_freq_hz_on_result(self, simple_body, downward_paths) -> None:
        engine = DosimetryEngine(SKIN_28GHZ)
        result = engine.compute(simple_body, downward_paths, mode="spatial")
        assert result.freq_hz == 28e9
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `py -3.12 -m pytest tests/test_sinc_pipeline.py -v`
Expected: FAIL (sinc is None)

- [ ] **Step 3: Add S_inc computation to engine.compute()**

In `src/aegis/engine.py`, after computing `sab` and before building the result:

1. Compute `sinc` by running the same kernel but with T0=1.0 and all corrections
   disabled (no fresnel, no curvature, no diffraction). This gives the raw
   cosine-projected power. Then divide out the cosine to get pure S_inc.

Alternative (simpler): for incoherent modes, S_inc per triangle is the sum of
`paths.power` for all paths, broadcast to all triangles. Since the current kernels
apply per-path cosine projection, the simplest approach is to compute a separate
`sinc` by summing path powers without projection:

```python
# In engine.py, after sab computation:
sinc = self._compute_sinc(body, paths)

def _compute_sinc(self, body, paths):
    """Compute incident power density per triangle (no T0, no cosine)."""
    # For incoherent: sum all path powers (already in W/m^2)
    sinc = np.sum(paths.power) * np.ones(body.n_triangles) / body.n_triangles
    # TODO: for spatial kernel, accumulate per-triangle path contributions
    return sinc
```

The spatial kernel computes `sab = (T * g) @ power` where T is the Fresnel factor
(M,N), g is ReLU/GELU (M,N), and power is (N,). This broadcasts all N paths to
all M triangles. For S_inc, we want the incident power density without T and g:

```python
# S_inc: all paths contribute equally to all triangles (broadcast kernel)
sinc = np.full(body.n_triangles, float(np.sum(_to_numpy(paths.power))))
```

This is correct because the current kernel broadcasts all N paths to all M triangles
via matrix multiply `(M,N) @ (N,)`. S_inc is a free-space field quantity,
independent of surface orientation or tissue. The kernel assumes far-field plane
waves, so S_inc is spatially uniform. At normal incidence: sab = T0 * sinc,
confirming the relationship.

For the RT integration (DiffeRT/Sionna), rays are mapped to specific triangles.
S_inc would need per-triangle accumulation there, but that code path is separate
from the core kernel and out of scope for this plan.

2. Add `freq_hz` parameter to `compute()` signature:

```python
def compute(self, body, paths, ..., freq_hz: float | None = None, ...) -> DosimetryResult:
    # Use explicit freq_hz if provided, else fall back to tissue
    effective_freq_hz = freq_hz if freq_hz is not None else self.freq_hz
```

3. Always compute spatial averaging using cached G matrices:

```python
from aegis.geometry.averaging import precompute_averaging_matrix

# In __init__, initialize cache slots:
self._G_cache: dict[tuple, Any] = {}

# In compute(), after sab:
def _get_G(self, body, target_area_m2):
    key = (id(body), body.n_triangles, target_area_m2)
    if key not in self._G_cache:
        self._G_cache[key] = precompute_averaging_matrix(
            body.centroids, body.areas, target_area_m2,
        )
    return self._G_cache[key]

G_4cm2 = self._get_G(body, 4e-4)
sab_averaged = G_4cm2 @ sab
sinc_averaged = G_4cm2 @ sinc

sab_1cm2_averaged = None
if effective_freq_hz > 30e9:
    G_1cm2 = self._get_G(body, 1e-4)
    sab_1cm2_averaged = G_1cm2 @ sab
```

4. Pass all new fields to DosimetryResult:

```python
return DosimetryResult(
    sab=sab,
    p_abs=p_abs,
    fidelity_level=level,
    sab_averaged=sab_averaged,
    sar_wb=sar_wb,
    sinc=sinc,
    sinc_averaged=sinc_averaged,
    sab_1cm2_averaged=sab_1cm2_averaged,
    freq_hz=effective_freq_hz,
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `py -3.12 -m pytest tests/test_sinc_pipeline.py -v`
Expected: all PASS

- [ ] **Step 5: Run full test suite**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/aegis/engine.py tests/test_sinc_pipeline.py
git commit -m "Add S_inc pipeline and always-on spatial averaging in engine"
```

---

## Phase 2: Viewer backend

### Task 5: Update viewer compute to return new arrays and compliance

**Files:**
- Modify: `src/aegis/viewer/compute.py`
- Modify: `src/aegis/viewer/routes/compute.py`
- Modify: `src/aegis/viewer/config.py`

- [ ] **Step 1: Update config defaults**

In `src/aegis/viewer/config.py`, in the `DEFAULTS["dosimetry"]` dict:
- Remove `"compliance_threshold": 10.0`
- Add `"freq_hz": 28.0e+9`
- Add `"exposure_scenario": "general_public"`
- Add `"display_mode": "raw_sab"`

- [ ] **Step 2: Update compute_dosimetry to return new data**

In `src/aegis/viewer/compute.py`, modify `compute_dosimetry()`:
- Always pass `spatial_averaging=True` to engine (remove the conditional)
- Extract `freq_hz` from tissue or config
- Add `sab_averaged_bytes`, `sinc_bytes` to the return dict
- Add compliance result to the return dict

```python
# After engine.compute():
result_dict = {
    "sab_bytes": result.sab.astype(np.float32).tobytes(),
    "sab_averaged_bytes": result.sab_averaged.astype(np.float32).tobytes(),
    "sinc_bytes": result.sinc.astype(np.float32).tobytes() if result.sinc is not None else None,
    "p_abs": float(result.p_abs),
    "peak_sab": float(result.peak_sab),
    "peak_sab_averaged": float(result.peak_sab_averaged) if result.sab_averaged is not None else None,
    "freq_hz": float(result.freq_hz or tissue.freq_hz),
}
```

- [ ] **Step 3: Update _build_stats_response to use ComplianceResult**

In `src/aegis/viewer/routes/compute.py`:

```python
from aegis.compliance import evaluate_compliance, ExposureScenario

def _build_stats_response(result, body, tissue, level, extra=None, mode=None, corrections=None):
    scenario_str = extra.pop("scenario", "general_public") if extra else "general_public"
    scenario = ExposureScenario(scenario_str)
    freq_hz = result.freq_hz or tissue.freq_hz

    # Compute S_inc whole-body average
    sinc_wb = None
    if result.sinc is not None:
        sinc_wb = float(np.sum(result.sinc * body.areas) / np.sum(body.areas))

    compliance = evaluate_compliance(
        scenario=scenario,
        freq_hz=freq_hz,
        peak_sab_4cm2=float(np.max(result.sab_averaged)) if result.sab_averaged is not None else float(result.peak_sab),
        peak_sinc_local=float(np.max(result.sinc_averaged)) if result.sinc_averaged is not None else 0.0,
        sinc_whole_body=sinc_wb,
        sar_wb=result.sar_wb,
        peak_sab_1cm2=float(np.max(result.sab_1cm2_averaged)) if result.sab_1cm2_averaged is not None else None,
    )

    stats = {
        "p_abs": float(result.p_abs),
        "p_abs_mw": float(result.p_abs * 1e3),
        "peak_sab": float(result.peak_sab),
        "peak_sab_averaged": float(np.max(result.sab_averaged)) if result.sab_averaged is not None else None,
        "compliance": {
            "overall_pass": compliance.overall_pass,
            "margin_db": compliance.margin_db if compliance.margin_db != float("inf") else None,
            "scenario": scenario.value,
            "freq_hz": freq_hz,
            "checks": [
                {
                    "label": c.label,
                    "value": c.value,
                    "limit": c.limit,
                    "unit": c.unit,
                    "pass": c.compliant,
                    "ratio": c.ratio,
                }
                for c in compliance.all_checks
            ],
        },
        # Keep legacy field for backward compat
        "compliant": compliance.overall_pass,
        "n_illuminated": int(np.sum(result.sab > 0)),
        "n_triangles": body.n_triangles,
        "level": level if level is not None else 0,
        "T0": float(tissue.T0),
    }
    if mode is not None:
        stats["mode"] = mode
    if corrections:
        stats["corrections"] = corrections
    if extra:
        stats.update(extra)
    return stats
```

- [ ] **Step 4: Run full tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/aegis/viewer/compute.py src/aegis/viewer/routes/compute.py src/aegis/viewer/config.py
git commit -m "Update viewer to return compliance result and new arrays"
```

---

### Task 6: Compliance report endpoint

**Files:**
- Modify: `src/aegis/viewer/routes/compute.py`
- Modify: `src/aegis/viewer/server.py` (if route registration needed)

- [ ] **Step 1: Add /api/compliance/report endpoint**

```python
@bp.route("/api/compliance/report", methods=["GET"])
def compliance_report():
    """Return full compliance report JSON for the last computation."""
    # Pull the last result from the app state
    last = current_app.config.get("_last_compliance_result")
    if last is None:
        return jsonify({"error": "No computation result available"}), 404
    return jsonify(last)
```

Store the compliance result dict on `current_app.config["_last_compliance_result"]`
in `_build_stats_response`.

- [ ] **Step 2: Test manually or add integration test**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`

- [ ] **Step 3: Commit**

```bash
git add src/aegis/viewer/routes/compute.py
git commit -m "Add /api/compliance/report endpoint"
```

---

## Phase 3: Frontend

### Task 7: Update TypeScript types and stores

**Files:**
- Modify: `aegis-web/src/api/types.ts`
- Modify: `aegis-web/src/stores/simulation.ts`
- Modify: `aegis-web/src/stores/ui.ts`

- [ ] **Step 1: Update DosimetryStats type**

In `aegis-web/src/api/types.ts`:

```typescript
export interface ComplianceCheck {
  label: string
  value: number
  limit: number
  unit: string
  pass: boolean
  ratio: number
}

export interface ComplianceInfo {
  overall_pass: boolean
  margin_db: number | null
  scenario: 'general_public' | 'occupational'
  freq_hz: number
  checks: ComplianceCheck[]
}

export interface DosimetryStats {
  p_abs: number
  p_abs_mw: number
  peak_sab: number
  peak_sab_averaged: number | null
  compliance: ComplianceInfo
  compliant: boolean  // legacy
  n_illuminated: number
  n_triangles: number
  level: number
  mode?: string
  corrections?: string[]
  S_inc: number
  distance_m: number
  T0: number
  n_rt_paths?: number
  path_viz?: PathViz[]
}
```

- [ ] **Step 2: Update simulation store**

In `aegis-web/src/stores/simulation.ts`, add:

```typescript
  sabAveragedArray: Float32Array | null  // spatially averaged S_ab
  sincArray: Float32Array | null         // incident power density
  sincAveragedArray: Float32Array | null // spatially averaged S_inc
  freqGhz: number                       // operating frequency in GHz
```

Add setters and update the compute action to store the new arrays from the API
response (binary arraybuffers alongside sab_bytes).

- [ ] **Step 3: Update UI store**

In `aegis-web/src/stores/ui.ts`, add:

```typescript
  displayMode: 'raw_sab' | 'avg_sab' | 'sinc' | 'ratio_sab' | 'ratio_sinc'
  exposureScenario: 'general_public' | 'occupational'
```

With default values `'raw_sab'` and `'general_public'`.

- [ ] **Step 4: Build to check for type errors**

Run: `cd aegis-web && npm run build`
Expected: no type errors

- [ ] **Step 5: Commit**

```bash
git add aegis-web/src/api/types.ts aegis-web/src/stores/simulation.ts aegis-web/src/stores/ui.ts
git commit -m "Add compliance types, display modes, and frequency to frontend stores"
```

---

### Task 8: Frequency input and exposure scenario toggle

**Files:**
- Modify: `aegis-web/src/components/panels/ParametersPanel.tsx`

- [ ] **Step 1: Add frequency input**

Add a numeric input for frequency in GHz with preset buttons (3.5, 28, 39, 60):

```tsx
<label>Frequency (GHz)</label>
<div style={{ display: 'flex', gap: 4 }}>
  <input
    type="number"
    value={freqGhz}
    onChange={(e) => setFreqGhz(parseFloat(e.target.value))}
    min={6.1} max={300} step={0.1}
    style={{ width: 70 }}
  />
  {[3.5, 28, 39, 60].map((f) => (
    <button key={f} onClick={() => setFreqGhz(f)}
      className={freqGhz === f ? 'active' : ''}>
      {f}
    </button>
  ))}
</div>
```

Note: 3.5 GHz is below the 6 GHz compliance range. The compliance panel should
show "below supported range" for this frequency. The frequency input itself should
not restrict to >6 GHz since users may want to simulate at lower frequencies.

- [ ] **Step 2: Add exposure scenario toggle**

```tsx
<label>Exposure scenario</label>
<div className="btn-group">
  <button
    className={scenario === 'general_public' ? 'active' : ''}
    onClick={() => setScenario('general_public')}>
    General Public
  </button>
  <button
    className={scenario === 'occupational' ? 'active' : ''}
    onClick={() => setScenario('occupational')}>
    Occupational
  </button>
</div>
```

- [ ] **Step 3: Build and verify**

Run: `cd aegis-web && npm run build`
Expected: builds without errors

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/panels/ParametersPanel.tsx
git commit -m "Add frequency input and exposure scenario toggle to parameters panel"
```

---

### Task 9: Display mode selector

**Files:**
- Modify: `aegis-web/src/components/panels/ParametersPanel.tsx` (or a new ViewPanel)
- Modify: `aegis-web/src/components/scene/BodyMesh.tsx`

- [ ] **Step 1: Add display mode dropdown**

In the parameters panel or a separate view controls section:

```tsx
<label>Display</label>
<select value={displayMode} onChange={(e) => setDisplayMode(e.target.value)}>
  <option value="raw_sab">Raw S_ab</option>
  <option value="avg_sab">Averaged S_ab (4 cm²)</option>
  <option value="sinc">S_inc (incident)</option>
  <option value="ratio_sab">Compliance ratio (S_ab)</option>
  <option value="ratio_sinc">Compliance ratio (S_inc)</option>
</select>
```

- [ ] **Step 2: Update BodyMesh to use selected array**

In `aegis-web/src/components/scene/BodyMesh.tsx`, change the data source based on
`displayMode`:

```tsx
const displayMode = useUIStore(s => s.displayMode)
const sabArray = useSimulationStore(s => s.sabArray)
const sabAveragedArray = useSimulationStore(s => s.sabAveragedArray)
const sincArray = useSimulationStore(s => s.sincArray)
const compliance = useSimulationStore(s => s.stats?.compliance)

// Pick the right array based on display mode
let dataArray: Float32Array | null = null
let isRatioMode = false
let ratioLimit = 1.0

switch (displayMode) {
  case 'raw_sab': dataArray = sabArray; break
  case 'avg_sab': dataArray = sabAveragedArray; break
  case 'sinc': dataArray = sincArray; break
  case 'ratio_sab':
    dataArray = sabAveragedArray
    isRatioMode = true
    ratioLimit = compliance?.checks?.find(c => c.label === 'S_ab (4 cm²)')?.limit ?? 20.0
    break
  case 'ratio_sinc':
    dataArray = sincAveragedArray  // use spatially-averaged S_inc per Table 6
    isRatioMode = true
    ratioLimit = compliance?.checks?.find(c => c.label === 'S_inc (local)')?.limit ?? 10.0
    break
}
```

For ratio modes, divide each value by `ratioLimit` before passing to the colormap.
Use a fixed green-yellow-orange-red colormap with range [0, 2] instead of the
adaptive jet colormap.

- [ ] **Step 3: Build and verify**

Run: `cd aegis-web && npm run build`

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/panels/ParametersPanel.tsx aegis-web/src/components/scene/BodyMesh.tsx
git commit -m "Add five heatmap display modes with compliance ratio coloring"
```

---

### Task 10: Compliance panel in HUD

**Files:**
- Modify: `aegis-web/src/components/layout/HudOverlay.tsx`

- [ ] **Step 1: Replace single PASS/FAIL with compliance panel**

Create a `CompliancePanel` component:

```tsx
function CompliancePanel() {
  const stats = useSimulationStore(s => s.stats)
  const scenario = useUIStore(s => s.exposureScenario)
  const setScenario = useUIStore(s => s.setExposureScenario)

  if (!stats?.compliance) return null
  const { compliance } = stats

  return (
    <div className="compliance-panel">
      <div className="compliance-header">
        <span>COMPLIANCE (ICNIRP 2020)</span>
        <select value={scenario} onChange={e => setScenario(e.target.value)}>
          <option value="general_public">General Public</option>
          <option value="occupational">Occupational</option>
        </select>
      </div>

      {compliance.checks.map((check) => (
        <div key={check.label} className="compliance-row">
          <span className="check-label">{check.label}</span>
          <span className="check-values">
            {check.value.toFixed(1)} / {check.limit.toFixed(1)} {check.unit}
          </span>
          <span className={`check-status ${check.pass ? (check.ratio > 0.8 ? 'warn' : 'pass') : 'fail'}`}>
            {check.pass ? (check.ratio > 0.8 ? 'WARN' : 'PASS') : 'FAIL'}
          </span>
          <div className="margin-bar">
            <div
              className="margin-fill"
              style={{
                width: `${Math.min(check.ratio * 100, 100)}%`,
                background: check.ratio > 1 ? '#f87171'
                  : check.ratio > 0.8 ? '#fbbf24'
                  : '#4ade80',
              }}
            />
          </div>
        </div>
      ))}

      {compliance.margin_db != null && (
        <div className="compliance-footer">
          <span>Margin: {compliance.margin_db > 0 ? '+' : ''}{compliance.margin_db.toFixed(1)} dB</span>
          <span>f = {(compliance.freq_hz / 1e9).toFixed(1)} GHz</span>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Add CSS styles for compliance panel**

Add styles to the existing CSS file (inline styles or CSS module) for
`.compliance-panel`, `.compliance-row`, `.margin-bar`, `.margin-fill`,
`.check-status.pass`, `.check-status.warn`, `.check-status.fail`.

- [ ] **Step 3: Build and verify**

Run: `cd aegis-web && npm run build`

- [ ] **Step 4: Commit**

```bash
git add aegis-web/src/components/layout/HudOverlay.tsx
git commit -m "Add structured compliance panel with margin bars to HUD"
```

---

### Task 11: Peak location indicator

**Files:**
- Modify: `aegis-web/src/components/scene/BodyMesh.tsx`

- [ ] **Step 1: Add peak marker mesh**

After the body mesh, add a small glowing sphere at the peak location:

```tsx
// Find peak triangle index from averaged sab
const peakIdx = useMemo(() => {
  if (!sabAveragedArray) return null
  let maxVal = -Infinity
  let maxIdx = 0
  for (let i = 0; i < sabAveragedArray.length; i++) {
    if (sabAveragedArray[i] > maxVal) {
      maxVal = sabAveragedArray[i]
      maxIdx = i
    }
  }
  return maxIdx
}, [sabAveragedArray])

// Get centroid position from geometry
const peakPos = useMemo(() => {
  if (peakIdx === null || !geometry) return null
  const pos = geometry.getAttribute('position')
  // Each triangle = 3 vertices, centroid = average
  const i = peakIdx * 9  // 3 vertices * 3 coords
  const x = (pos.array[i] + pos.array[i+3] + pos.array[i+6]) / 3
  const y = (pos.array[i+1] + pos.array[i+4] + pos.array[i+7]) / 3
  const z = (pos.array[i+2] + pos.array[i+5] + pos.array[i+8]) / 3
  return [x, y, z] as [number, number, number]
}, [peakIdx, geometry])

// Render marker
{peakPos && (
  <mesh position={peakPos}>
    <sphereGeometry args={[0.005, 16, 16]} />
    <meshBasicMaterial color="#ff4444" transparent opacity={0.8} />
  </mesh>
)}
```

- [ ] **Step 2: Build and verify**

Run: `cd aegis-web && npm run build`

- [ ] **Step 3: Commit**

```bash
git add aegis-web/src/components/scene/BodyMesh.tsx
git commit -m "Add peak exposure location indicator on body mesh"
```

---

## Phase 4: Optimization and cleanup

### Task 12: Update viz/dashboard.py compliance display

**Files:**
- Modify: `src/aegis/viz/dashboard.py`

- [ ] **Step 1: Update dashboard compliance checks**

Replace all `result.peak_sab < ICNIRP_2020.sab_peak` with proper compliance
evaluation using the new module:

```python
from aegis.compliance import evaluate_compliance, ExposureScenario

compliance = evaluate_compliance(
    scenario=ExposureScenario.GENERAL_PUBLIC,
    freq_hz=result.freq_hz or 28e9,
    peak_sab_4cm2=float(np.max(result.sab_averaged)) if result.sab_averaged is not None else result.peak_sab,
    peak_sinc_local=float(np.max(result.sinc_averaged)) if result.sinc_averaged is not None else 0.0,
    sar_wb=result.sar_wb,
)
```

- [ ] **Step 2: Run tests**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x`

- [ ] **Step 3: Commit**

```bash
git add src/aegis/viz/dashboard.py
git commit -m "Update dashboard to use new compliance module"
```

---

### Task 13: JAX-compatible G matrix for differentiable optimization

**Files:**
- Modify: `src/aegis/geometry/averaging.py`
- Modify: `src/aegis/coherent/ecbf.py` (if optimization target is updated)

- [ ] **Step 1: Add JAX conversion utility**

In `src/aegis/geometry/averaging.py`:

```python
def averaging_matrix_to_jax(G):
    """Convert scipy sparse G to JAX-compatible format.

    Returns a dense JAX array (suitable for small-to-medium meshes)
    or a BCOO sparse array for large meshes.
    """
    try:
        import jax.numpy as jnp
        return jnp.array(G.toarray())
    except ImportError:
        raise ImportError("JAX is required for differentiable averaging")
```

- [ ] **Step 2: Test JAX conversion (skip if JAX not installed)**

```python
@pytest.mark.skipif(not _has_jax(), reason="JAX not installed")
def test_jax_conversion():
    from aegis.geometry.averaging import averaging_matrix_to_jax
    centroids, areas = _make_flat_grid(5)
    G = precompute_averaging_matrix(centroids, areas)
    G_jax = averaging_matrix_to_jax(G)
    assert G_jax.shape == G.shape
```

- [ ] **Step 3: Commit**

```bash
git add src/aegis/geometry/averaging.py tests/test_averaging_matrix.py
git commit -m "Add JAX-compatible averaging matrix conversion"
```

---

### Task 14: Final integration test and cleanup

**Files:**
- Run all tests
- Update docs if needed

- [ ] **Step 1: Run full test suite**

Run: `py -3.12 -m pytest tests/ -m "not slow" -x -v`
Expected: all PASS

- [ ] **Step 2: Run linter**

Run: `py -3.12 -m ruff check src/ tests/`
Run: `py -3.12 -m ruff format --check src/ tests/`
Fix any issues.

- [ ] **Step 3: Build frontend**

Run: `cd aegis-web && npm run build`
Expected: clean build

- [ ] **Step 4: Manual smoke test**

Run: `py -3.12 -m aegis.viewer --location "Ghent, Belgium"`
Open browser, verify:
- Compliance panel shows with correct limits
- Display mode selector works
- Frequency input present
- Peak marker visible

- [ ] **Step 5: Final commit and tag**

Stage only the files changed in this task (do not use `git add -A`):

```bash
git status  # review changes
# Stage specific files that were modified in cleanup
git commit -m "Complete compliance overhaul: ICNIRP 2020, S_inc, spatial averaging, viewer"
git tag v0.X.Y
git push origin master --tags
```
