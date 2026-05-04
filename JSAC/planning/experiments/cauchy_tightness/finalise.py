"""Post-processor: regenerate plot + summary + README block.

Two modes:
- default (fast): load `ratios.npz`, replot, and write README + summary.
- `--resweep`: load `q_and_a.npz` (Q matrices + a_los vectors saved by
  run_tightness.py) and redo the precoder sweep without recomputing Q.
  Use this when iterating on precoder ensemble logic in run_tightness.py.

Lets us iterate on the figure without re-running the ~7-minute Q sweep.
Uses the same rendering helpers as run_tightness.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from aegis.geometry.mesh import BodyMesh  # noqa: E402
from aegis.mimo.array import AntennaArray  # noqa: E402
from aegis.tissue.dielectric import TissueModel  # noqa: E402
from run_tightness import (  # noqa: E402
    BROADSIDE,
    BS_CENTER,
    CHANNEL_MODELS,
    D,
    ENSEMBLE_LABELS,
    ENSEMBLE_SIZES,
    FREQ_HZ,
    N_BODIES,
    N_H,
    N_V,
    PHANTOMS,
    STOCHASTIC_SUBPATHS,
    TX_POWER_W,
    BodyAnalytics,
    compute_body_analytics,
    evaluate_ratios,
    plot_panel,
)


def _resweep_from_qa() -> dict[str, dict[str, np.ndarray]]:
    """Re-run the precoder sweep using saved Q + a_los matrices."""
    qa = np.load(_HERE / "q_and_a.npz")
    array = AntennaArray.upa(
        n_h=N_H,
        n_v=N_V,
        d_h=D,
        d_v=D,
        center=BS_CENTER,
        broadside=BROADSIDE,
        element_pattern="patch",
    )
    analytics: dict[str, BodyAnalytics] = {}
    for name, path in PHANTOMS:
        analytics[name] = compute_body_analytics(BodyMesh.load(path))

    ratios_flat: dict[str, dict[str, list[np.ndarray]]] = {
        ch: {ens: [] for ens in ENSEMBLE_SIZES} for ch in CHANNEL_MODELS
    }
    seed_counter = 0
    for body_name, _ in PHANTOMS:
        for channel in CHANNEL_MODELS:
            for body_idx in range(N_BODIES):
                Q = qa[f"Q__{body_name}__{channel}__{body_idx:03d}"]
                a_los = qa[f"a__{body_name}__{channel}__{body_idx:03d}"]
                rng = np.random.default_rng(20_000 + seed_counter)
                seed_counter += 1
                ratios = evaluate_ratios(np.asarray(Q), np.asarray(a_los),
                                         analytics[body_name], array, rng)
                for ens, vals in ratios.items():
                    ratios_flat[channel][ens].append(vals)

    return {
        ch: {ens: np.concatenate(vals) if vals else np.array([])
             for ens, vals in ens_dict.items()}
        for ch, ens_dict in ratios_flat.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--resweep",
        action="store_true",
        help="re-run the precoder sweep from saved Q + a_los (slower; needed "
             "when precoder ensemble logic changes)",
    )
    args = parser.parse_args()

    out_dir = _HERE

    if args.resweep:
        print("re-sweeping precoders from q_and_a.npz ...")
        ratios_flat = _resweep_from_qa()
        # Persist re-swept ratios so subsequent default runs see the fresh
        # numbers.
        ratio_payload: dict[str, np.ndarray] = {}
        for channel, ens_dict in ratios_flat.items():
            for ensemble, vals in ens_dict.items():
                ratio_payload[f"ratio_db__{channel}__{ensemble}"] = vals
        np.savez(out_dir / "ratios.npz", **ratio_payload)
        print(f"updated {out_dir / 'ratios.npz'}")
    else:
        npz = np.load(out_dir / "ratios.npz")
        ratios_flat = {}
        for channel in CHANNEL_MODELS:
            ratios_flat[channel] = {}
            for ensemble in ENSEMBLE_SIZES:
                key = f"ratio_db__{channel}__{ensemble}"
                ratios_flat[channel][ensemble] = (
                    np.asarray(npz[key]) if key in npz.files else np.array([])
                )

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
    plot_panel(axes[0], ratios_flat["specular"], "(a) plaza specular (LOS + ground + 2 facades)")
    plot_panel(
        axes[1],
        ratios_flat["stochastic"],
        f"(b) 3GPP UMa-LOS (12 clusters x {STOCHASTIC_SUBPATHS} subpaths)",
    )
    fig.suptitle(
        "Tightness of the rank-1 Cauchy operator bound (Theorem 2)\n"
        rf"$x^H Q x \leq T_0 (A_\mathrm{{ab}}/4) D_\mathrm{{max}} |a^H x|^2$, "
        rf"{len(PHANTOMS)} phantoms, {N_BODIES} positions each, 26 GHz, "
        rf"{N_H}x{N_V} UPA"
    )
    fig.tight_layout()
    fig.savefig(out_dir / "tightness.pdf")
    fig.savefig(out_dir / "tightness.png", dpi=180)
    plt.close(fig)
    print(f"wrote {out_dir / 'tightness.pdf'}")
    print(f"wrote {out_dir / 'tightness.png'}")

    # Summary stats
    summary: dict = {"by_channel": {}, "constants": {}, "body_analytics": {}}
    for channel, ens_dict in ratios_flat.items():
        summary["by_channel"][channel] = {}
        for ensemble, vals in ens_dict.items():
            if vals.size == 0:
                continue
            summary["by_channel"][channel][ensemble] = {
                "n": int(vals.size),
                "mean_db": float(np.mean(vals)),
                "median_db": float(np.median(vals)),
                "p10_db": float(np.percentile(vals, 10)),
                "p90_db": float(np.percentile(vals, 90)),
                "min_db": float(np.min(vals)),
                "max_db": float(np.max(vals)),
                "fraction_violating": float(np.mean(vals > 0)),
            }

    # Body analytics (recompute from STLs, cheap)
    for name, path in PHANTOMS:
        b = BodyMesh.load(path)
        anal = compute_body_analytics(b)
        summary["body_analytics"][name] = {
            "total_area_m2": float(anal.total_area),
            "A_ab_over_4_m2": float(anal.A_ab_over_4),
            "D_max": float(anal.D_max),
        }

    # Tissue
    try:
        tissue = TissueModel.from_database("Skin", FREQ_HZ)
    except Exception:  # noqa: BLE001
        tissue = TissueModel("Skin 26 GHz", eps_r=17.4, sigma=23.5, freq_hz=FREQ_HZ)
    summary["constants"] = {
        "freq_hz": FREQ_HZ,
        "T_0": float(tissue.T0),
        "tissue": tissue.name,
        "tissue_eps_r": float(tissue.eps_r),
        "tissue_sigma": float(tissue.sigma),
        "tx_power_w": TX_POWER_W,
        "n_h": N_H,
        "n_v": N_V,
        "phantoms": [p[0] for p in PHANTOMS],
        "n_positions_per_phantom": N_BODIES,
    }

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"wrote {out_dir / 'summary.json'}")

    # Console summary
    print("\n=== summary: 10 log10(LHS/RHS) [dB] by channel x ensemble ===")
    print("    (>0 dB means bound is violated)\n")
    for channel in CHANNEL_MODELS:
        print(f"  channel = {channel}")
        for ensemble in ENSEMBLE_SIZES:
            s = summary["by_channel"][channel].get(ensemble)
            if s is None:
                continue
            print(
                f"    {ensemble:10s}  n={s['n']:5d}  "
                f"med={s['median_db']:+7.2f}  p10={s['p10_db']:+7.2f}  "
                f"p90={s['p90_db']:+7.2f}  max={s['max_db']:+7.2f}  "
                f"frac>0={s['fraction_violating']:.2%}"
            )
        print()

    # Auto-fill README results section
    readme = out_dir / "README.md"
    text = readme.read_text()
    block_lines = [
        "<!-- BEGIN AUTO-RESULTS -->",
        "",
        "**Per-body geometry constants** (`A_ab/4 = mean(A_perp)`, "
        "`D_max = max(A_perp) / mean(A_perp)`, "
        f"from {256} Fibonacci directions):",
        "",
        "| phantom | total area (m^2) | A_ab/4 (m^2) | D_max |",
        "|---|---|---|---|",
    ]
    for name, _ in PHANTOMS:
        a = summary["body_analytics"][name]
        block_lines.append(
            f"| {name} | {a['total_area_m2']:.3f} | {a['A_ab_over_4_m2']:.4f} | {a['D_max']:.3f} |"
        )
    block_lines += [
        "",
        f"**Tissue constants:** Skin at 26 GHz, "
        f"`eps_r = {summary['constants']['tissue_eps_r']:.2f}`, "
        f"`sigma = {summary['constants']['tissue_sigma']:.2f}` S/m, "
        f"`T_0 = {summary['constants']['T_0']:.4f}` (normal-incidence "
        "transmission).",
        "",
        "**Bound tightness (10 log10(LHS/RHS) in dB; positive means bound "
        "violated, i.e. the actual `x^H Q x` exceeds the rank-1 Cauchy "
        "ceiling).**",
        "",
    ]
    for channel in CHANNEL_MODELS:
        title = (
            "Plaza specular (LOS + ground + 2 facades)"
            if channel == "specular"
            else f"3GPP UMa-LOS (12 clusters x {STOCHASTIC_SUBPATHS} subpaths)"
        )
        block_lines.append(f"_{title}_")
        block_lines.append("")
        block_lines.append(
            "| ensemble | n | median dB | p10 dB | p90 dB | max dB | "
            "fraction > 0 dB |"
        )
        block_lines.append("|---|---|---|---|---|---|---|")
        for ensemble in ENSEMBLE_SIZES:
            s = summary["by_channel"][channel].get(ensemble)
            if s is None:
                continue
            block_lines.append(
                f"| {ENSEMBLE_LABELS[ensemble]} | {s['n']} | "
                f"{s['median_db']:+.2f} | {s['p10_db']:+.2f} | "
                f"{s['p90_db']:+.2f} | {s['max_db']:+.2f} | "
                f"{s['fraction_violating']:.0%} |"
            )
        block_lines.append("")

    block_lines.append(
        "**Key empirical findings.** The bound holds (negative dB) only for "
        "precoders concentrated near the body's LOS direction. For all "
        "other ensembles the bound is violated, often by tens of dB. The "
        "median violation depends strongly on multipath richness "
        "(plaza specular vs 3GPP UMa-LOS with 60 subpaths). See "
        "`tightness.{pdf,png}` for the CDFs."
    )
    block_lines.append("")
    block_lines.append("<!-- END AUTO-RESULTS -->")

    new_block = "\n".join(block_lines)
    start = "<!-- BEGIN AUTO-RESULTS -->"
    end = "<!-- END AUTO-RESULTS -->"
    if start in text and end in text:
        before, _, rest = text.partition(start)
        _, _, after = rest.partition(end)
        new_text = before + new_block + after
        readme.write_text(new_text)
        print(f"updated {readme}")
    else:
        print(f"WARN: AUTO-RESULTS markers not found in {readme}; "
              "appended block instead")
        readme.write_text(text + "\n\n" + new_block + "\n")


if __name__ == "__main__":
    main()
