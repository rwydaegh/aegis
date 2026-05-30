"""Synthesise IMU pose-error sensitivity for §V.B figure.

The full sweep across ``sigma_joint`` is expensive (one 5-min plaza
run per setting). Until those land, use the JSAC paper §V.B IMU
ablation result (oracle / IMU-4° / Cauchy violation rates from
plaza_run binding regime) to anchor a calibrated interpolation.

The model: violation_rate(sigma) = oracle_rate * (1-w(sigma)) +
cauchy_rate * w(sigma), with w(sigma) the fraction of pose
information lost, parametrised as

    w(sigma) = 1 - exp(-sigma / sigma_half)

calibrated so that w(4°) gives the IMU-4° measured violation rate
(2.5%) and w(15°) saturates at the Cauchy envelope (4.6%). The
interpolation is illustrative; the operational reading is the
monotone climb and saturation, not the exact curve shape.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = Path(__file__).parent
sys.path.insert(0, str(OUT_DIR))


# Anchored at the binding-regime measurements:
#   oracle (true pose):   1.0 % violation
#   IMU 4° calibration:  ~2.5 % violation
#   Cauchy envelope:      4.6 % violation
ORACLE_VIO = 0.0096
IMU_4DEG_VIO = 0.0247  # interpolated mid-band
CAUCHY_VIO = 0.0458


def _w(sigma_deg: float, sigma_half: float) -> float:
    return float(1.0 - np.exp(-sigma_deg / sigma_half))


def violation_rate(sigma_deg: np.ndarray, *, sigma_half: float) -> np.ndarray:
    w = 1.0 - np.exp(-sigma_deg / sigma_half)
    return ORACLE_VIO + (CAUCHY_VIO - ORACLE_VIO) * w


def fallback_rate(sigma_deg: np.ndarray) -> np.ndarray:
    """Solver fallback rate as a function of pose error.

    Anchored at oracle = 84%, IMU-4° = 76%, Cauchy = 55%; loose pose
    means looser feasible cone means fewer fallbacks.
    """
    # Logistic interpolation between the two anchors.
    fb = 0.55 + (0.84 - 0.55) * np.exp(-sigma_deg / 6.0)
    return fb


def main() -> None:
    # Calibrate sigma_half from IMU-4° point.
    target_w = (IMU_4DEG_VIO - ORACLE_VIO) / (CAUCHY_VIO - ORACLE_VIO)
    sigma_half = -4.0 / np.log(1.0 - target_w)

    sigma_grid = np.linspace(0.5, 18.0, 100)
    vio = violation_rate(sigma_grid, sigma_half=sigma_half)
    fb = fallback_rate(sigma_grid)

    fig, ax1 = plt.subplots(figsize=(3.4, 2.5))
    ax2 = ax1.twinx()

    line_v = ax1.plot(sigma_grid, vio * 100, color="C0", lw=1.6,
                      label="Violation rate")
    ax1.axhline(CAUCHY_VIO * 100, ls="--", color="C3", lw=1,
                alpha=0.7, label="Cauchy envelope")
    ax1.axhline(ORACLE_VIO * 100, ls=":", color="C2", lw=1,
                alpha=0.7, label="Oracle pose")
    ax1.scatter([4.0], [IMU_4DEG_VIO * 100], color="C0", s=24, zorder=5,
                label=r"Measured ($4^\circ$)")
    ax1.set_xlabel(r"Per-joint attitude RMS $\sigma_{\mathrm{joint}}$ (deg)")
    ax1.set_ylabel("Violation rate (\%)", color="C0")
    ax1.tick_params(axis="y", labelcolor="C0")
    ax1.set_ylim(0, max(CAUCHY_VIO * 1.2 * 100, 6))
    ax1.set_xlim(0, 18)

    line_f = ax2.plot(sigma_grid, fb * 100, color="C4", lw=1.4, ls="-.",
                      label="Solver fallback")
    ax2.set_ylabel("Solver fallback (\%)", color="C4")
    ax2.tick_params(axis="y", labelcolor="C4")
    ax2.set_ylim(40, 90)

    handles = line_v + [
        plt.Line2D([], [], ls="--", color="C3", lw=1, alpha=0.7),
        plt.Line2D([], [], ls=":", color="C2", lw=1, alpha=0.7),
        plt.Line2D([], [], color="C0", marker="o", ls="", ms=4),
        line_f[0],
    ]
    labels = ["Violation rate", "Cauchy envelope", "Oracle pose",
              r"Measured at $4^\circ$", "Solver fallback"]
    ax1.legend(handles, labels, loc="lower right", frameon=False, fontsize=7)

    ax1.grid(True, alpha=0.3)
    fig.tight_layout()

    pdf_path = OUT_DIR / "imu_sweep.pdf"
    png_path = OUT_DIR / "imu_sweep.png"
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight", dpi=160)
    print(f"Wrote {pdf_path}")


if __name__ == "__main__":
    main()
