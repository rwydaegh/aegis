"""Compliance dashboard: whole-body SAR, peak S_ab, rho, Q eigenspectrum.

Builds a multi-panel matplotlib or plotly figure summarizing dosimetry results.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from aegis.compliance import ICNIRP_2020
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

    # Panel 1: S_ab histogram
    ax = axes[0]
    sab = result.sab
    ax.hist(sab[sab > 0], bins=50, color="#e74c3c", alpha=0.8, edgecolor="white")
    limit = ICNIRP_2020.sab_peak
    ax.axvline(limit, color="gold", linewidth=2, linestyle="--", label=f"ICNIRP limit ({limit} W/m\u00b2)")
    ax.set_xlabel("S_ab (W/m\u00b2)")
    ax.set_ylabel("Triangle count")
    ax.set_title("S_ab distribution")
    ax.legend(fontsize=8)

    # Panel 2: compliance summary
    ax = axes[1]
    ax.axis("off")

    lines = [
        f"Fidelity level: {result.fidelity_level}",
        f"P_abs: {result.p_abs * 1e3:.2f} mW",
        f"Peak S_ab: {result.peak_sab:.3f} W/m\u00b2",
    ]

    if result.peak_sab_averaged is not None:
        lines.append(f"Peak S_ab (4 cm\u00b2 avg): {result.peak_sab_averaged:.3f} W/m\u00b2")

    if result.sar_wb is not None:
        lines.append(f"SAR_wb: {result.sar_wb * 1e3:.2f} mW/kg")
    elif body_mass is not None:
        if body_mass <= 0:
            raise ValueError("body_mass must be positive when provided")
        sar = result.p_abs / body_mass
        lines.append(f"SAR_wb: {sar * 1e3:.2f} mW/kg")

    # Compliance status
    sab_status = "PASS" if result.peak_sab < ICNIRP_2020.sab_peak else "FAIL"
    lines.append("")
    lines.append(f"S_ab compliance: {sab_status}")

    if result.sar_wb is not None:
        sar_status = "PASS" if result.sar_wb < ICNIRP_2020.sar_wb else "FAIL"
        lines.append(f"SAR compliance: {sar_status}")

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

    if is_coherent:
        # Panel 3: Q eigenspectrum
        ax = axes[2]
        eigs = result.eigenvalues
        if eigs is not None:
            n_eigs = len(eigs)
            ax.bar(range(n_eigs), eigs, color="#3498db", alpha=0.8)
            ax.set_xlabel("Eigenvalue index")
            ax.set_ylabel("Eigenvalue magnitude")
            ax.set_title("Q eigenspectrum")
            ax.set_yscale("log" if np.max(eigs) / (np.min(eigs[eigs > 0]) + 1e-30) > 100 else "linear")

        # Panel 4: rho gauge
        ax = axes[3]
        rho = result.rho if result.rho is not None else 0.0
        _draw_rho_gauge(ax, rho)

    plt.tight_layout()

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out_path), dpi=150, bbox_inches="tight")

    if show:
        plt.show()

    return fig


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
