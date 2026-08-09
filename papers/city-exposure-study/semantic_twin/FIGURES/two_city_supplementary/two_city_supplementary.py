"""Supplementary analyses of the retained two-city paired roofline campaign.

The published two-city figure shows two panels: a fixed-route surplus CDF and a
normalised whole-body SAR CDF. Everything the campaign retained beyond that is
mined here, straight from the read-only result package.

Input is the retained package at ``PACKAGE_ROOT``. Nothing is written there. The
per-seed scalar shards under ``<campaign>/checkpoint/replicas/seed_*.npz`` are the
primary source, because they are the only artefact that still carries the seed
axis. Their column order is declared by ``<campaign>/checkpoint/index.json`` and
is asserted at load time against the names this script assumes, so a schema drift
fails loudly instead of silently relabelling a curve.

What is not retained, and therefore not plotted: separate sampled-suffix transfer
(the campaign persisted only acceptance counts and a chi diagnostic), and the
per-replica body ``Sab`` fields for the 56,024 surface samples at every look (only
the cumulative sums at looks 4, 8, 12, 16 survive, which fixes the mean field but
not a seed-resampling interval).
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PACKAGE_ROOT = pathlib.Path("/home/user/aegis-roofline-results-20260807T015530Z")
OUTPUT_DIR = pathlib.Path(__file__).resolve().parent

COMPONENTS = ("direct", "specular", "diffuse", "total")
BODY_METRICS = (
    "arriving_power_density_w_m2",
    "susceptibility",
    "peak_sab_w_m2",
    "mean_sab_w_m2",
    "absorbed_power_w",
    "sar_wb_w_kg",
)
FIELD_META = (
    "includes_specular",
    "missing_specular",
    "maximum_completed_all_specular_order",
    "maximum_completed_specular_suffix_order",
    "direct_atom_count",
    "specular_atom_count",
    "nonzero_diffuse_cell_count",
)
REFERENCE_FIELDS = ("d_ref_m_inv2", "reference_s0_w_m2")
TIMING_FIELDS = (
    "estimator_wall_seconds",
    "direct_shadow_seconds",
    "stochastic_trace_seconds",
    "specular_seconds",
    "body_coupling_seconds",
)

LOOKS = (4, 8, 12, 16)
SAMPLERS = ("iid", "rotated_fibonacci")
SAMPLER_LABEL = {"iid": "IID", "rotated_fibonacci": "Fibonacci"}
SAMPLER_STYLE = {"iid": "-", "rotated_fibonacci": "--"}
CITIES = (
    ("korenmarkt", "Korenmarkt, Ghent"),
    ("prague", "Prague Old Town Square"),
)
COMPONENT_COLOUR = {
    "direct": "#1b1b1b",
    "specular": "#c0392b",
    "diffuse": "#2471a3",
    "total": "#117a3d",
}
CITY_COLOUR = {"korenmarkt": "#c0392b", "prague": "#2471a3"}

DB = 10.0 / np.log(10.0)


@dataclass(frozen=True)
class Campaign:
    """One city in one sampling mode, with the seed axis intact."""

    city: str
    sampler: str
    seeds: tuple[int, ...]
    #: (seeds, points, components)
    raw_transfer: np.ndarray
    #: (seeds, points, components, body metrics)
    body_metrics: np.ndarray
    #: (seeds, points, field meta)
    field_meta: np.ndarray
    #: (seeds, points, reference fields)
    reference: np.ndarray
    #: (seeds, points, timing fields)
    timings: np.ndarray
    #: one dict per standpoint, from ``locations.jsonl``
    locations: tuple[dict, ...]

    @property
    def points(self) -> int:
        return self.raw_transfer.shape[1]

    @property
    def route_distance_m(self) -> np.ndarray:
        return np.array([row["route_distance_m"] for row in self.locations])

    @property
    def is_registered(self) -> np.ndarray:
        return np.array([row["point_kind"] == "camera_registered" for row in self.locations])

    def transfer(self, component: str, look: int = 16) -> np.ndarray:
        """Seed-mean raw transfer over the first ``look`` committed seeds."""
        return self.raw_transfer[:look, :, COMPONENTS.index(component)].mean(axis=0)

    def transfer_se(self, component: str, look: int = 16) -> np.ndarray:
        sample = self.raw_transfer[:look, :, COMPONENTS.index(component)]
        return sample.std(axis=0, ddof=1) / np.sqrt(look)

    def body(self, component: str, metric: str, look: int = 16) -> np.ndarray:
        return self.body_metrics[
            :look, :, COMPONENTS.index(component), BODY_METRICS.index(metric)
        ].mean(axis=0)

    def body_se(self, component: str, metric: str, look: int = 16) -> np.ndarray:
        sample = self.body_metrics[:look, :, COMPONENTS.index(component), BODY_METRICS.index(metric)]
        return sample.std(axis=0, ddof=1) / np.sqrt(look)

    def d_ref(self) -> np.ndarray:
        return self.reference[:, :, REFERENCE_FIELDS.index("d_ref_m_inv2")].mean(axis=0)

    def surplus_db(self, look: int = 16) -> np.ndarray:
        return 10.0 * np.log10(self.transfer("total", look) / self.transfer("direct", look))

    def shadow_loss_db(self, look: int = 16) -> np.ndarray:
        return 10.0 * np.log10(self.d_ref() / self.transfer("direct", look))

    def ensemble_peak_sab(self) -> np.ndarray:
        return np.array(
            [row["components"]["total"]["body"]["ensemble_field_peak_sab_w_m2"] for row in self.locations]
        )


def load_campaign(city: str, sampler: str) -> Campaign:
    directory = PACKAGE_ROOT / f"{city}_convergence_cuda_{sampler}"
    index = json.loads((directory / "checkpoint" / "index.json").read_text())
    # A schema drift must fail here rather than mislabel a curve downstream.
    assert tuple(index["components"]) == COMPONENTS, index["components"]
    assert tuple(index["body_metrics"]) == BODY_METRICS, index["body_metrics"]
    assert tuple(index["reference_fields"]) == REFERENCE_FIELDS, index["reference_fields"]
    assert tuple(index["timing_fields"]) == TIMING_FIELDS, index["timing_fields"]
    assert tuple(index["convergence_looks"]) == LOOKS, index["convergence_looks"]

    committed = index["committed"]
    shards = [np.load(directory / "checkpoint" / entry["path"]) for entry in committed]
    stack = {
        key: np.stack([shard[key] for shard in shards])
        for key in ("raw_transfer", "body_metrics", "field_meta", "reference", "timings")
    }
    locations = tuple(
        json.loads(line) for line in (directory / "locations.jsonl").read_text().splitlines() if line.strip()
    )
    assert len(locations) == index["points"] == stack["raw_transfer"].shape[1]
    return Campaign(
        city=city,
        sampler=sampler,
        seeds=tuple(entry["seed"] for entry in committed),
        raw_transfer=stack["raw_transfer"],
        body_metrics=stack["body_metrics"],
        field_meta=stack["field_meta"],
        reference=stack["reference"],
        timings=stack["timings"],
        locations=locations,
    )


def ecdf(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Midpoint empirical CDF, the same convention the published figure uses."""
    array = np.sort(np.asarray(values, dtype=np.float64))
    return array, (np.arange(array.size) + 0.5) / array.size


def _constant(ratio: np.ndarray) -> dict:
    """Report a ratio claimed to be constant, together with how constant it is."""
    return {
        "value": float(np.mean(ratio)),
        "max_relative_deviation": float(np.abs(ratio / np.mean(ratio) - 1.0).max()),
    }


def se_db(sample: np.ndarray) -> np.ndarray:
    """Standard error of a positive quantity, propagated to dB by the delta rule."""
    mean = sample.mean(axis=0)
    se = sample.std(axis=0, ddof=1) / np.sqrt(sample.shape[0])
    return DB * se / mean


def setup_style() -> None:
    try:
        import scienceplots  # noqa: F401

        plt.style.use(["science", "ieee", "no-latex"])
    except Exception:  # pragma: no cover - style is cosmetic
        plt.style.use("default")
    mpl.rcParams.update(
        {
            "figure.dpi": 200,
            "savefig.dpi": 400,
            "font.size": 7,
            "axes.titlesize": 7.5,
            "axes.labelsize": 7,
            "legend.fontsize": 6,
            "xtick.labelsize": 6.5,
            "ytick.labelsize": 6.5,
            "legend.frameon": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linewidth": 0.4,
            "lines.linewidth": 0.9,
            "lines.markersize": 2.6,
            "axes.prop_cycle": mpl.cycler(color=["#1b1b1b", "#c0392b", "#2471a3", "#117a3d", "#8e44ad"]),
        }
    )


def save(fig: plt.Figure, stem: str) -> None:
    for suffix in ("pdf", "png"):
        fig.savefig(OUTPUT_DIR / f"{stem}.{suffix}", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


# --------------------------------------------------------------------------------------
# S1  Route transfer profile
# --------------------------------------------------------------------------------------
def figure_route_profile(data: dict[tuple[str, str], Campaign], numbers: dict) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 4.1))
    for ax, (city, title) in zip(axes, CITIES):
        campaign = data[(city, "iid")]
        distance = campaign.route_distance_m
        ax.plot(
            distance,
            10.0 * np.log10(campaign.d_ref()),
            color="#7f8c8d",
            linestyle=":",
            label="unshadowed reference",
        )
        for component in ("total", "direct", "specular", "diffuse"):
            ax.plot(
                distance,
                10.0 * np.log10(campaign.transfer(component)),
                color=COMPONENT_COLOUR[component],
                linestyle="-" if component in ("total", "direct") else "--",
                label=component,
            )
        registered = campaign.is_registered
        ax.plot(
            distance[registered],
            10.0 * np.log10(campaign.transfer("total"))[registered],
            linestyle="none",
            marker="o",
            markerfacecolor="none",
            markeredgecolor=COMPONENT_COLOUR["total"],
            markeredgewidth=0.6,
            label="camera-registered",
        )
        ax.set_title(f"{title} ({campaign.points} standpoints)")
        ax.set_ylabel(r"transfer $10\log_{10}(D)$  [dB re 1 m$^{-2}$]")
        numbers.setdefault("route_profile", {})[city] = {
            "registered_points": int(registered.sum()),
            "total_transfer_db_min": float(10.0 * np.log10(campaign.transfer("total")).min()),
            "total_transfer_db_max": float(10.0 * np.log10(campaign.transfer("total")).max()),
            "total_transfer_db_span": float(
                np.ptp(10.0 * np.log10(campaign.transfer("total")))
            ),
            "diffuse_below_direct_db_median": float(
                np.median(10.0 * np.log10(campaign.transfer("direct") / campaign.transfer("diffuse")))
            ),
            "specular_below_direct_db_median": float(
                np.median(10.0 * np.log10(campaign.transfer("direct") / campaign.transfer("specular")))
            ),
        }
    axes[0].legend(ncol=2, loc="lower left", handlelength=1.6, columnspacing=1.0)
    axes[-1].set_xlabel("route distance [m]")
    fig.align_ylabels(axes)
    fig.subplots_adjust(hspace=0.45)
    save(fig, "S1_route_transfer_profile")


# --------------------------------------------------------------------------------------
# S2  Shadowing loss and multipath surplus along the route
# --------------------------------------------------------------------------------------
def figure_route_budget(data: dict[tuple[str, str], Campaign], numbers: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(3.5, 3.9), sharex="col")
    for column, (city, title) in enumerate(CITIES):
        campaign = data[(city, "iid")]
        distance = campaign.route_distance_m
        shadow = campaign.shadow_loss_db()
        surplus = campaign.surplus_db()
        top, bottom = axes[0, column], axes[1, column]
        top.fill_between(distance, 0.0, shadow, color="#7f8c8d", alpha=0.35, linewidth=0)
        top.plot(distance, shadow, color="#34495e")
        top.set_title(title.split(",")[0], pad=3)
        specular_share = 100.0 * campaign.transfer("specular") / campaign.transfer("total")
        diffuse_share = 100.0 * campaign.transfer("diffuse") / campaign.transfer("total")
        bottom.stackplot(
            distance,
            specular_share,
            diffuse_share,
            colors=[COMPONENT_COLOUR["specular"], COMPONENT_COLOUR["diffuse"]],
            alpha=0.55,
            edgecolor="none",
            labels=["specular", "diffuse"],
        )
        twin = bottom.twinx()
        twin.plot(distance, surplus, color="#117a3d", linewidth=1.0)
        twin.set_ylim(0.0, 1.75)
        if column == 1:
            twin.set_ylabel("surplus [dB]", color="#117a3d", labelpad=1)
            twin.tick_params(axis="y", colors="#117a3d")
        else:
            twin.set_yticklabels([])
        twin.grid(False)
        bottom.set_xlabel("route distance [m]")
        numbers.setdefault("route_budget", {})[city] = {
            "shadow_loss_db_median": float(np.median(shadow)),
            "shadow_loss_db_min": float(shadow.min()),
            "shadow_loss_db_max": float(shadow.max()),
            "shadow_loss_argmax_standpoint": int(shadow.argmax()),
            "surplus_db_median": float(np.median(surplus)),
            "surplus_db_min": float(surplus.min()),
            "surplus_db_max": float(surplus.max()),
            "surplus_argmax_standpoint": int(surplus.argmax()),
            "surplus_argmin_standpoint": int(surplus.argmin()),
            "specular_share_percent_median": float(np.median(specular_share)),
            "specular_share_percent_min": float(specular_share.min()),
            "specular_share_percent_max": float(specular_share.max()),
            "diffuse_share_percent_median": float(np.median(diffuse_share)),
            "diffuse_share_percent_max": float(diffuse_share.max()),
            "pearson_r_shadow_vs_surplus": float(np.corrcoef(shadow, surplus)[0, 1]),
        }
    axes[0, 0].set_ylabel("shadow loss [dB]")
    axes[1, 0].set_ylabel("share of total [%]")
    axes[0, 0].set_ylim(0.0, 3.8)
    axes[0, 1].set_ylim(0.0, 3.8)
    axes[1, 0].set_ylim(0.0, 32.0)
    axes[1, 1].set_ylim(0.0, 32.0)
    axes[0, 1].set_yticklabels([])
    axes[1, 1].set_yticklabels([])
    axes[1, 0].legend(loc="lower left", handlelength=1.2, fontsize=5.5)
    fig.subplots_adjust(wspace=0.12, hspace=0.22)
    save(fig, "S2_route_shadow_and_surplus")


# --------------------------------------------------------------------------------------
# S3  Seed convergence
# --------------------------------------------------------------------------------------
def figure_convergence(data: dict[tuple[str, str], Campaign], numbers: dict) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(3.5, 3.9))
    for row, (city, title) in enumerate(CITIES):
        left, right = axes[row, 0], axes[row, 1]
        for sampler in SAMPLERS:
            campaign = data[(city, sampler)]
            medians, p90s, movement = [], [], []
            for look in LOOKS:
                sample = campaign.raw_transfer[:look, :, COMPONENTS.index("total")]
                errors = se_db(sample)
                medians.append(np.median(errors))
                p90s.append(np.percentile(errors, 90))
            for previous, current in zip(LOOKS[:-1], LOOKS[1:]):
                shift = np.abs(
                    10.0
                    * np.log10(campaign.transfer("total", current) / campaign.transfer("total", previous))
                )
                movement.append(np.percentile(shift, 90))
            marker = "o" if sampler == "iid" else "^"
            left.plot(LOOKS, p90s, SAMPLER_STYLE[sampler], marker=marker, color=CITY_COLOUR[city],
                      label=f"p90, {SAMPLER_LABEL[sampler]}")
            left.plot(LOOKS, medians, SAMPLER_STYLE[sampler], marker=marker, color="#7f8c8d",
                      label=f"median, {SAMPLER_LABEL[sampler]}")
            right.plot(LOOKS[1:], movement, SAMPLER_STYLE[sampler], marker=marker, color=CITY_COLOUR[city],
                       label=SAMPLER_LABEL[sampler])
            numbers.setdefault("convergence", {}).setdefault(city, {})[sampler] = {
                "se_db_median_by_look": {str(look): float(value) for look, value in zip(LOOKS, medians)},
                "se_db_p90_by_look": {str(look): float(value) for look, value in zip(LOOKS, p90s)},
                "look_to_look_p90_abs_db": {
                    f"{a}_to_{b}": float(value) for (a, b), value in zip(zip(LOOKS[:-1], LOOKS[1:]), movement)
                },
            }
        left.set_yscale("log")
        right.set_yscale("log")
        left.set_ylabel(f"{title.split(',')[0]}\nSE of total transfer [dB]")
        right.set_ylabel(r"p90 $|$look shift$|$ [dB]")
        left.set_xticks(LOOKS)
        right.set_xticks(LOOKS[1:])
        if row == 1:
            left.set_xlabel("seeds in look")
            right.set_xlabel("look upper seed count")
    axes[0, 0].legend(loc="lower left", handlelength=1.8, fontsize=5.2, ncol=1)
    axes[0, 1].legend(loc="upper right", handlelength=1.8, fontsize=5.5)
    fig.subplots_adjust(wspace=0.55, hspace=0.34)
    save(fig, "S3_seed_convergence")


# --------------------------------------------------------------------------------------
# S4  Paired IID against Fibonacci
# --------------------------------------------------------------------------------------
def figure_paired_deltas(data: dict[tuple[str, str], Campaign], numbers: dict) -> None:
    quantities = (
        ("total transfer", lambda c: c.transfer("total")),
        ("body mean $S_{ab}$", lambda c: c.body("total", "mean_sab_w_m2")),
        ("peak $S_{ab}$", lambda c: c.body("total", "peak_sab_w_m2")),
        ("diffuse transfer", lambda c: c.transfer("diffuse")),
    )
    colours = ["#117a3d", "#c0392b", "#8e44ad", "#2471a3"]
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 3.9))
    for ax, (city, title) in zip(axes, CITIES):
        iid = data[(city, "iid")]
        fibonacci = data[(city, "rotated_fibonacci")]
        for colour, (label, getter) in zip(colours, quantities):
            delta = 10.0 * np.log10(getter(iid) / getter(fibonacci))
            x, y = ecdf(np.abs(delta))
            ax.step(np.maximum(x, 1e-6), y, where="post", color=colour, label=label)
            numbers.setdefault("paired_deltas", {}).setdefault(city, {})[label] = {
                "max_abs_db": float(np.abs(delta).max()),
                "p90_abs_db": float(np.percentile(np.abs(delta), 90)),
                "median_abs_db": float(np.median(np.abs(delta))),
                "median_signed_db": float(np.median(delta)),
                "argmax_standpoint": int(np.abs(delta).argmax()),
            }
        direct_delta = np.abs(
            10.0 * np.log10(iid.transfer("direct") / fibonacci.transfer("direct"))
        ).max()
        numbers.setdefault("paired_deltas", {}).setdefault(city, {})["direct transfer"] = {
            "max_abs_db": float(direct_delta),
            "note": "direct transfer is a deterministic exact atom sum, identical in both samplers",
        }
        ax.set_xscale("log")
        ax.set_xlim(1e-6, 1.0)
        ax.set_ylim(0.0, 1.0)
        ax.set_title(title)
        ax.set_ylabel("fixed-route ECDF")
    axes[0].legend(loc="upper left", handlelength=1.5)
    axes[-1].set_xlabel(r"$|$IID $-$ Fibonacci$|$ per standpoint [dB]")
    fig.subplots_adjust(hspace=0.42)
    save(fig, "S4_paired_sampler_deltas")


# --------------------------------------------------------------------------------------
# S5  Fixed-route distributions
# --------------------------------------------------------------------------------------
def figure_fixed_route_cdfs(data: dict[tuple[str, str], Campaign], numbers: dict) -> None:
    panels = (
        ("multipath surplus [dB]", lambda c: c.surplus_db(), None),
        (r"normalised wbSAR [m$^2$ kg$^{-1}$]", lambda c: c.body("total", "sar_wb_w_kg"), "log"),
        (r"peak $S_{ab}$ / body-mean $S_{ab}$", lambda c: c.body("total", "peak_sab_w_m2") / c.body("total", "mean_sab_w_m2"), None),
    )
    fig, axes = plt.subplots(3, 1, figsize=(3.5, 5.0))
    for ax, (label, getter, scale) in zip(axes, panels):
        for city, title in CITIES:
            for sampler in SAMPLERS:
                campaign = data[(city, sampler)]
                x, y = ecdf(getter(campaign))
                ax.step(
                    x,
                    y,
                    where="post",
                    color=CITY_COLOUR[city],
                    linestyle=SAMPLER_STYLE[sampler],
                    label=f"{title.split(' ')[0].rstrip(',')} {SAMPLER_LABEL[sampler]}",
                )
            values = getter(data[(city, "iid")])
            numbers.setdefault("fixed_route_cdf", {}).setdefault(city, {})[label] = {
                "median": float(np.median(values)),
                "p10": float(np.percentile(values, 10)),
                "p90": float(np.percentile(values, 90)),
                "min": float(values.min()),
                "max": float(values.max()),
                "n_standpoints": int(values.size),
            }
        if scale:
            ax.set_xscale(scale)
        ax.set_xlabel(label)
        ax.set_ylabel("fixed-route ECDF")
        ax.set_ylim(0.0, 1.0)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.985),
        handlelength=1.6,
        columnspacing=1.2,
        fontsize=5.8,
    )
    axes[0].set_title("Empirical CDF over the fixed route, not a population CDF", fontsize=6.5, pad=3)
    fig.subplots_adjust(hspace=0.58, top=0.86)
    save(fig, "S5_fixed_route_cdfs")


# --------------------------------------------------------------------------------------
# S6  Body endpoint relations
# --------------------------------------------------------------------------------------
def figure_body_endpoints(data: dict[tuple[str, str], Campaign], numbers: dict) -> None:
    fig, axes = plt.subplots(3, 1, figsize=(3.5, 5.2))
    peak_axis, coupling_axis, bias_axis = axes
    for city, title in CITIES:
        campaign = data[(city, "iid")]
        mean_sab = campaign.body("total", "mean_sab_w_m2")
        peak_sab = campaign.body("total", "peak_sab_w_m2")
        arriving = campaign.body("total", "arriving_power_density_w_m2")
        ensemble_peak = campaign.ensemble_peak_sab()
        surplus = campaign.surplus_db()
        peak_axis.plot(
            mean_sab,
            peak_sab,
            linestyle="none",
            marker="o",
            markerfacecolor="none",
            markeredgewidth=0.5,
            color=CITY_COLOUR[city],
            label=title.split(",")[0],
        )
        coupling_axis.plot(
            surplus,
            mean_sab / arriving,
            linestyle="none",
            marker="o",
            markerfacecolor="none",
            markeredgewidth=0.5,
            color=CITY_COLOUR[city],
            label=title.split(",")[0],
        )
        bias = 10.0 * np.log10(peak_sab / ensemble_peak)
        # The body reweights each component by incidence, so the surplus the body
        # absorbs is not the surplus the geometry delivers.
        body_surplus = 10.0 * np.log10(mean_sab / campaign.body("direct", "mean_sab_w_m2"))
        x, y = ecdf(body_surplus - surplus)
        bias_axis.step(x, y, where="post", color=CITY_COLOUR[city], label=title.split(",")[0])
        numbers.setdefault("body_endpoints", {})[city] = {
            "peak_over_mean_median": float(np.median(peak_sab / mean_sab)),
            "peak_over_mean_min": float((peak_sab / mean_sab).min()),
            "peak_over_mean_max": float((peak_sab / mean_sab).max()),
            "coupling_efficiency_median": float(np.median(mean_sab / arriving)),
            "coupling_efficiency_min": float((mean_sab / arriving).min()),
            "coupling_efficiency_max": float((mean_sab / arriving).max()),
            "pearson_r_surplus_vs_coupling": float(np.corrcoef(surplus, mean_sab / arriving)[0, 1]),
            "replica_peak_bias_db_median": float(np.median(bias)),
            "replica_peak_bias_db_max": float(bias.max()),
            "body_minus_transfer_surplus_db_median": float(np.median(body_surplus - surplus)),
            "body_minus_transfer_surplus_db_max_abs": float(np.abs(body_surplus - surplus).max()),
            "sar_over_mean_sab": _constant(campaign.body("total", "sar_wb_w_kg") / mean_sab),
            "absorbed_power_over_mean_sab": _constant(
                campaign.body("total", "absorbed_power_w") / mean_sab
            ),
            "arriving_over_total_transfer": _constant(arriving / campaign.transfer("total")),
        }
    for city, _ in CITIES:
        campaign = data[(city, "iid")]
        mean_sab = campaign.body("total", "mean_sab_w_m2")
        ratio = np.median(campaign.body("total", "peak_sab_w_m2") / mean_sab)
        grid = np.linspace(mean_sab.min(), mean_sab.max(), 8)
        peak_axis.plot(grid, ratio * grid, color=CITY_COLOUR[city], linewidth=0.5, linestyle=":")
    peak_axis.set_xlabel(r"body-mean $S_{ab}$  [normalised]")
    peak_axis.set_ylabel(r"per-replica peak $S_{ab}$")
    peak_axis.set_xscale("log")
    peak_axis.set_yscale("log")
    peak_axis.legend(loc="upper left", handlelength=1.2)
    peak_axis.set_title("dotted line: city median peak-to-mean ratio", fontsize=6.0, pad=3)
    coupling_axis.set_xlabel("multipath surplus [dB]")
    coupling_axis.set_ylabel(r"$\overline{S_{ab}}$ / arriving $S$")
    coupling_axis.margins(y=0.10)
    bias_axis.set_xlabel("body-absorbed surplus minus transfer surplus [dB]")
    bias_axis.set_ylabel("fixed-route ECDF")
    bias_axis.axvline(0.0, color="#7f8c8d", linewidth=0.6, linestyle=":")
    bias_axis.legend(loc="lower right", handlelength=1.2)
    fig.subplots_adjust(hspace=0.62)
    save(fig, "S6_body_endpoint_relations")


# --------------------------------------------------------------------------------------
# S7  Sampler variance ratio by component
# --------------------------------------------------------------------------------------
def figure_variance_ratio(data: dict[tuple[str, str], Campaign], numbers: dict) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(3.5, 3.7))
    for ax, (city, title) in zip(axes, CITIES):
        iid = data[(city, "iid")]
        fibonacci = data[(city, "rotated_fibonacci")]
        for component in ("specular", "diffuse", "total"):
            index = COMPONENTS.index(component)
            variance_iid = iid.raw_transfer[:, :, index].var(axis=0, ddof=1)
            variance_fib = fibonacci.raw_transfer[:, :, index].var(axis=0, ddof=1)
            ratio = variance_fib / variance_iid
            x, y = ecdf(np.log2(ratio))
            ax.step(x, y, where="post", color=COMPONENT_COLOUR[component], label=component)
            numbers.setdefault("variance_ratio", {}).setdefault(city, {})[component] = {
                "median": float(np.median(ratio)),
                "q10": float(np.percentile(ratio, 10)),
                "q90": float(np.percentile(ratio, 90)),
                "max": float(ratio.max()),
                "fraction_below_one": float(np.mean(ratio < 1.0)),
            }
        ax.axvline(0.0, color="#7f8c8d", linewidth=0.6, linestyle=":")
        ax.set_title(title)
        ax.set_ylabel("fixed-route ECDF")
        ax.set_ylim(0.0, 1.0)
        ax.set_xlim(-11.0, 11.0)
    axes[0].legend(loc="upper left", handlelength=1.4)
    axes[-1].set_xlabel(r"$\log_2$(Fibonacci variance / IID variance), 16 seeds")
    fig.subplots_adjust(hspace=0.45)
    save(fig, "S7_variance_ratio_by_component")


def audit_numbers(data: dict[tuple[str, str], Campaign], numbers: dict) -> None:
    """Cross checks that keep the README honest, plus what is missing."""
    published = {
        "korenmarkt": {"surplus_db": 1.12153, "wbsar": 0.0631297},
        "prague": {"surplus_db": 1.10519, "wbsar": 0.0121379},
    }
    for city, _ in CITIES:
        campaign = data[(city, "iid")]
        numbers.setdefault("audit", {})[city] = {
            "seeds": list(campaign.seeds),
            "points": campaign.points,
            "recomputed_median_surplus_db": float(np.median(campaign.surplus_db())),
            "published_median_surplus_db": published[city]["surplus_db"],
            "recomputed_median_wbsar": float(np.median(campaign.body("total", "sar_wb_w_kg"))),
            "published_median_wbsar": published[city]["wbsar"],
            "component_sum_max_relative_error": float(
                np.abs(
                    campaign.raw_transfer[:, :, :3].sum(axis=2) / campaign.raw_transfer[:, :, 3] - 1.0
                ).max()
            ),
            "direct_transfer_seed_spread_max": float(
                np.ptp(campaign.raw_transfer[:, :, 0], axis=0).max()
            ),
            "specular_atom_count_median": float(
                np.median(campaign.field_meta[:, :, FIELD_META.index("specular_atom_count")].mean(axis=0))
            ),
            "specular_atom_count_min": float(
                campaign.field_meta[:, :, FIELD_META.index("specular_atom_count")].mean(axis=0).min()
            ),
            "nonzero_diffuse_cells_median": float(
                np.median(
                    campaign.field_meta[:, :, FIELD_META.index("nonzero_diffuse_cell_count")].mean(axis=0)
                )
            ),
            "estimator_wall_seconds_per_replica_total": float(
                campaign.timings[:, :, TIMING_FIELDS.index("estimator_wall_seconds")].sum(axis=1).mean()
            ),
        }
    numbers["not_retained"] = [
        "separate sampled-suffix transfer (only acceptance counts and a chi diagnostic survive)",
        "per-replica body Sab fields at every look (only cumulative sums at looks 4, 8, 12, 16)",
        "specular orders above one (production transport stops at one reflection)",
        "corrected stage timing (the paired artefacts carry a known timing attribution defect)",
    ]


def main() -> None:
    setup_style()
    data = {
        (city, sampler): load_campaign(city, sampler)
        for city, _ in CITIES
        for sampler in SAMPLERS
    }
    numbers: dict = {}
    figure_route_profile(data, numbers)
    figure_route_budget(data, numbers)
    figure_convergence(data, numbers)
    figure_paired_deltas(data, numbers)
    figure_fixed_route_cdfs(data, numbers)
    figure_body_endpoints(data, numbers)
    figure_variance_ratio(data, numbers)
    audit_numbers(data, numbers)
    (OUTPUT_DIR / "supplementary_numbers.json").write_text(json.dumps(numbers, indent=1, sort_keys=True) + "\n")
    print(json.dumps(numbers, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
