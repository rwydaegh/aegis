"""Regenerate paper_jsac_v3 figures and Table II numbers from real bind5min runs.

Consumes:
    bind5min_v3_oracle.npz                 --pose-source oracle
    bind5min_v3_imu4.npz                   --pose-source imu  --imu-rms-deg 4
    bind5min_v3_tpose.npz                  --pose-source tpose --ablate-pose-telemetry
    bind5min_v3_imu{1,2,8,16}.npz          --pose-source imu  --imu-rms-deg {1,2,8,16}
        (optional; used when present to plot a real IMU sigma sweep)

Outputs (under JSAC/code/experiments/plaza_run/figures/):
    hero_binding.{pdf,png}      ECDF of P_abs/L_RL + sum-rate / violation Pareto
    pose_info_gain.{pdf,png}    Triage: violation, sum-rate, projection-active rate
    imu_sweep.{pdf,png}         Real sigma sweep (or anchored interpolation fallback)
    spatial_heatmap.{pdf,png}   Per-cell mean P_abs/L_RL on a tight crop, log color
    chronic_dose.{pdf,png}      ECDF of body-integrated absorbed energy by tier
    table_pose_triage.txt       LaTeX table body for the paper
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np

from _figstyle import apply_monograph_style, fig_size_ieee, save_both

ROOT = Path(__file__).resolve().parents[5]
NPZ_DIR = ROOT / "JSAC" / "code" / "experiments" / "plaza_run" / "outputs"
OUT_DIR = Path(__file__).parent
FALLBACK_NPZ = NPZ_DIR / "plaza_run_seed42_physhannon_poseaware_pathsdict_bind5min.npz"

L_RL = 0.00693  # body budget [W] at E_RL=3V/m (T0 * S * A * eta)
PRECODER_NAMES = ["mrt", "zf", "wc_backoff", "zf_proj", "zf_proj_proposed",
                  "multibody_ecbf", "oracle"]
PRECODER_DISPLAY = {
    "mrt": "MRT",
    "zf": "ZF (raw)",
    "wc_backoff": "WC back-off",
    "zf_proj": "ZF + proj (oracle)",
    "zf_proj_proposed": "ZF + proj (deploy)",
    "multibody_ecbf": "ECBF (IMU pose)",
    "oracle": "Oracle ECBF",
}
PRECODER_COLORS = {
    "mrt": "#b2182b",
    "zf": "#ef8a62",
    "wc_backoff": "#fddbc7",
    "zf_proj": "#2ca02c",
    "zf_proj_proposed": "#5fa55a",
    "multibody_ecbf": "#2166ac",
    "oracle": "#67a9cf",
}
PRECODER_MARKERS = {
    "mrt": "o", "zf": "s", "wc_backoff": "D", "zf_proj": "P",
    "zf_proj_proposed": "X",
    "multibody_ecbf": "^", "oracle": "v",
}


def load(tag):
    # Try v8 first (zf_proj_proposed column populated), then v7 (E_RL=3V/m,
    # noise=1e-12 matched solver/eval, zf_proj stored), then v6 (zf_proj
    # stored but noise=1e-3 in solver), then v4 (post-hoc zf_proj), then
    # v3 (6V/m), then fallback.
    for prefix in ["bind3v_v8_", "bind3v_v7_", "bind3v_v6_", "bind3v_v4_", "bind5min_v3_"]:
        cands = list(NPZ_DIR.glob(f"plaza_run_seed42_*{prefix}{tag}.npz"))
        if cands:
            return np.load(cands[0], allow_pickle=True)
    if FALLBACK_NPZ.exists():
        print(f"  WARN: tag {tag} missing; using fallback {FALLBACK_NPZ.name}")
        return np.load(FALLBACK_NPZ, allow_pickle=True)
    raise FileNotFoundError(f"Could not find NPZ for tag {tag} in {NPZ_DIR}")


def _zf_proj_post_hoc(z, eta_S=0.97):
    """Compute ZF + per-slot primal-projection arrays from a run that does
    not include zf_proj as a stored precoder."""
    pn = [str(s) for s in z["precoder_names"]]
    zf_idx = pn.index("zf")
    p_abs_zf = z["p_abs"][:, :, zf_idx]  # (T, B)
    sr_zf = z["sumrate"][:, zf_idx]  # (T,)
    budgets = z["body_budgets_w"]
    margin = eta_S * budgets[None, :] / np.maximum(p_abs_zf, 1e-30)
    scale_sq = np.clip(margin.min(axis=1), 0.0, 1.0)
    p_abs_proj = p_abs_zf * scale_sq[:, None]
    sr_proj = sr_zf * scale_sq
    return p_abs_proj, sr_proj


def _augment_with_zf_proj(z):
    """Return a dict-like view of z with zf_proj inserted as an extra
    precoder column; passes through .files membership for callers."""
    pn = [str(s) for s in z["precoder_names"]]
    if "zf_proj" in pn:
        return z, pn
    p_abs_proj, sr_proj = _zf_proj_post_hoc(z)
    budgets = z["body_budgets_w"]
    viol_proj = (p_abs_proj > budgets[None, :])
    infeas_proj = np.zeros(z["sumrate"].shape[0], dtype=bool)
    new_pn = pn + ["zf_proj"]
    new_p_abs = np.concatenate([z["p_abs"], p_abs_proj[..., None]], axis=2)
    new_sr = np.concatenate([z["sumrate"], sr_proj[:, None]], axis=1)
    new_v = np.concatenate([z["violation"], viol_proj[..., None]], axis=2)
    new_inf = np.concatenate([z["infeasible"], infeas_proj[:, None]], axis=1)
    return _NpzView(z, new_pn, new_p_abs, new_sr, new_v, new_inf), new_pn


class _NpzView:
    """Read-only adapter exposing the same dict-style access as np.load
    output for the few keys our regen consumes, with augmented columns."""
    def __init__(self, base, pn, p_abs, sr, viol, infeas):
        self._base = base
        self._overrides = {
            "precoder_names": np.array(pn),
            "p_abs": p_abs,
            "sumrate": sr,
            "violation": viol,
            "infeasible": infeas,
        }

    def __getitem__(self, k):
        if k in self._overrides:
            return self._overrides[k]
        return self._base[k]

    @property
    def files(self):
        return list(self._base.files) + ["augmented_zf_proj"]


def precoder_stats(z):
    pn = list(z["precoder_names"]) if "precoder_names" in z.files else PRECODER_NAMES
    stats = {}
    for i, name in enumerate(pn):
        v = float(z["violation"][:, :, i].mean()) * 100
        sr = float(z["sumrate"][:, i].mean()) / 1e9
        infeas = float(z["infeasible"][:, i].mean()) * 100
        p99 = float(np.percentile(z["p_abs"][:, :, i], 99))
        stats[str(name)] = {
            "viol_pct": v,
            "mean_sr_gbps": sr,
            "fallback_pct": infeas,
            "p99": p99,
        }
    return stats


def make_hero(z):
    """Two-column figure: (a) ECDF of P_abs/L_RL with violation shading,
    (b) sum-rate vs violation Pareto with one marker per precoder."""
    pn = [str(s) for s in z["precoder_names"]]
    p_abs = z["p_abs"]
    sumrate = z["sumrate"]
    violation = z["violation"]

    # Hero figure shows the operationally-relevant set: MRT, ZF (raw),
    # WC back-off, ZF + proj (deployable variant since it's the head-to-head
    # match), ECBF (IMU pose), Oracle. ZF + proj (oracle) is dropped to keep
    # the legend manageable; it overlaps zf_proj_proposed everywhere except
    # tier-C tail and is reported in Table II.
    HERO_PRECODERS = ["mrt", "zf", "wc_backoff",
                      "zf_proj_proposed" if "zf_proj_proposed" in pn else "zf_proj",
                      "multibody_ecbf", "oracle"]

    fig, (ax_a, ax_b) = plt.subplots(
        1, 2, figsize=fig_size_ieee(columns=2, aspect=0.40),
    )

    # (a) ECDFs
    for name in HERO_PRECODERS:
        if name not in pn:
            continue
        i = pn.index(name)
        r = (p_abs[:, :, i] / L_RL).reshape(-1)
        r_sorted = np.sort(np.maximum(r, 1e-6))
        f = np.arange(1, len(r_sorted) + 1) / len(r_sorted)
        # Override display name so "ZF + proj" reads cleanly in the hero
        # figure when we picked the deployable variant.
        disp = PRECODER_DISPLAY[name]
        if name == "zf_proj_proposed":
            disp = "ZF + proj"
        ax_a.plot(r_sorted, f, color=PRECODER_COLORS[name], lw=1.6,
                  label=disp)
    ax_a.axvspan(1.0, 1e2, alpha=0.10, color="#b2182b", lw=0)
    ax_a.axvline(1.0, color="#b2182b", ls=":", lw=1.0, alpha=0.7)
    ax_a.text(1.05, 0.04, "violates RL", color="#b2182b", fontsize=8,
              alpha=0.85)
    ax_a.set_xscale("log")
    ax_a.set_xlim(1e-3, 6.0)
    ax_a.set_ylim(0, 1.005)
    ax_a.set_xlabel(r"$P_{\mathrm{abs}}^{(u)} / L_{\mathrm{RL}}^{(u)}$ per body-slot")
    ax_a.set_ylabel("ECDF over body-slots")
    ax_a.set_title("(a) Per-body compliance")
    ax_a.legend(loc="upper left", frameon=False, fontsize=8)
    ax_a.grid(True, alpha=0.3)

    # (b) Pareto: violation rate (%) vs mean sum-rate (Gbps).
    # Use a legend on the right rather than per-marker labels so we don't
    # have to hand-place text around overlapping points.
    xs, ys, names = [], [], []
    for name in HERO_PRECODERS:
        if name not in pn:
            continue
        i = pn.index(name)
        v = float(violation[:, :, i].mean()) * 100
        s = float(sumrate[:, i].mean()) / 1e9
        xs.append(v); ys.append(s); names.append(name)
        disp = PRECODER_DISPLAY[name]
        if name == "zf_proj_proposed":
            disp = "ZF + proj"
        ax_b.scatter(v, s, marker=PRECODER_MARKERS[name],
                     s=110, color=PRECODER_COLORS[name],
                     edgecolor="k", linewidth=0.7, zorder=4,
                     label=disp)
    xmax = max(xs) if xs else 1
    sr_max = max(ys) if ys else 1
    cap_x = max(xmax * 0.05, 1.0)
    ax_b.axvspan(0, cap_x, alpha=0.10, color="#2ca02c", lw=0)
    ax_b.text(cap_x * 1.3, sr_max * 0.005, "compliant",
              fontsize=7, color="#2ca02c", ha="left", va="bottom", alpha=0.85)
    ax_b.set_xlim(-xmax * 0.04, xmax * 1.10)
    ax_b.set_ylim(-sr_max * 0.05, sr_max * 1.18)
    ax_b.set_xlabel("Cap-violation rate over body-slots (%)")
    ax_b.set_ylabel("Mean sum-rate (Gbps)")
    ax_b.set_title("(b) Sum-rate vs. compliance")
    ax_b.legend(loc="upper right", frameon=False, fontsize=7,
                handletextpad=0.4, borderaxespad=0.3)
    ax_b.grid(True, alpha=0.3)

    fig.tight_layout()
    save_both(fig, OUT_DIR / "hero_binding")
    plt.close(fig)


def make_pose_info(stats_o, stats_i, stats_t):
    """Two-panel: cap-violation rate and mean sum-rate vs pose source.
    Pose source modulates compliance at sub-percent scale; rate is
    saturated at the MCS cap across all three sources, so both panels
    use the same y-axis units."""
    sources = ["Oracle", r"IMU $4^\circ$", "T-pose"]
    s_list = [stats_o["multibody_ecbf"], stats_i["multibody_ecbf"], stats_t["multibody_ecbf"]]
    viol = [s["viol_pct"] for s in s_list]
    sr = [s["mean_sr_gbps"] for s in s_list]

    fig, axes = plt.subplots(
        1, 2, figsize=fig_size_ieee(columns=2, aspect=0.42),
    )
    x = np.arange(3)
    # Colour-code per pose source so the same source has the same colour across
    # both panels: oracle = blue, IMU 4° = green, T-pose = red.
    pose_colors = ["#2166ac", "#2ca02c", "#b2182b"]

    axes[0].bar(x, viol, color=pose_colors, alpha=0.85, edgecolor="k", lw=0.4)
    axes[0].set_xticks(x); axes[0].set_xticklabels(sources)
    axes[0].set_ylabel("Cap-violation rate (%)")
    axes[0].set_title("(a) Compliance vs pose source")
    axes[0].set_ylim(0, max(viol) * 1.30 + 0.05)
    for xi, v in zip(x, viol):
        axes[0].text(xi, v + max(viol) * 0.04, f"{v:.2f}%", ha="center", fontsize=8)
    axes[0].grid(True, alpha=0.3, axis="y")

    axes[1].bar(x, sr, color=pose_colors, alpha=0.85, edgecolor="k", lw=0.4)
    axes[1].set_xticks(x); axes[1].set_xticklabels(sources)
    axes[1].set_ylabel("Mean sum-rate (Gbps)")
    axes[1].set_title("(b) Throughput at MCS28 cap")
    axes[1].set_ylim(0, max(sr) * 1.30 + 0.05)
    for xi, v in zip(x, sr):
        axes[1].text(xi, v + max(sr) * 0.04, f"{v:.2f}", ha="center", fontsize=8)
    axes[1].grid(True, alpha=0.3, axis="y")
    # Reference line at MCS28 sum-cap. Place text inside the axes margin
    # so it doesn't get clipped on tight figure layouts.
    axes[1].axhline(74.0, color="k", ls=":", lw=0.7, alpha=0.5)
    axes[1].text(0.02, 74.0 / (max(sr) * 1.30), "MCS28 cap",
                 transform=axes[1].transAxes,
                 fontsize=7, va="bottom", ha="left", alpha=0.6)

    fig.tight_layout()
    save_both(fig, OUT_DIR / "pose_info_gain")
    plt.close(fig)


def _imu_sweep_real_data():
    """Find bind3v_v4_imu{N}.npz files (or bind5min_v3) and return
    (sigma_arr, viol, sr, fb). Returns None if fewer than 2 sigma points."""
    pts = {}
    for sigma in [0, 1, 2, 4, 8, 16]:
        tag = "oracle" if sigma == 0 else f"imu{sigma}"
        cands = []
        for prefix in ["bind3v_v8_", "bind3v_v7_", "bind3v_v4_", "bind5min_v3_"]:
            cands.extend(NPZ_DIR.glob(f"plaza_run_seed42_*{prefix}{tag}.npz"))
            if cands:
                break
        if not cands:
            continue
        z = np.load(cands[0], allow_pickle=True)
        pn = [str(s) for s in z["precoder_names"]]
        i = pn.index("multibody_ecbf") if sigma > 0 else pn.index("oracle")
        v = float(z["violation"][:, :, i].mean()) * 100
        s = float(z["sumrate"][:, i].mean()) / 1e9
        fb = float(z["infeasible"][:, i].mean()) * 100
        pts[float(sigma)] = (v, s, fb)
    if len(pts) < 2:
        return None
    sigmas = np.array(sorted(pts))
    viol = np.array([pts[s][0] for s in sigmas])
    sr = np.array([pts[s][1] for s in sigmas])
    fb = np.array([pts[s][2] for s in sigmas])
    return sigmas, viol, sr, fb


def make_imu_sweep(stats_o, stats_i, stats_t):
    """Plot real σ-sweep if available; else logistic interpolation between
    oracle (σ=0), IMU (σ=4), T-pose envelope (σ=∞)."""
    real = _imu_sweep_real_data()

    fig, ax_v = plt.subplots(figsize=fig_size_ieee(columns=1, aspect=0.78))
    ax_s = ax_v.twinx()
    ax_v.grid(True, alpha=0.3)

    s0, s4, sT = stats_o["multibody_ecbf"], stats_i["multibody_ecbf"], stats_t["multibody_ecbf"]
    tpose_v = sT["viol_pct"]; tpose_sr = sT["mean_sr_gbps"]

    if real is not None:
        sigmas, viol, sr, fb = real
        ax_v.plot(sigmas, viol, color="#b2182b", marker="o", lw=1.6,
                  label="Cap-violation (%)")
        ax_s.plot(sigmas, sr, color="#2ca02c", marker="s", lw=1.6, ls="--",
                  label="Sum-rate (Gbps)")
        ax_v.set_xlim(-0.5, max(sigmas) * 1.05 + 0.5)
        title_suffix = f"({len(sigmas)} measured points)"
    else:
        # Anchor logistic blend on σ=0, σ=4, σ→∞
        sigma = np.linspace(0.0, 18.0, 100)
        ratio = (s4["viol_pct"] - s0["viol_pct"]) / max(tpose_v - s0["viol_pct"], 1e-9)
        ratio = float(np.clip(ratio, 1e-6, 1 - 1e-6))
        sigma_half = -4.0 / np.log(1.0 - ratio)
        w = 1 - np.exp(-sigma / sigma_half)
        viol_curve = s0["viol_pct"] + (tpose_v - s0["viol_pct"]) * w
        sr_curve = s0["mean_sr_gbps"] + (tpose_sr - s0["mean_sr_gbps"]) * w
        ax_v.plot(sigma, viol_curve, color="#b2182b", lw=1.6,
                  label="Cap-violation (%)")
        ax_s.plot(sigma, sr_curve, color="#2ca02c", lw=1.6, ls="--",
                  label="Sum-rate (Gbps)")
        # Anchor markers
        ax_v.scatter([0.0, 4.0], [s0["viol_pct"], s4["viol_pct"]],
                     color="#b2182b", marker="o", s=40, zorder=4, edgecolor="k", linewidth=0.4)
        ax_s.scatter([0.0, 4.0], [s0["mean_sr_gbps"], s4["mean_sr_gbps"]],
                     color="#2ca02c", marker="s", s=40, zorder=4, edgecolor="k", linewidth=0.4)
        title_suffix = "(3 anchor points; logistic blend)"

    # T-pose asymptote band
    ax_v.axhline(tpose_v, color="#b2182b", ls=":", lw=1.0, alpha=0.7)
    ax_s.axhline(tpose_sr, color="#2ca02c", ls=":", lw=1.0, alpha=0.7)

    ax_v.set_xlabel(r"Per-joint attitude RMS $\sigma_{\mathrm{joint}}$ (deg)")
    ax_v.set_ylabel("Cap-violation rate (%)", color="#b2182b")
    ax_s.set_ylabel("Mean sum-rate (Gbps)", color="#2ca02c")
    ax_v.tick_params(axis="y", labelcolor="#b2182b")
    ax_s.tick_params(axis="y", labelcolor="#2ca02c")
    ax_v.set_title(f"IMU sensitivity {title_suffix}", fontsize=9)
    # Compose ymax from the envelope and any sweep-curve maxima so all
    # markers/lines stay on-axis.
    if real is not None:
        v_top = max(tpose_v, float(real[1].max()), float(s4["viol_pct"]))
        s_top = max(tpose_sr, float(real[2].max()), s4["mean_sr_gbps"])
        s_bot = min(s0["mean_sr_gbps"], float(real[2].min()), s4["mean_sr_gbps"])
    else:
        v_top, s_top = tpose_v, max(tpose_sr, s4["mean_sr_gbps"])
        s_bot = s0["mean_sr_gbps"]
    ax_v.set_ylim(-0.05 * max(v_top, 0.1), v_top * 1.20 + 0.05)
    ax_s.set_ylim(s_bot * 0.9, s_top * 1.15 + 0.05)
    ax_v.text(ax_v.get_xlim()[1] * 0.97, tpose_v, " T-pose env.",
              ha="right", va="bottom", color="#b2182b", fontsize=7, alpha=0.85)

    fig.tight_layout()
    save_both(fig, OUT_DIR / "imu_sweep")
    plt.close(fig)


def make_per_tier_breakdown(npz_path):
    """Per-tier (A/B/C) violation rate for each precoder in the K=25
    regime sweep. Visualises the sensing-pipeline-floor finding: tier-A
    and tier-B carry zero violations under all compliance-aware
    precoders; tier-C carries the floor due to undetected bystanders.

    Parameters
    ----------
    npz_path : Path
        regimeK25_v7 (or v8) NPZ with the new ``zf_proj_proposed`` column.
    """
    import matplotlib.pyplot as _plt
    import numpy as _np
    z = _np.load(npz_path, allow_pickle=True)
    pn = [str(s) for s in z["precoder_names"]]
    tiers = _np.asarray(z["tier"], dtype=int)
    TIER_LABEL = {0: "A (served)", 1: "B (cooperating)", 2: "C (sensed)"}
    fig, ax = _plt.subplots(figsize=fig_size_ieee(columns=1, aspect=0.78))

    bar_set = ["zf", "zf_proj_proposed", "multibody_ecbf"]
    bar_disp = {"zf": "ZF (raw)",
                "zf_proj_proposed": "ZF + proj (deploy)",
                "multibody_ecbf": "ECBF (deploy)"}
    bar_colors = {"zf": "#ef8a62", "zf_proj_proposed": "#5fa55a",
                  "multibody_ecbf": "#2166ac"}
    if "zf_proj_proposed" not in pn:
        bar_set = ["zf", "zf_proj", "multibody_ecbf"]
        bar_disp["zf_proj_proposed"] = "ZF + proj (oracle)"
        bar_colors["zf_proj"] = "#2ca02c"

    n_groups = 3  # tier A, B, C
    n_bars = len(bar_set)
    width = 0.8 / n_bars
    x = _np.arange(n_groups)

    for j, name in enumerate(bar_set):
        if name not in pn:
            continue
        i = pn.index(name)
        viols = []
        for t in range(3):
            mask = tiers == t
            if mask.sum() == 0:
                viols.append(0)
            else:
                viols.append(float(z["violation"][:, mask, i].mean()) * 100)
        offset = (j - (n_bars - 1) / 2) * width
        ax.bar(x + offset, viols, width,
               label=bar_disp.get(name, name),
               color=bar_colors.get(name, "#999999"),
               alpha=0.9, edgecolor="k", lw=0.4)
        for xi, v in zip(x + offset, viols):
            if v > 0.5:
                ax.text(xi, v + 0.5, f"{v:.1f}", ha="center", va="bottom",
                        fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels([TIER_LABEL[t] for t in range(3)], fontsize=8)
    ax.set_ylabel("Cap-violation rate (%)")
    ax.set_title(r"Per-tier violation, $K=25$ regime", fontsize=9)
    ax.legend(loc="upper left", frameon=False, fontsize=7)
    ax.grid(True, alpha=0.3, axis="y")
    fig.tight_layout()
    save_both(fig, OUT_DIR / "per_tier_breakdown")
    _plt.close(fig)


def make_chronic(z_imu, dt_s=None):
    """ECDF of body-integrated absorbed energy as a fraction of the chronic
    RL budget (= L_RL × duration), one curve per precoder. Shows that
    unconstrained ZF/MRT push many bodies past the chronic cap, while the
    proposed primal-projected precoder keeps every body well below."""
    pn = [str(s) for s in z_imu["precoder_names"]]
    p_abs = z_imu["p_abs"]  # (T, B, P)
    if dt_s is None:
        dt_s = float(z_imu["dt_s"]) if "dt_s" in z_imu.files else 1.0 / 30.0
    duration_s = p_abs.shape[0] * dt_s
    max_compliant_J = L_RL * duration_s

    fig, ax = plt.subplots(figsize=fig_size_ieee(columns=1, aspect=0.78))
    fracs_max = 0.0
    chronic_set = ["mrt", "zf", "wc_backoff",
                   "zf_proj_proposed" if "zf_proj_proposed" in pn else "zf_proj",
                   "multibody_ecbf"]
    for name in chronic_set:
        if name not in pn:
            continue
        i = pn.index(name)
        energy_J = p_abs[:, :, i].sum(axis=0) * dt_s  # per-body
        frac = energy_J / max_compliant_J
        x = np.sort(np.maximum(frac, 1e-4))
        y = np.arange(1, len(x) + 1) / len(x)
        disp = PRECODER_DISPLAY[name]
        if name == "zf_proj_proposed":
            disp = "ZF + proj"
        ax.plot(x, y, color=PRECODER_COLORS[name], lw=1.6,
                label=f"{disp} (med $={np.median(frac):.2f}$)")
        fracs_max = max(fracs_max, float(frac.max()))

    ax.axvline(1.0, color="k", ls="--", lw=1.0, alpha=0.6)
    ax.axvspan(1.0, max(fracs_max * 1.1, 5.0), alpha=0.08, color="#b2182b", lw=0)
    ax.text(1.05, 0.05, "exceeds chronic\nRL budget", color="#b2182b",
            fontsize=7, va="bottom", ha="left")
    ax.set_xscale("log")
    ax.set_xlim(1e-2, max(fracs_max * 1.2, 5.0))
    ax.set_ylim(0, 1.005)
    ax.set_xlabel(f"Body-integrated energy / ($L_{{\\mathrm{{RL}}}}\\!\\cdot\\!{duration_s:.0f}\\,$s)")
    ax.set_ylabel("ECDF over bodies")
    ax.legend(loc="upper left", frameon=False, fontsize=7)
    ax.grid(True, alpha=0.3, which="both")
    fig.tight_layout()
    save_both(fig, OUT_DIR / "chronic_dose")
    plt.close(fig)


def make_spatial(z_oracle, z_imu):
    """Per-cell mean P_abs / L_RL on a tight crop, log color, side-by-side
    ZF (using oracle pose) vs ZF + primal projection (IMU pose).
    Empty cells are masked."""
    pn = [str(s) for s in z_oracle["precoder_names"]]
    pn_i = [str(s) for s in z_imu["precoder_names"]]
    zf_idx = pn.index("zf")
    # Prefer the deployable variant for the right-panel heatmap; fall back
    # to the oracle variant or to the dual ascent.
    if "zf_proj_proposed" in pn_i:
        prop_idx = pn_i.index("zf_proj_proposed")
    elif "zf_proj" in pn_i:
        prop_idx = pn_i.index("zf_proj")
    else:
        prop_idx = pn_i.index("multibody_ecbf")

    pos_o = z_oracle["body_positions"]
    pos_i = z_imu["body_positions"]
    pa_zf = z_oracle["p_abs"][:, :, zf_idx]
    pa_pr = z_imu["p_abs"][:, :, prop_idx]

    # Tight crop: 5%-95% percentile of body positions
    xy_all = np.concatenate([pos_o[..., :2].reshape(-1, 2),
                             pos_i[..., :2].reshape(-1, 2)], axis=0)
    xlo, xhi = np.percentile(xy_all[:, 0], [2, 98])
    ylo, yhi = np.percentile(xy_all[:, 1], [2, 98])
    # Pad a bit
    xpad = (xhi - xlo) * 0.05
    ypad = (yhi - ylo) * 0.05
    xlo -= xpad; xhi += xpad; ylo -= ypad; yhi += ypad

    cell = 2.0  # m
    xb = np.arange(xlo, xhi + cell, cell)
    yb = np.arange(ylo, yhi + cell, cell)

    def heat(pos, vals):
        xy = pos[..., :2].reshape(-1, 2)
        v = vals.reshape(-1)
        sums, _, _ = np.histogram2d(xy[:, 0], xy[:, 1], bins=[xb, yb], weights=v)
        cnt, _, _ = np.histogram2d(xy[:, 0], xy[:, 1], bins=[xb, yb])
        h = np.full_like(sums, np.nan)
        nz = cnt > 0
        h[nz] = sums[nz] / cnt[nz] / L_RL
        return h

    h_zf = heat(pos_o, pa_zf)
    h_pr = heat(pos_i, pa_pr)

    # Log color scale, common to both panels.
    vmin = max(1e-3, min(np.nanmin(h_zf[h_zf > 0]) if (h_zf > 0).any() else 1e-3,
                         np.nanmin(h_pr[h_pr > 0]) if (h_pr > 0).any() else 1e-3))
    vmax = max(np.nanmax(h_zf), np.nanmax(h_pr), 1.0)
    norm = mcolors.LogNorm(vmin=vmin, vmax=vmax)

    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad(color="#f0f0f0")  # empty cells = light gray

    fig, axes = plt.subplots(
        1, 2, figsize=fig_size_ieee(columns=2, aspect=0.42), sharey=True,
    )
    right_label = "ZF + proj (IMU pose)"
    if "zf_proj_proposed" in pn_i:
        right_label = "ZF + proj (deployable, IMU pose)"
    for ax, h, ttl in zip(axes, [h_zf, h_pr], ["ZF (unconstrained)", right_label]):
        masked = np.ma.masked_invalid(h.T)
        im = ax.imshow(masked, origin="lower",
                       extent=[xb[0], xb[-1], yb[0], yb[-1]],
                       cmap=cmap, norm=norm, aspect="equal",
                       interpolation="nearest")
        # Contour at L_RL = 1
        try:
            xc = (xb[:-1] + xb[1:]) / 2
            yc = (yb[:-1] + yb[1:]) / 2
            ax.contour(xc, yc, np.where(np.isnan(h.T), 0, h.T),
                       levels=[1.0], colors="white", linewidths=1.0)
        except Exception:
            pass
        ax.set_xlabel("$x$ (m)")
        ax.set_title(ttl)
    axes[0].set_ylabel("$y$ (m)")
    cbar = fig.colorbar(im, ax=axes, fraction=0.04, pad=0.02)
    cbar.set_label(r"Per-cell mean $P_{\mathrm{abs}}/L_{\mathrm{RL}}$ (log)")
    save_both(fig, OUT_DIR / "spatial_heatmap")
    plt.close(fig)


def write_table(stats_o, stats_i, stats_t):
    lines = ["% Auto-generated by regen_v3_figures.py"]
    s = stats_o["multibody_ecbf"]
    lines.append(rf"Oracle (true pose) & ${s['mean_sr_gbps']:.2f}\,$Gbps & "
                 rf"${s['viol_pct']:.2f}\,\%$ & ${s['fallback_pct']:.0f}\,\%$ \\")
    s = stats_i["multibody_ecbf"]
    lines.append(rf"Virtual IMU ($4^\circ$) & ${s['mean_sr_gbps']:.2f}\,$Gbps & "
                 rf"${s['viol_pct']:.2f}\,\%$ & ${s['fallback_pct']:.0f}\,\%$ \\")
    s = stats_t["multibody_ecbf"]
    lines.append(rf"T-pose fallback & ${s['mean_sr_gbps']:.2f}\,$Gbps & "
                 rf"${s['viol_pct']:.2f}\,\%$ & ${s['fallback_pct']:.0f}\,\%$ \\")
    out = "\n".join(lines)
    (OUT_DIR / "table_pose_triage.txt").write_text(out + "\n")
    print(out)


def main():
    apply_monograph_style(mode="png")
    print("=== Loading NPZs ===")
    z_oracle, _ = _augment_with_zf_proj(load("oracle"))
    z_imu, _ = _augment_with_zf_proj(load("imu4"))
    z_tpose, _ = _augment_with_zf_proj(load("tpose"))

    s_o = precoder_stats(z_oracle)
    s_i = precoder_stats(z_imu)
    s_t = precoder_stats(z_tpose)

    for tag, s in [("oracle", s_o), ("imu", s_i), ("tpose", s_t)]:
        print(f"\n--- {tag} ---")
        for n, d in s.items():
            print(f"  {n:18s} viol={d['viol_pct']:5.2f}% sr={d['mean_sr_gbps']:6.2f}Gbps "
                  f"fallback={d['fallback_pct']:5.1f}% p99={d['p99']:.2e}")

    print("\n=== Generating figures ===")
    make_hero(z_imu)
    make_pose_info(s_o, s_i, s_t)
    make_imu_sweep(s_o, s_i, s_t)
    make_chronic(z_imu)
    make_spatial(z_oracle, z_imu)
    # Per-tier breakdown using the K=25 regime NPZ (the deployable
    # variant lives there; fall back to bind5min if unavailable).
    regime_k25 = list(NPZ_DIR.glob("plaza_run_seed42_*regimeK25_v7.npz"))
    if regime_k25:
        make_per_tier_breakdown(regime_k25[0])
        print("  per_tier_breakdown.pdf <- regimeK25_v7.npz")

    print("\n=== Table II body ===")
    write_table(s_o, s_i, s_t)


if __name__ == "__main__":
    main()
