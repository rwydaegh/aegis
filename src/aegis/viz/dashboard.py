"""Compliance dashboard: whole-body SAR, peak S_ab, rho, Q eigenspectrum.

Builds a multi-panel matplotlib or plotly figure summarizing dosimetry results.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from aegis.compliance import ExposureScenario, evaluate_compliance, icnirp_limits
from aegis.defaults import DEFAULT_FREQ_HZ, NUMERICAL_FLOOR
from aegis.result import DosimetryResult


def plot_dashboard(
    result: DosimetryResult,
    *,
    body_mass: float | None = None,
    title: str = "AEGIS compliance dashboard",
    out_path: str | Path | None = None,
    show: bool = True,
) -> Any:
    """Render a multi-panel compliance dashboard.

    Panels:
    1. S_ab histogram with ICNIRP 10 W/m^2 limit line
    2. Compliance status bar (pass/fail for SAR and S_ab)
    3. Q eigenspectrum (if coherent result)
    4. rho gauge (if coherent result)

    Parameters
    ----------
    result : DosimetryResult from engine.compute()
    body_mass : body mass [kg] for SAR display
    title : dashboard title
    out_path : save PNG to this path
    show : display figure

    Returns
    -------
    matplotlib Figure
    """
    import matplotlib.pyplot as plt

    is_coherent = result.Q is not None
    n_panels = 4 if is_coherent else 2

    fig, axes = plt.subplots(1, n_panels, figsize=(5 * n_panels, 5))
    if n_panels == 1:
        axes = [axes]
    fig.suptitle(title, fontsize=14, fontweight="bold")

    _draw_sab_histogram(axes[0], result)
    _draw_compliance_summary(axes[1], result, body_mass)

    if is_coherent:
        _draw_eigenspectrum(axes[2], result)
        rho = result.rho if result.rho is not None else 0.0
        _draw_rho_gauge(axes[3], rho)

    plt.tight_layout()

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out_path), dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig


def _draw_sab_histogram(ax: Any, result: DosimetryResult) -> None:
    """Draw S_ab histogram with ICNIRP limit line (panel 1)."""
    sab = result.sab
    ax.hist(sab[sab > 0], bins=50, color="#e74c3c", alpha=0.8, edgecolor="white")
    freq_hz = result.freq_hz or DEFAULT_FREQ_HZ
    limits = icnirp_limits(ExposureScenario.GENERAL_PUBLIC, freq_hz)
    limit = limits.sab_4cm2
    if limit is not None:
        ax.axvline(limit, color="gold", linewidth=2, linestyle="--", label=f"ICNIRP limit ({limit} W/m\u00b2)")
    ax.set_xlabel("S_ab (W/m\u00b2)")
    ax.set_ylabel("Triangle count")
    ax.set_title("S_ab distribution")
    ax.legend(fontsize=8)


def _draw_compliance_summary(ax: Any, result: DosimetryResult, body_mass: float | None) -> None:
    """Draw compliance text summary panel (panel 2)."""
    ax.axis("off")

    lines = [
        f"Fidelity level: {result.fidelity_level}",
        f"P_abs: {result.p_abs * 1e3:.2f} mW",
        f"Peak S_ab: {result.peak_sab:.3f} W/m\u00b2",
    ]

    if result.peak_sab_averaged is not None:
        lines.append(f"Peak S_ab (4 cm\u00b2 avg): {result.peak_sab_averaged:.3f} W/m\u00b2")

    sar_wb = result.sar_wb
    if sar_wb is not None:
        lines.append(f"SAR_wb: {sar_wb * 1e3:.2f} mW/kg")
    elif body_mass is not None:
        if body_mass <= 0:
            raise ValueError("body_mass must be positive when provided")
        sar_wb = result.p_abs / body_mass
        lines.append(f"SAR_wb: {sar_wb * 1e3:.2f} mW/kg")

    # Compliance evaluation via centralized kwargs
    freq_hz = result.freq_hz or DEFAULT_FREQ_HZ
    ckw = result.compliance_kwargs()
    if sar_wb is not None:
        ckw["sar_wb"] = sar_wb  # Override with body_mass-derived SAR if available
    compliance = evaluate_compliance(
        scenario=ExposureScenario.GENERAL_PUBLIC,
        freq_hz=freq_hz,
        **ckw,
    )

    lines.append("")
    for check in compliance.all_checks:
        status = "PASS" if check.compliant else "FAIL"
        lines.append(f"{check.label}: {status} (margin {check.margin_db:+.1f} dB)")

    lines.append("")
    overall = "PASS" if compliance.overall_pass else "FAIL"
    lines.append(f"Overall: {overall}")

    for i, line in enumerate(lines):
        color = "black"
        weight = "normal"
        if "PASS" in line:
            color = "#2ecc71"
            weight = "bold"
        elif "FAIL" in line:
            color = "#e74c3c"
            weight = "bold"
        ax.text(
            0.1,
            0.9 - i * 0.1,
            line,
            transform=ax.transAxes,
            fontsize=11,
            verticalalignment="top",
            color=color,
            fontweight=weight,
        )
    ax.set_title("Compliance summary")


def _draw_eigenspectrum(ax: Any, result: DosimetryResult) -> None:
    """Draw Q eigenvalue bar chart (panel 3)."""
    eigs = result.eigenvalues
    if eigs is not None:
        n_eigs = len(eigs)
        ax.bar(range(n_eigs), eigs, color="#3498db", alpha=0.8)
        ax.set_xlabel("Eigenvalue index")
        ax.set_ylabel("Eigenvalue magnitude")
        ax.set_title("Q eigenspectrum")
        ax.set_yscale("log" if np.max(eigs) / (np.min(eigs[eigs > 0]) + NUMERICAL_FLOOR) > 100 else "linear")


def _draw_rho_gauge(ax: Any, rho: float) -> None:
    """Draw a semicircular rho gauge (0 to 1)."""
    theta = np.linspace(0, np.pi, 100)

    # Background arc
    ax.plot(np.cos(theta), np.sin(theta), color="#bdc3c7", linewidth=8)

    # Filled arc up to rho
    theta_fill = np.linspace(0, np.pi * rho, 100)
    color = "#2ecc71" if rho < 0.5 else "#f39c12" if rho < 0.8 else "#e74c3c"
    ax.plot(np.cos(theta_fill), np.sin(theta_fill), color=color, linewidth=8)

    # Needle
    needle_angle = np.pi * rho
    ax.plot(
        [0, 0.8 * np.cos(needle_angle)],
        [0, 0.8 * np.sin(needle_angle)],
        color="black",
        linewidth=2,
    )
    ax.plot(0, 0, "ko", markersize=6)

    ax.text(0, -0.2, f"\u03c1 = {rho:.3f}", ha="center", fontsize=14, fontweight="bold")
    ax.text(-1.0, -0.05, "0", ha="center", fontsize=10)
    ax.text(1.0, -0.05, "1", ha="center", fontsize=10)
    ax.set_xlim(-1.3, 1.3)
    ax.set_ylim(-0.4, 1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("Exposure-signal alignment \u03c1")
