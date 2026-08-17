"""Supplementary analyses of the current five-city first-material-interaction campaign.

Primary input is the authenticated multi-city result package

    outputs/roofline_campaign/current_five_city_first_material_interaction/
        current_five_city_first_material_interaction.json

produced under the ``first_material_interaction_v1`` transport contract: exact
direct, exact order-1 all-specular, and a stochastic next-event estimate of the
first diffuse interaction only, with 200,000 IID primary rays and 4,096 output
cells. Its five cities are Korenmarkt, Prague, Madrid, Mexico City and Tokyo
Hachiko, all on ``provider_corridor_v1`` routes, all with seeds 7 to 22 and looks
4, 8, 12, 16.

Secondary input is the pair of 64-replica campaign directories for Mexico City and
Tokyo. Those ran the older ``hybrid_max_bounces_v1`` contract, so they cannot
extend the current numbers, but their first 16 seeds are bit-identical to the
16-replica campaigns, which makes look 16 against look 64 a clean nested test of
whether 16 replicas are enough at a fixed route.

Nothing is written outside this directory, and every input path is read-only.
"""

from __future__ import annotations

import json
import pathlib

import matplotlib as mpl
import numpy as np

from _supplementary_common import DB, ecdf, save, setup_style

import matplotlib.pyplot as plt

PRODUCTION_ROOT = pathlib.Path("/home/user/aegis-exposure-body-path/papers/city-exposure-study/semantic_twin")
CAMPAIGN_ROOT = PRODUCTION_ROOT / "outputs" / "roofline_campaign"
RESULT_JSON = (
    CAMPAIGN_ROOT / "current_five_city_first_material_interaction" / "current_five_city_first_material_interaction.json"
)
REPLICA64 = {
    "Mexico": CAMPAIGN_ROOT / "mexico_zocalo_provider_corridor_v1_convergence64_cuda_iid",
    "Tokyo": CAMPAIGN_ROOT / "tokyo_hachiko_provider_corridor_v1_convergence64_cuda_iid",
}
REPLICA16 = {
    "Mexico": CAMPAIGN_ROOT / "mexico_zocalo_provider_corridor_v1_convergence_cuda_iid",
    "Tokyo": CAMPAIGN_ROOT / "tokyo_hachiko_provider_corridor_v1_convergence_cuda_iid",
}

CITY_ORDER = ("Korenmarkt", "Prague", "Madrid", "Mexico", "Tokyo")
CITY_LABEL = {
    "Korenmarkt": "Korenmarkt",
    "Prague": "Prague",
    "Madrid": "Madrid",
    "Mexico": "Mexico City",
    "Tokyo": "Tokyo Hachiko",
}
CITY_COLOUR = {
    "Korenmarkt": "#c0392b",
    "Prague": "#2471a3",
    "Madrid": "#e08214",
    "Mexico": "#117a3d",
    "Tokyo": "#7d3c98",
}
COMPONENTS = ("direct", "all_specular", "first_diffuse")
COMPONENT_LABEL = {
    "direct": "direct",
    "all_specular": "order-1 specular",
    "first_diffuse": "first diffuse",
    "total": "total",
}
COMPONENT_COLOUR = {
    "direct": "#1b1b1b",
    "all_specular": "#c0392b",
    "first_diffuse": "#2471a3",
    "total": "#117a3d",
}
LOOKS = (4, 8, 12, 16)
FLOOR_DB = -95.0  # plotting floor for the structurally zero components


def load_results() -> dict:
    return json.loads(RESULT_JSON.read_text())


def route_array(city: dict, key: str) -> np.ndarray:
    return np.array([point[key] for point in city["route"]], dtype=np.float64)


def component_transfer(city: dict, component: str) -> np.ndarray:
    return np.array(
        [point["component_raw_transfer_m_inv2"][component] for point in city["route"]],
        dtype=np.float64,
    )


def component_body(city: dict, component: str, metric: str) -> np.ndarray:
    return np.array([point["component_body"][component][metric] for point in city["route"]], dtype=np.float64)


def safe_db(values: np.ndarray, floor: float = FLOOR_DB) -> np.ndarray:
    """dB with a plotting floor, because zero-direct standpoints are structural."""
    out = np.full(values.shape, floor, dtype=np.float64)
    positive = values > 0.0
    out[positive] = 10.0 * np.log10(values[positive])
    return out


def masked_db(values: np.ndarray) -> np.ndarray:
    """dB with structural zeros left as gaps, so a line breaks instead of diving."""
    return safe_db(values, floor=np.nan)


def _specular_over_direct(city: dict) -> float:
    """Median specular-to-direct ratio in dB, over standpoints where both exist."""
    specular = component_transfer(city, "all_specular")
    direct = component_transfer(city, "direct")
    usable = (specular > 0.0) & (direct > 0.0)
    return float(np.median(10.0 * np.log10(specular[usable] / direct[usable])))


def load_shards(directory: pathlib.Path) -> tuple[np.ndarray, list[int], dict]:
    index = json.loads((directory / "checkpoint" / "index.json").read_text())
    stack = np.stack(
        [np.load(directory / "checkpoint" / entry["path"])["raw_transfer"] for entry in index["committed"]]
    )
    body = np.stack([np.load(directory / "checkpoint" / entry["path"])["body_metrics"] for entry in index["committed"]])
    return stack, [entry["seed"] for entry in index["committed"]], {"index": index, "body": body}


# --------------------------------------------------------------------------------------
# C1  Per-standpoint transfer profile, five cities
# --------------------------------------------------------------------------------------
def figure_route_profiles(results: dict, numbers: dict) -> None:
    fig, axes = plt.subplots(5, 1, figsize=(3.5, 7.4), sharex=False)
    for ax, name in zip(axes, CITY_ORDER):
        city = results["cities"][name]
        distance = route_array(city, "route_distance_m")
        total = component_transfer(city, "total")
        for component in ("total",) + COMPONENTS:
            values = component_transfer(city, component)
            ax.plot(
                distance,
                masked_db(values),
                color=COMPONENT_COLOUR[component],
                linestyle="-" if component in ("total", "direct") else "--",
                marker="." if name in ("Mexico", "Tokyo") else None,
                label=COMPONENT_LABEL[component],
            )
        zero_direct = np.array(city["tail_instability"]["zero_direct_standpoints"], dtype=int)
        if zero_direct.size:
            ax.plot(
                distance[zero_direct],
                masked_db(total)[zero_direct],
                linestyle="none",
                marker="v",
                color="#f0c419",
                markeredgecolor="#8a6d00",
                markeredgewidth=0.5,
                markersize=4.0,
                label="zero direct",
            )
        ax.set_ylabel(f"{CITY_LABEL[name]}\n" + r"$10\log_{10}D$ [dB]")
        numbers.setdefault("route_profiles", {})[name] = {
            "standpoints": int(distance.size),
            "route_span_m": float(distance.max()),
            "total_transfer_db_median": float(np.median(safe_db(total))),
            "total_transfer_db_span": float(np.ptp(safe_db(total))),
            "zero_direct_standpoints": zero_direct.tolist(),
            "specular_over_direct_db_median_where_both_positive": _specular_over_direct(city),
        }
    axes[-1].set_xlabel("route distance [m]")
    handles, labels = axes[3].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.925),
        handlelength=1.4,
        columnspacing=0.9,
        fontsize=5.8,
    )
    fig.align_ylabels(axes)
    fig.subplots_adjust(hspace=0.42, top=0.9)
    save(fig, "C1_five_city_route_profiles")


# --------------------------------------------------------------------------------------
# C2  Component share and multipath surplus
# --------------------------------------------------------------------------------------
def figure_component_share(results: dict, numbers: dict) -> None:
    fig, axes = plt.subplots(5, 1, figsize=(3.5, 7.0))
    for ax, name in zip(axes, CITY_ORDER):
        city = results["cities"][name]
        distance = route_array(city, "route_distance_m")
        total = component_transfer(city, "total")
        specular_share = 100.0 * component_transfer(city, "all_specular") / total
        diffuse_share = 100.0 * component_transfer(city, "first_diffuse") / total
        ax.stackplot(
            distance,
            specular_share,
            diffuse_share,
            colors=[COMPONENT_COLOUR["all_specular"], COMPONENT_COLOUR["first_diffuse"]],
            alpha=0.55,
            edgecolor="none",
            labels=["order-1 specular", "first diffuse"],
        )
        ax.set_ylim(0.0, 105.0)
        ax.set_ylabel(f"{CITY_LABEL[name]}\nshare of total [%]")
        twin = ax.twinx()
        surplus = route_array(city, "multipath_surplus_db")
        finite = np.isfinite(surplus)
        twin.plot(distance[finite], surplus[finite], color="#117a3d", linewidth=1.0)
        twin.set_ylabel("surplus [dB]", color="#117a3d", labelpad=1)
        twin.tick_params(axis="y", colors="#117a3d")
        twin.grid(False)
        numbers.setdefault("component_share", {})[name] = {
            "specular_share_percent_median": float(np.median(specular_share)),
            "specular_share_percent_min": float(specular_share.min()),
            "specular_share_percent_max": float(specular_share.max()),
            "diffuse_share_percent_median": float(np.median(diffuse_share)),
            "diffuse_share_percent_max": float(diffuse_share.max()),
            "surplus_db_median_finite": float(np.median(surplus[finite])) if finite.any() else None,
            "surplus_db_max_finite": float(surplus[finite].max()) if finite.any() else None,
            "surplus_undefined_standpoints": int((~finite).sum()),
            "shadowed_share_of_route_percent": float(100.0 * np.mean(specular_share + diffuse_share > 50.0)),
        }
    axes[0].legend(loc="center left", handlelength=1.4, fontsize=5.6)
    axes[-1].set_xlabel("route distance [m]")
    fig.align_ylabels(axes)
    fig.subplots_adjust(hspace=0.45)
    save(fig, "C2_five_city_component_share")


# --------------------------------------------------------------------------------------
# C3  Cross-city fixed-route distributions
# --------------------------------------------------------------------------------------
def figure_cross_city(results: dict, numbers: dict) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(3.5, 6.4))
    surplus_axis, sar_axis, peak_axis, quantile_axis = axes
    for name in CITY_ORDER:
        city = results["cities"][name]
        colour = CITY_COLOUR[name]
        surplus = route_array(city, "multipath_surplus_db")
        finite = np.isfinite(surplus)
        x, y = ecdf(surplus[finite])
        surplus_axis.step(x, y, where="post", color=colour, label=CITY_LABEL[name])
        x, y = ecdf(route_array(city, "wbsar"))
        sar_axis.step(x, y, where="post", color=colour)
        ratio = route_array(city, "peak_sab_ensemble_field") / route_array(city, "mean_sab")
        x, y = ecdf(ratio)
        peak_axis.step(x, y, where="post", color=colour)
        numbers.setdefault("cross_city", {})[name] = {
            "standpoints": len(city["route"]),
            "surplus_db_median_over_finite_points": float(np.median(surplus[finite])),
            "surplus_finite_points": int(finite.sum()),
            "wbsar_median": float(np.median(route_array(city, "wbsar"))),
            "wbsar_min": float(route_array(city, "wbsar").min()),
            "wbsar_max": float(route_array(city, "wbsar").max()),
            "wbsar_decades_spanned": float(
                np.log10(route_array(city, "wbsar").max() / route_array(city, "wbsar").min())
            ),
            "peak_over_mean_median": float(np.median(ratio)),
            "peak_over_mean_max": float(ratio.max()),
        }
    positions = np.arange(len(CITY_ORDER), dtype=np.float64)
    for offset, quantile, marker in ((-0.22, "q10", "v"), (0.0, "q50", "o"), (0.22, "q90", "^")):
        estimates, lower, upper = [], [], []
        for name in CITY_ORDER:
            entry = results["cities"][name]["route_quantile_uncertainty"]["quantiles"]["wbsar"][quantile]
            estimates.append(entry["estimate"])
            lower.append(entry["estimate"] - entry["ci95_percentile"][0])
            upper.append(entry["ci95_percentile"][1] - entry["estimate"])
            numbers.setdefault("bootstrap_wbsar", {}).setdefault(name, {})[quantile] = {
                "estimate": float(entry["estimate"]),
                "ci95_low": float(entry["ci95_percentile"][0]),
                "ci95_high": float(entry["ci95_percentile"][1]),
                "ci95_width_relative_percent": float(
                    100.0 * (entry["ci95_percentile"][1] - entry["ci95_percentile"][0]) / entry["estimate"]
                ),
            }
        quantile_axis.errorbar(
            positions + offset,
            estimates,
            yerr=[lower, upper],
            linestyle="none",
            marker=marker,
            markersize=3.0,
            capsize=1.6,
            elinewidth=0.7,
            color="#1b1b1b" if quantile == "q50" else "#7f8c8d",
            label=f"route {quantile}",
        )
    surplus_axis.set_xlabel("multipath surplus [dB]")
    sar_axis.set_xlabel(r"normalised wbSAR [m$^2$ kg$^{-1}$]")
    sar_axis.set_xscale("log")
    peak_axis.set_xlabel(r"peak $S_{ab}$ of mean field / area-mean $S_{ab}$")
    for ax in (surplus_axis, sar_axis, peak_axis):
        ax.set_ylabel("fixed-route ECDF")
        ax.set_ylim(0.0, 1.0)
    quantile_axis.set_yscale("log")
    quantile_axis.set_xticks(positions)
    quantile_axis.set_xticklabels([CITY_LABEL[name] for name in CITY_ORDER], rotation=18, ha="right")
    quantile_axis.set_ylabel(r"wbSAR [m$^2$ kg$^{-1}$]")
    quantile_axis.legend(loc="lower left", handlelength=1.2, ncol=3, fontsize=5.6)
    handles, labels = surplus_axis.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.99),
        handlelength=1.2,
        columnspacing=0.8,
        fontsize=5.8,
    )
    surplus_axis.set_title("Fixed-route ECDFs over registered standpoints, not population CDFs", fontsize=6.2, pad=4)
    fig.subplots_adjust(hspace=0.78, top=0.895)
    save(fig, "C3_five_city_distributions")


# --------------------------------------------------------------------------------------
# C4  Convergence and tail instability
# --------------------------------------------------------------------------------------
def figure_convergence(results: dict, numbers: dict) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(3.5, 5.2))
    se_axis, shift_axis, tail_axis = axes
    for name in CITY_ORDER:
        city = results["cities"][name]
        colour = CITY_COLOUR[name]
        looks, p90, maximum = [], [], []
        for entry in city["convergence"]["standard_error"]:
            looks.append(entry["replicas"])
            p90.append(entry["total_transfer"]["p90_db_delta_approximation"])
            maximum.append(entry["total_transfer"]["maximum_db_delta_approximation"])
        se_axis.plot(looks, p90, "-", marker="o", color=colour, label=CITY_LABEL[name])
        se_axis.plot(looks, maximum, ":", marker="s", color=colour, alpha=0.7)
        boundaries, shifts, tail_max, route_q50 = [], [], [], []
        for entry in city["convergence"]["look_to_look"]:
            boundaries.append(entry["to_replicas"])
            shifts.append(entry["total_transfer"]["p90_abs_db"])
        for entry in city["tail_instability"]["look_to_look"]:
            tail_max.append(entry["final_lower_decile_points"]["maximum_abs_db"])
            route_q50.append(entry["route_quantile_abs_change_db"]["q50"])
        shift_axis.plot(boundaries, shifts, "-", marker="o", color=colour)
        tail_axis.plot(boundaries, tail_max, "-", marker="o", color=colour)
        tail_axis.plot(boundaries, route_q50, "--", marker="s", color=colour, alpha=0.7)
        numbers.setdefault("convergence", {})[name] = {
            "se_db_p90_by_look": {str(look): float(value) for look, value in zip(looks, p90)},
            "se_db_max_by_look": {str(look): float(value) for look, value in zip(looks, maximum)},
            "look_to_look_p90_abs_db": {str(boundary): float(value) for boundary, value in zip(boundaries, shifts)},
            "look_to_look_max_abs_db_12_to_16": float(
                city["convergence"]["look_to_look"][-1]["total_transfer"]["maximum_abs_db"]
            ),
            "tail_lower_decile_max_abs_db_12_to_16": float(tail_max[-1]),
            "route_q50_abs_change_db_12_to_16": float(route_q50[-1]),
            "tail_over_q50_ratio_12_to_16": float(tail_max[-1] / route_q50[-1]),
            "tail_status": city["tail_instability"]["status"],
        }
    se_axis.set_yscale("log")
    shift_axis.set_yscale("log")
    tail_axis.set_yscale("log")
    se_axis.set_xticks(LOOKS)
    shift_axis.set_xticks(LOOKS[1:])
    tail_axis.set_xticks(LOOKS[1:])
    se_axis.set_ylabel("SE of total transfer [dB]")
    se_axis.set_xlabel("seeds in look")
    se_axis.set_title("solid: p90 across standpoints, dotted: maximum", fontsize=6.0, pad=3)
    shift_axis.set_ylabel(r"p90 $|$look shift$|$ [dB]")
    shift_axis.set_xlabel("look upper seed count")
    tail_axis.set_ylabel(r"$|$look shift$|$ [dB]")
    tail_axis.set_xlabel("look upper seed count")
    tail_axis.set_title("solid: worst lower-decile standpoint, dashed: route q50", fontsize=6.0, pad=3)
    handles, labels = se_axis.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        ncol=5,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.955),
        handlelength=1.2,
        columnspacing=0.8,
        fontsize=5.8,
    )
    fig.subplots_adjust(hspace=0.78, top=0.9)
    save(fig, "C4_five_city_convergence")


# --------------------------------------------------------------------------------------
# C5  Standpoints with zero direct transport
# --------------------------------------------------------------------------------------
def figure_zero_direct(results: dict, numbers: dict) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 3.8))
    for ax, name in zip(axes, ("Mexico", "Tokyo")):
        city = results["cities"][name]
        zero_direct = set(city["tail_instability"]["zero_direct_standpoints"])
        standpoints = np.arange(len(city["route"]))
        specular = component_transfer(city, "all_specular")
        diffuse = component_transfer(city, "first_diffuse")
        direct = component_transfer(city, "direct")
        stacked = np.concatenate([direct, specular, diffuse])
        base = 10.0 * np.log10(stacked[stacked > 0.0].min()) - 6.0
        width = 0.28
        for offset, values, component in (
            (-width, direct, "direct"),
            (0.0, specular, "all_specular"),
            (width, diffuse, "first_diffuse"),
        ):
            heights = masked_db(values) - base
            ax.bar(
                standpoints + offset,
                heights,
                width,
                bottom=base,
                color=COMPONENT_COLOUR[component],
                label=COMPONENT_LABEL[component],
            )
        for point in zero_direct:
            ax.axvspan(point - 0.5, point + 0.5, color="#f0c419", alpha=0.28, linewidth=0, zorder=0)
        ax.set_xticks(standpoints)
        ax.set_xlim(-0.7, standpoints[-1] + 0.7)
        ax.set_ylim(base, max(safe_db(direct).max(), safe_db(specular).max()) + 6.0)
        ax.set_ylabel(f"{CITY_LABEL[name]}\n" + r"$10\log_{10}D$ [dB]")
        wbsar = route_array(city, "wbsar")
        shadowed = sorted(zero_direct)
        lit = [point for point in standpoints if point not in zero_direct]
        numbers.setdefault("zero_direct", {})[name] = {
            "zero_direct_standpoints": shadowed,
            "shadowed_wbsar_median": float(np.median(wbsar[shadowed])),
            "lit_wbsar_median": float(np.median(wbsar[lit])),
            "shadow_deficit_db": float(10.0 * np.log10(np.median(wbsar[lit]) / np.median(wbsar[shadowed]))),
            "shadowed_specular_transfer": [float(specular[point]) for point in shadowed],
            "shadowed_diffuse_transfer": [float(diffuse[point]) for point in shadowed],
            "shadowed_carried_entirely_by_first_diffuse": bool(
                all(specular[point] == 0.0 and diffuse[point] > 0.0 for point in shadowed)
            ),
            "lit_specular_share_percent_median": float(
                np.median(100.0 * specular[lit] / (direct[lit] + specular[lit] + diffuse[lit]))
            ),
            "surplus_undefined_because_direct_is_zero": shadowed,
        }
    axes[-1].set_xlabel("standpoint index (shaded: zero direct transport)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        ncol=3,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.955),
        handlelength=1.2,
        columnspacing=1.0,
        fontsize=5.8,
    )
    fig.align_ylabels(axes)
    fig.subplots_adjust(hspace=0.34, top=0.9)
    save(fig, "C5_zero_direct_standpoints")


# --------------------------------------------------------------------------------------
# C6  16 replicas against 64, hybrid contract
# --------------------------------------------------------------------------------------
def figure_replica_16_vs_64(numbers: dict) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 3.6))
    delta_axis, se_axis = axes
    for name in ("Mexico", "Tokyo"):
        colour = CITY_COLOUR[name]
        long_run, long_seeds, _ = load_shards(REPLICA64[name])
        short_run, short_seeds, _ = load_shards(REPLICA16[name])
        assert short_seeds == long_seeds[: len(short_seeds)]
        shared = np.abs(short_run - long_run[: len(short_seeds)]).max()
        total_index = 3
        mean16 = long_run[:16, :, total_index].mean(axis=0)
        mean64 = long_run[:, :, total_index].mean(axis=0)
        positive = (mean16 > 0.0) & (mean64 > 0.0)
        delta = np.full(mean16.shape, np.nan)
        delta[positive] = 10.0 * np.log10(mean16[positive] / mean64[positive])
        standpoints = np.arange(mean16.size)
        delta_axis.plot(
            standpoints,
            np.abs(delta),
            linestyle="none",
            marker="o",
            markerfacecolor="none",
            markeredgewidth=0.6,
            color=colour,
            label=CITY_LABEL[name],
        )
        counts = np.array([4, 8, 12, 16, 24, 32, 48, 64])
        p90 = []
        for count in counts:
            sample = long_run[:count, :, total_index]
            mean = sample.mean(axis=0)
            error = sample.std(axis=0, ddof=1) / np.sqrt(count)
            usable = mean > 0.0
            p90.append(np.percentile(DB * error[usable] / mean[usable], 90))
        se_axis.plot(counts, p90, "-", marker="o", color=colour, label=CITY_LABEL[name])
        reference = p90[3] * np.sqrt(16.0 / counts)
        se_axis.plot(counts, reference, ":", color=colour, alpha=0.6)

        # p90 can move between standpoints as n grows, so also pair each standpoint
        # with itself and report the ratio of its own standard errors.
        def point_se(count: int) -> np.ndarray:
            sample = long_run[:count, :, total_index]
            return sample.std(axis=0, ddof=1) / np.sqrt(count) / sample.mean(axis=0)

        paired_ratio = point_se(16) / point_se(64)
        numbers.setdefault("replica_16_vs_64", {})[name] = {
            "contract": "hybrid_max_bounces_v1 (not the current production contract)",
            "shared_seed_max_abs_difference": float(shared),
            "standpoints": int(mean16.size),
            "zero_transfer_standpoints": int((~positive).sum()),
            "delta_16_vs_64_db_median": float(np.nanmedian(np.abs(delta))),
            "delta_16_vs_64_db_max": float(np.nanmax(np.abs(delta))),
            "delta_16_vs_64_db_argmax_standpoint": int(np.nanargmax(np.abs(delta))),
            "se_p90_db_at_16": float(p90[3]),
            "se_p90_db_at_64": float(p90[-1]),
            "se_p90_reduction_16_to_64": float(p90[3] / p90[-1]),
            "se_paired_reduction_16_to_64_median": float(np.median(paired_ratio)),
            "se_paired_reduction_16_to_64_min": float(paired_ratio.min()),
            "se_paired_reduction_16_to_64_max": float(paired_ratio.max()),
            "root_n_expectation": 2.0,
        }
    delta_axis.set_yscale("log")
    delta_axis.set_xlabel("standpoint index")
    delta_axis.set_ylabel(r"$|$16 vs 64 replicas$|$ [dB]")
    delta_axis.legend(loc="best", handlelength=1.2, fontsize=5.6)
    se_axis.set_xscale("log")
    se_axis.set_yscale("log")
    se_axis.set_xticks([4, 8, 16, 32, 64])
    se_axis.set_xticklabels(["4", "8", "16", "32", "64"])
    se_axis.xaxis.set_minor_locator(mpl.ticker.NullLocator())
    se_axis.set_xlabel("replicas")
    se_axis.set_ylabel("p90 SE of total transfer [dB]")
    se_axis.set_title(r"dotted: $1/\sqrt{n}$ anchored at 16 replicas", fontsize=6.0, pad=3)
    fig.subplots_adjust(hspace=0.62)
    save(fig, "C6_replica_16_vs_64")


def audit(results: dict, numbers: dict) -> None:
    published = {
        "Korenmarkt": 0.0000819,
        "Prague": 0.0001559,
        "Madrid": 0.0004083,
        "Mexico": 0.043625,
        "Tokyo": 0.019732,
    }
    for name in CITY_ORDER:
        city = results["cities"][name]
        total = component_transfer(city, "total")
        parts = sum(component_transfer(city, component) for component in COMPONENTS)
        numbers.setdefault("audit", {})[name] = {
            "seeds": city["seeds"],
            "standpoints": city["standpoints"],
            "replicas": city["replicas"],
            "transport_topology": city["transport_topology"],
            "route_contract": city["contract"]["route_contract"],
            "campaign_identity_sha256": city["provenance"]["campaign_identity_sha256"],
            "component_sum_max_relative_error": float(np.abs(parts / total - 1.0).max()),
            "recomputed_12_to_16_max_abs_db": float(
                city["convergence"]["look_to_look"][-1]["total_transfer"]["maximum_abs_db"]
            ),
            "published_12_to_16_max_abs_db": published[name],
            "estimator_wall_seconds_total": float(city["timings"]["estimator_wall_seconds"]["total_seconds"]),
            "specular_seconds_total": float(city["timings"]["specular_seconds"]["total_seconds"]),
            "stochastic_trace_seconds_total": float(city["timings"]["stochastic_trace_seconds"]["total_seconds"]),
            "body_coupling_seconds_total": float(city["timings"]["body_coupling_seconds"]["total_seconds"]),
        }
    numbers["not_retained"] = [
        "per-seed shards for the five first-material-interaction campaigns are not in this results tree, "
        "so seed-level resampling is only possible for the hybrid-contract 16 and 64 replica directories",
        "a per-replica ensemble-field peak, which the campaign records as unavailable for bootstrapping",
        "any specular order above one, by contract",
        "any continuation of a sampled path after the first diffuse interaction, by contract",
    ]
    numbers["contract"] = {
        "transport": "first_material_interaction_v1",
        "primary_rays": 200000,
        "output_cells": 4096,
        "launch_sampling": "iid",
        "seeds": "7 to 22",
        "looks": list(LOOKS),
    }


def main() -> None:
    setup_style()
    results = load_results()
    numbers: dict = {}
    figure_route_profiles(results, numbers)
    figure_component_share(results, numbers)
    figure_cross_city(results, numbers)
    figure_convergence(results, numbers)
    figure_zero_direct(results, numbers)
    figure_replica_16_vs_64(numbers)
    audit(results, numbers)
    output = pathlib.Path(__file__).resolve().parent / "five_city_numbers.json"
    output.write_text(json.dumps(numbers, indent=1, sort_keys=True) + "\n")
    print(json.dumps(numbers, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
