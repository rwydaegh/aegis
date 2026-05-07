"""Tier-C ISAC detection vs range — paper figure for `paper_v2.tex` §VI.

Plots Pd(R) for the paper's operating point (26 GHz, 8x8 panel,
30 dBm Tx, 0 dBsm body, 400 MHz NR FR2, 6 dB NF), with three CPI
choices (1 ms / 10 ms / 100 ms coherent dwell) and Pfa = 1e-6.

Also annotates:
- the 50 m plaza range,
- the angular cell footprint at 50 m (HPBW * R = 11 m crossrange),
- the range cell at 400 MHz (0.375 m).

Run from repo root:
    python JSAC/code/experiments/tier_c_decision/detection_vs_range.py

Outputs:
    detection_vs_range.pdf
    detection_vs_range.png
    link_budget.json
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from aegis.sensing import (
    angular_resolution_deg,
    crossrange_resolution_m,
    detection_probability,
    monostatic_snr_db,
    range_resolution_m,
)

OUT_DIR = Path(__file__).parent

# Paper §VII operating point.
F_HZ = 26e9
B_HZ = 400e6
N_PER_SIDE = 8
EIRP_DBM = 30.0 + 21.0  # 30 dBm Tx + 21 dBi 8x8 panel gain
RX_GAIN_DBI = 21.0
RCS_DBSM = 0.0  # 1 m^2 standing torso at 26 GHz
NF_DB = 6.0
PFA = 1e-6

# CPI choices: 1 ms / 10 ms / 100 ms coherent dwell at numerology mu=2 (60 kHz SCS).
SCS = 15e3 * 4  # mu=2
CPI_MS = [1.0, 10.0, 100.0]


def cpi_gain_db(cpi_s: float) -> float:
    """Coherent integration gain for ``N`` OFDM symbols in a CPI of length cpi_s."""
    n = max(int(round(cpi_s * SCS)), 1)
    return 10.0 * math.log10(n)


def main() -> None:
    ranges = np.linspace(5.0, 200.0, 400)

    snrs_int: dict[float, np.ndarray] = {}
    pds: dict[float, np.ndarray] = {}
    snr_single = np.zeros_like(ranges)

    for cpi_ms in CPI_MS:
        g_db = cpi_gain_db(cpi_ms * 1e-3)
        snr_int_arr = np.empty_like(ranges)
        pd_arr = np.empty_like(ranges)
        for i, R in enumerate(ranges):
            s1, s_int = monostatic_snr_db(
                range_m=float(R),
                eirp_dbm=EIRP_DBM,
                rx_gain_dbi=RX_GAIN_DBI,
                freq_hz=F_HZ,
                bandwidth_hz=B_HZ,
                rcs_dbsm=RCS_DBSM,
                noise_figure_db=NF_DB,
                integration_gain_db=g_db,
            )
            snr_int_arr[i] = s_int
            pd_arr[i] = detection_probability(s_int, pfa=PFA)
            if cpi_ms == CPI_MS[0]:
                snr_single[i] = s1
        snrs_int[cpi_ms] = snr_int_arr
        pds[cpi_ms] = pd_arr

    hpbw = angular_resolution_deg(N_PER_SIDE, F_HZ)
    rng_res = range_resolution_m(B_HZ)
    cr_50 = crossrange_resolution_m(50.0, hpbw)

    # -----------------------------------------------------------------
    # Figure: two-panel, SNR(R) and Pd(R)
    # -----------------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.0), constrained_layout=True)

    ax0 = axes[0]
    for cpi_ms in CPI_MS:
        ax0.plot(ranges, snrs_int[cpi_ms], label=f"CPI = {cpi_ms:g} ms")
    ax0.axhline(13.2, color="k", linestyle=":", linewidth=0.8, label="Pd = 0.9 @ Pfa=1e-6")
    ax0.axvline(50.0, color="grey", linestyle="--", linewidth=0.8)
    ax0.text(50.5, 60.0, "plaza range", color="grey", fontsize=8)
    ax0.set_xlabel("Range R [m]")
    ax0.set_ylabel("Integrated SNR [dB]")
    ax0.set_title("Monostatic ISAC link budget\n8x8 @ 26 GHz, 30 dBm Tx, 0 dBsm body")
    ax0.set_xlim(5, 200)
    ax0.grid(True, alpha=0.3)
    ax0.legend(loc="upper right", fontsize=8, frameon=False)

    ax1 = axes[1]
    for cpi_ms in CPI_MS:
        ax1.plot(ranges, pds[cpi_ms], label=f"CPI = {cpi_ms:g} ms")
    ax1.axhline(0.9, color="k", linestyle=":", linewidth=0.8)
    ax1.axvline(50.0, color="grey", linestyle="--", linewidth=0.8)
    ax1.set_xlabel("Range R [m]")
    ax1.set_ylabel("Detection probability Pd  (Pfa = 1e-6)")
    ax1.set_title(f"Albersheim Pd, Swerling-0\nHPBW = {hpbw:.1f} deg  -> crossrange {cr_50:.1f} m at R=50 m")
    ax1.set_xlim(5, 200)
    ax1.set_ylim(-0.02, 1.05)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="lower left", fontsize=8, frameon=False)

    fig.suptitle("Tier-C ISAC detection at plaza range (paper v2 §VI)", fontsize=11, y=1.04)

    pdf_path = OUT_DIR / "detection_vs_range.pdf"
    png_path = OUT_DIR / "detection_vs_range.png"
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight", dpi=150)
    plt.close(fig)
    print(f"wrote {pdf_path}")
    print(f"wrote {png_path}")

    # -----------------------------------------------------------------
    # Numerical summary at R=50 m for the decision document.
    # -----------------------------------------------------------------
    summary = {
        "operating_point": {
            "carrier_GHz": 26.0,
            "bandwidth_MHz": B_HZ * 1e-6,
            "tx_power_dBm": 30.0,
            "panel_elements": N_PER_SIDE * N_PER_SIDE,
            "panel_gain_dBi": 21.0,
            "rcs_dBsm": RCS_DBSM,
            "noise_figure_dB": NF_DB,
            "pfa": PFA,
            "scs_kHz": SCS * 1e-3,
            "numerology_mu": 2,
        },
        "geometry_at_50m": {
            "azimuth_HPBW_deg": hpbw,
            "crossrange_m": cr_50,
            "range_resolution_m": rng_res,
            "cell_area_m2": cr_50 * rng_res,
        },
        "snr_at_50m": {
            "single_snapshot_dB": float(snr_single[np.argmin(np.abs(ranges - 50.0))]),
            "integrated_dB": {
                f"CPI_{cpi_ms:g}ms": float(snrs_int[cpi_ms][np.argmin(np.abs(ranges - 50.0))]) for cpi_ms in CPI_MS
            },
        },
        "pd_at_50m": {f"CPI_{cpi_ms:g}ms": float(pds[cpi_ms][np.argmin(np.abs(ranges - 50.0))]) for cpi_ms in CPI_MS},
        # Largest range at which Pd >= 0.99. If saturated across the
        # whole sweep, report the swept maximum and a saturation flag.
        "max_pd99_range_m": {
            f"CPI_{cpi_ms:g}ms": (float(ranges[pds[cpi_ms] >= 0.99].max()) if np.any(pds[cpi_ms] >= 0.99) else 0.0)
            for cpi_ms in CPI_MS
        },
        "pd99_saturated_at_max_range": {f"CPI_{cpi_ms:g}ms": bool(pds[cpi_ms][-1] >= 0.99) for cpi_ms in CPI_MS},
    }
    json_path = OUT_DIR / "link_budget.json"
    json_path.write_text(json.dumps(summary, indent=2))
    print(f"wrote {json_path}")


if __name__ == "__main__":
    main()
