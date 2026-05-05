"""CSI per-path calibration residual sweep (paper §V.B).

For a synthetic single-body, single-cell path dictionary, perturb the
in-silico per-path complex amplitudes with a log-normal-magnitude /
von-Mises-phase IID model (the "deployed channel" stand-in), synthesise
uplink BS-side CSI at a given SNR, run the §V.B least-squares calibration
to recover a per-path complex scale factor, and report the residual error
between the recovered scale and the planted perturbation.

Residual metric (parameter-space):

    rho_dB = 20 * log10( ||beta_hat - gamma||_2 / ||gamma||_2 )

where gamma is the planted multiplicative perturbation and beta_hat is the
LS solution. This directly measures how well calibration would reproduce
the deployed amplitudes that downstream Q-construction needs.

We sweep:
  - UL SNR in {0, 5, 10, 15, 20, 25, 30} dB (per-element receive SNR)
  - N_paths in {20, 40, 60} (matching the rank-CDF experiment's 60 used
    for 3GPP UMa-LOS)

Outputs
-------
    residual_vs_snr.pdf,.png    -- the figure, one curve per N_paths.
    residual_table.md           -- mean / 90th-percentile residual per cell.
    residuals.npz               -- raw per-trial residuals.

Run
---
    python -m JSAC.code.experiments.csi_calibration.run_calibration

or directly:
    python JSAC/code/experiments/csi_calibration/run_calibration.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make in-repo aegis importable regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import matplotlib.pyplot as plt
import numpy as np

from aegis.constants import C_0
from aegis.mimo.array import AntennaArray
from aegis.twin.path_dictionary import calibrate_amplitudes

# ----------------------------------------------------------------------
# Scenario constants -- matched to rank_check / paper hero
# ----------------------------------------------------------------------
FREQ_HZ = 26.0e9
N_H, N_V = 8, 8  # 8x8 panel
M_ANT = N_H * N_V  # 64
SECTOR_AZ_HALF_DEG = 60.0  # paths fall inside +/- 60 deg in azimuth
SECTOR_EL_HALF_DEG = 30.0  # +/- 30 deg in elevation around broadside

# Perturbation model (the in-silico vs deployed gap stand-in).
# IID per path: log-normal magnitude (sigma_dB), von Mises phase (kappa).
# sigma_dB = 3 dB amounts to ~ +/- 4 dB 1-sigma of magnitude error.
# kappa = 4 corresponds to ~ 30 deg circular-stddev phase error.
PERT_SIGMA_DB = 3.0
PERT_KAPPA = 4.0

SNR_DB_GRID = np.arange(0.0, 30.0 + 1e-6, 5.0)
N_PATHS_GRID = (20, 40, 60)
N_TRIALS = 200

OUTPUT_DIR = Path(__file__).resolve().parent


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _make_array() -> AntennaArray:
    """8x8 UPA with half-wavelength spacing centred at origin, broadside +x."""
    spacing = 0.5 * C_0 / FREQ_HZ
    return AntennaArray.upa(
        n_h=N_H,
        n_v=N_V,
        d_h=spacing,
        d_v=spacing,
        center=np.zeros(3),
        broadside=np.array([1.0, 0.0, 0.0]),
        element_pattern="isotropic",
    )


def _sample_directions(n_paths: int, rng: np.random.Generator) -> np.ndarray:
    """N unit directions in the BS sector, broadside = +x."""
    az = np.deg2rad(rng.uniform(-SECTOR_AZ_HALF_DEG, SECTOR_AZ_HALF_DEG, n_paths))
    el = np.deg2rad(rng.uniform(-SECTOR_EL_HALF_DEG, SECTOR_EL_HALF_DEG, n_paths))
    cos_el = np.cos(el)
    return np.stack([cos_el * np.cos(az), cos_el * np.sin(az), np.sin(el)], axis=1)


def _sample_alpha_insilico(n_paths: int, rng: np.random.Generator) -> np.ndarray:
    """Per-path in-silico amplitudes: unit-mean complex Gaussian (Rayleigh mag)."""
    return (rng.standard_normal(n_paths) + 1j * rng.standard_normal(n_paths)) / np.sqrt(2.0)


def _sample_perturbation(n_paths: int, rng: np.random.Generator) -> np.ndarray:
    """Log-normal magnitude (sigma_dB) and von-Mises phase (kappa)."""
    log_mag_db = rng.normal(0.0, PERT_SIGMA_DB, n_paths)
    mag = 10.0 ** (log_mag_db / 20.0)
    phase = rng.vonmises(0.0, PERT_KAPPA, n_paths)
    return mag * np.exp(1j * phase)


def _add_awgn(h_clean: np.ndarray, snr_db: float, rng: np.random.Generator) -> np.ndarray:
    """Per-element AWGN at the requested SNR (signal-power / per-element noise-power)."""
    sig_pow = float(np.mean(np.abs(h_clean) ** 2))
    noise_pow = sig_pow / (10.0 ** (snr_db / 10.0))
    sigma = np.sqrt(noise_pow / 2.0)
    n = sigma * (rng.standard_normal(h_clean.shape) + 1j * rng.standard_normal(h_clean.shape))
    return h_clean + n


RIDGE_STRENGTH = 1.0e-2  # for the ridge-LS comparison curve at N=N_max


# ----------------------------------------------------------------------
# Single trial
# ----------------------------------------------------------------------
def _run_trial(
    array: AntennaArray,
    n_paths: int,
    snr_db: float,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    """Return (rho_no_cal, rho_ls, rho_ridge) -- linear (not dB) residuals."""
    k_hat = _sample_directions(n_paths, rng)
    # steering_matrix returns (N, M); we want (M, N) for a column-per-path design.
    A_steer = array.steering_matrix(k_hat, FREQ_HZ).T

    alpha_insilico = _sample_alpha_insilico(n_paths, rng)
    gamma = _sample_perturbation(n_paths, rng)
    alpha_deployed = gamma * alpha_insilico

    # "Deployed" CSI = sum_n alpha_deployed_n * a_n + noise.
    h_clean = A_steer @ alpha_deployed
    h_meas = _add_awgn(h_clean, snr_db, rng)

    norm_gamma = np.linalg.norm(gamma)
    rho_no_cal = float(np.linalg.norm(np.ones_like(gamma) - gamma) / norm_gamma)

    beta_ls = calibrate_amplitudes(A_steer, alpha_insilico, h_meas)
    rho_ls = float(np.linalg.norm(beta_ls - gamma) / norm_gamma)

    beta_ridge = calibrate_amplitudes(A_steer, alpha_insilico, h_meas, ridge=RIDGE_STRENGTH)
    rho_ridge = float(np.linalg.norm(beta_ridge - gamma) / norm_gamma)

    return rho_no_cal, rho_ls, rho_ridge


# ----------------------------------------------------------------------
# Sweep
# ----------------------------------------------------------------------
def run_sweep() -> dict[str, np.ndarray]:
    array = _make_array()
    rng = np.random.default_rng(seed=20260504)

    shape = (len(N_PATHS_GRID), len(SNR_DB_GRID), N_TRIALS)
    rho_no_cal = np.empty(shape, dtype=np.float64)
    rho_ls = np.empty(shape, dtype=np.float64)
    rho_ridge = np.empty(shape, dtype=np.float64)

    for i, n_paths in enumerate(N_PATHS_GRID):
        for j, snr_db in enumerate(SNR_DB_GRID):
            for t in range(N_TRIALS):
                a, b, c = _run_trial(array, n_paths, snr_db, rng)
                rho_no_cal[i, j, t] = a
                rho_ls[i, j, t] = b
                rho_ridge[i, j, t] = c
        print(
            f"N_paths={n_paths:>3d}  done  "
            f"(median LS / ridge residual at 0/30 dB: "
            f"{20 * np.log10(np.median(rho_ls[i, 0])):+6.2f} / "
            f"{20 * np.log10(np.median(rho_ls[i, -1])):+6.2f}  ;  "
            f"{20 * np.log10(np.median(rho_ridge[i, 0])):+6.2f} / "
            f"{20 * np.log10(np.median(rho_ridge[i, -1])):+6.2f} dB)"
        )

    return {
        "snr_db": SNR_DB_GRID,
        "n_paths": np.array(N_PATHS_GRID),
        "rho_no_cal": rho_no_cal,
        "rho_ls": rho_ls,
        "rho_ridge": rho_ridge,
        "ridge_strength": np.array(RIDGE_STRENGTH),
    }


# ----------------------------------------------------------------------
# Plotting and reporting
# ----------------------------------------------------------------------
def _plot(out: dict[str, np.ndarray]) -> None:
    snr_db = out["snr_db"]
    rho_no_cal = out["rho_no_cal"]
    rho_ls = out["rho_ls"]
    rho_ridge = out["rho_ridge"]

    fig, ax = plt.subplots(figsize=(5.6, 4.0))
    colors = plt.cm.viridis(np.linspace(0.15, 0.85, len(N_PATHS_GRID)))

    for i, n_paths in enumerate(N_PATHS_GRID):
        ls_med = 20.0 * np.log10(np.median(rho_ls[i], axis=1))
        ls_p10 = 20.0 * np.log10(np.quantile(rho_ls[i], 0.1, axis=1))
        ls_p90 = 20.0 * np.log10(np.quantile(rho_ls[i], 0.9, axis=1))
        ax.plot(
            snr_db,
            ls_med,
            color=colors[i],
            marker="o",
            lw=1.6,
            label=f"plain LS, $N={n_paths}$",
        )
        ax.fill_between(snr_db, ls_p10, ls_p90, color=colors[i], alpha=0.15, lw=0)

        ridge_med = 20.0 * np.log10(np.median(rho_ridge[i], axis=1))
        ax.plot(
            snr_db,
            ridge_med,
            color=colors[i],
            marker="s",
            lw=1.2,
            ls="--",
            label=f"ridge LS, $N={n_paths}$",
        )

    # No-calibration baseline. Independent of SNR; collapse across all (i, j, t).
    no_cal_med_db = 20.0 * np.log10(np.median(rho_no_cal))
    ax.axhline(
        no_cal_med_db,
        ls=":",
        color="k",
        lw=1.2,
        label=rf"no calibration ($\beta=1$): {no_cal_med_db:+.1f} dB",
    )

    ax.set_xlabel("Uplink SNR per element [dB]")
    ax.set_ylabel(
        r"Per-path scale residual  "
        r"$20\log_{10}\|\hat{\beta}-\gamma\|/\|\gamma\|$  [dB]"
    )
    ax.set_title(
        "CSI per-path calibration residual\n"
        f"$M_\\mathrm{{ant}}={M_ANT}$, "
        f"$\\sigma_\\mathrm{{mag}}={PERT_SIGMA_DB:g}$ dB, "
        f"$\\kappa_\\mathrm{{phase}}={PERT_KAPPA:g}$, "
        f"{N_TRIALS} trials, ridge $={RIDGE_STRENGTH:g}$"
    )
    ax.legend(frameon=False, loc="upper right", ncol=2, fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_ylim(top=max(ax.get_ylim()[1], 5.0), bottom=min(-30.0, ax.get_ylim()[0]))
    fig.tight_layout()

    pdf = OUTPUT_DIR / "residual_vs_snr.pdf"
    png = OUTPUT_DIR / "residual_vs_snr.png"
    fig.savefig(pdf)
    fig.savefig(png, dpi=180)
    plt.close(fig)
    print(f"wrote  {pdf.name}, {png.name}")


def _table(out: dict[str, np.ndarray]) -> None:
    snr_db = out["snr_db"]
    rho_ls = out["rho_ls"]
    rho_ridge = out["rho_ridge"]
    no_cal_db = 20.0 * np.log10(np.median(out["rho_no_cal"]))
    lines = []
    lines.append("# CSI calibration residual table\n")
    lines.append(
        "Median (and 90th-percentile) parameter-space residual "
        r"$20\log_{10}\|\hat\beta-\gamma\|/\|\gamma\|$ in dB across "
        f"{N_TRIALS} trials per cell. "
        f"No-calibration baseline ($\\beta=1$): {no_cal_db:+.1f} dB (median, all trials).\n"
    )
    for tag, mat in (("plain LS", rho_ls), ("ridge LS", rho_ridge)):
        lines.append(f"## {tag}\n")
        header = "| SNR [dB] | " + " | ".join(f"N={n}" for n in N_PATHS_GRID) + " |"
        sep = "|" + "---|" * (1 + len(N_PATHS_GRID))
        lines.append(header)
        lines.append(sep)
        for j, snr in enumerate(snr_db):
            cells = []
            for i in range(len(N_PATHS_GRID)):
                med = 20.0 * np.log10(np.median(mat[i, j]))
                p90 = 20.0 * np.log10(np.quantile(mat[i, j], 0.9))
                cells.append(f"{med:+5.1f}  ({p90:+5.1f})")
            lines.append(f"| {int(snr):>3d}      | " + " | ".join(cells) + " |")
        lines.append("")
    md = OUTPUT_DIR / "residual_table.md"
    md.write_text("\n".join(lines) + "\n")
    print(f"wrote  {md.name}")


def main() -> None:
    out = run_sweep()
    np.savez(OUTPUT_DIR / "residuals.npz", **out)
    _plot(out)
    _table(out)


if __name__ == "__main__":
    main()
