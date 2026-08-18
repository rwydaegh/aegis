"""Plot first-interaction component shares on five fixed urban routes.

Run from any directory with:

    uv run --project /home/user/tools/devpc-python python components.py

The script authenticates the sealed aggregate, validates pointwise component
conservation and the declared zero-direct strata, then writes ``components.pdf``,
``components.png``, and ``components.json`` beside itself.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
SEMANTIC_TWIN = HERE.parents[2]
INPUT_DIRECTORY = SEMANTIC_TWIN / "outputs" / "roofline_campaign" / "current_five_city_first_material_interaction"
INPUT_JSON = INPUT_DIRECTORY / "current_five_city_first_material_interaction.json"
INPUT_MANIFEST = INPUT_DIRECTORY / "current_five_city_first_material_interaction_manifest.json"

RESULT_SCHEMA = "roofline_multicity_results_v1"
MANIFEST_SCHEMA = "roofline_multicity_artifacts_v1"
TRANSPORT_TOPOLOGY = "first_material_interaction_v1"
COMPONENTS = ("direct", "all_specular", "first_diffuse")
SEALED_COMPONENTS = (*COMPONENTS, "total")
CITY_ORDER = ("Korenmarkt", "Prague", "Madrid", "Mexico", "Tokyo")
CITY_LABELS = {
    "Korenmarkt": "Ghent",
    "Prague": "Prague",
    "Madrid": "Madrid",
    "Mexico": "Mexico City",
    "Tokyo": "Tokyo",
}
EXPECTED_ZERO_DIRECT = {
    "Korenmarkt": (),
    "Prague": (),
    "Madrid": (),
    "Mexico": (0, 1, 3),
    "Tokyo": (13, 14, 15),
}
COMPONENT_LABELS = {
    "direct": "Direct",
    "all_specular": "Exact order-1 specular",
    "first_diffuse": "First diffuse",
}
COMPONENT_STYLES = {
    "direct": {"color": "#000000", "hatch": ""},
    "all_specular": {"color": "#FF0000", "hatch": "////"},
    "first_diffuse": {"color": "#00C000", "hatch": "xxxx"},
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_authenticated_results() -> tuple[dict, dict, str]:
    manifest = json.loads(INPUT_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == MANIFEST_SCHEMA
    assert manifest["result_schema_version"] == RESULT_SCHEMA
    assert set(manifest["sources"]) == set(CITY_ORDER)
    for city_name in CITY_ORDER:
        source = manifest["sources"][city_name]
        assert tuple(source["components"]) == SEALED_COMPONENTS
        assert source["transport_topology"] == TRANSPORT_TOPOLOGY
    expected = manifest["artifacts"][INPUT_JSON.name]["sha256"]
    actual = _sha256(INPUT_JSON)
    assert actual == expected, f"aggregate hash mismatch: {actual} != {expected}"

    results = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    assert results["schema_version"] == RESULT_SCHEMA
    assert set(results["cities"]) == set(CITY_ORDER)
    return results, manifest, actual


def _validated_city_arrays(results: dict) -> tuple[dict[str, np.ndarray], dict]:
    arrays: dict[str, np.ndarray] = {}
    city_audit: dict[str, dict] = {}
    observed_zero_direct: dict[str, tuple[int, ...]] = {}
    conservation_errors: list[np.ndarray] = []

    for city_name in CITY_ORDER:
        city = results["cities"][city_name]
        assert tuple(city["components"]) == SEALED_COMPONENTS
        assert city["transport_topology"] == TRANSPORT_TOPOLOGY
        assert city["contract"]["specular_acceptance"] == ("first_material_interaction_exact_order_1")

        route = city["route"]
        assert [point["standpoint"] for point in route] == list(range(len(route)))
        assert np.all(np.diff([point["route_distance_m"] for point in route]) > 0.0)
        values = np.asarray(
            [[point["component_raw_transfer_m_inv2"][key] for key in SEALED_COMPONENTS] for point in route],
            dtype=np.float64,
        )
        assert np.isfinite(values).all()
        assert np.all(values >= 0.0)
        assert np.all(values[:, -1] > 0.0)

        component_sum = values[:, :3].sum(axis=1)
        error = component_sum - values[:, 3]
        np.testing.assert_allclose(component_sum, values[:, 3], rtol=5e-13, atol=1e-18)
        conservation_errors.append(error)

        zero_direct = tuple(np.flatnonzero(values[:, 0] == 0.0).tolist())
        declared_zero_direct = tuple(city["tail_instability"]["zero_direct_standpoints"])
        assert zero_direct == declared_zero_direct
        observed_zero_direct[city_name] = zero_direct
        assert zero_direct == EXPECTED_ZERO_DIRECT[city_name]
        if zero_direct:
            indices = np.asarray(zero_direct, dtype=int)
            assert np.all(values[indices, 1] == 0.0)
            np.testing.assert_array_equal(values[indices, 2], values[indices, 3])

        shares = values[:, :3] / values[:, 3, None]
        np.testing.assert_allclose(shares.sum(axis=1), 1.0, rtol=5e-13, atol=5e-15)
        arrays[city_name] = shares
        dominance = np.argmax(shares, axis=1)
        city_audit[city_name] = {
            "standpoints": len(route),
            "route_span_m": float(route[-1]["route_distance_m"]),
            "zero_direct_standpoints": list(zero_direct),
            "median_component_share_percent": {
                component: float(100.0 * np.median(shares[:, index])) for index, component in enumerate(COMPONENTS)
            },
            "dominant_component_counts": {
                component: int(np.count_nonzero(dominance == index)) for index, component in enumerate(COMPONENTS)
            },
        }

    assert observed_zero_direct == EXPECTED_ZERO_DIRECT
    all_errors = np.concatenate(conservation_errors)
    return arrays, {
        "cities": city_audit,
        "component_conservation": {
            "assertion": "direct + exact order-1 specular + first diffuse = total",
            "relative_tolerance": 5e-13,
            "absolute_tolerance_m_inv2": 1e-18,
            "maximum_absolute_residual_m_inv2": float(np.max(np.abs(all_errors))),
            "passed": True,
        },
        "zero_direct_assertion": {
            "expected_and_observed": {city: list(EXPECTED_ZERO_DIRECT[city]) for city in CITY_ORDER},
            "count": int(sum(len(points) for points in EXPECTED_ZERO_DIRECT.values())),
            "passed": True,
        },
    }


def _configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "serif",
            "font.serif": ["Latin Modern Roman", "Computer Modern Roman", "DejaVu Serif"],
            "font.size": 9.0,
            "axes.labelsize": 9.0,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
            "mathtext.fontset": "cm",
            "text.usetex": True,
            "text.latex.preamble": r"\usepackage[T1]{fontenc}",
            "axes.linewidth": 0.6,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "xtick.major.size": 3.0,
            "ytick.major.size": 3.0,
            "hatch.linewidth": 0.35,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.facecolor": "white",
        }
    )


def _plot(arrays: dict[str, np.ndarray]) -> None:
    _configure_style()
    fig, ax = plt.subplots(figsize=(7.16, 2.55))
    gap = 1.6
    cursor = 0.0
    centers: list[float] = []

    for city_index, city_name in enumerate(CITY_ORDER):
        shares = 100.0 * arrays[city_name]
        x = cursor + np.arange(shares.shape[0], dtype=np.float64)
        bottom = np.zeros(shares.shape[0], dtype=np.float64)
        for component_index, component in enumerate(COMPONENTS):
            style = COMPONENT_STYLES[component]
            ax.bar(
                x,
                shares[:, component_index],
                width=0.88,
                bottom=bottom,
                color=style["color"],
                edgecolor="white" if component == "direct" else "#202020",
                linewidth=0.18,
                hatch=style["hatch"],
                rasterized=False,
                zorder=2,
            )
            bottom += shares[:, component_index]

        zero_indices = np.asarray(EXPECTED_ZERO_DIRECT[city_name], dtype=int)
        if zero_indices.size:
            zero_x = x[zero_indices]
            ax.plot(
                zero_x,
                np.full(zero_x.shape, 101.8),
                linestyle="none",
                marker="v",
                markersize=5.4,
                markerfacecolor="none",
                markeredgecolor="black",
                markeredgewidth=0.8,
                clip_on=False,
                zorder=5,
            )
            label = ", ".join(str(point) for point in EXPECTED_ZERO_DIRECT[city_name])
            ax.text(
                float(np.mean(zero_x)),
                1.075,
                f"points {label}",
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="bottom",
                fontsize=8.0,
                clip_on=False,
            )

        centers.append(float((x[0] + x[-1]) / 2.0))
        cursor = float(x[-1] + 1.0 + gap)
        if city_index < len(CITY_ORDER) - 1:
            ax.axvline(cursor - gap / 2.0, color="0.72", linewidth=0.55, zorder=1)

    handles = [
        Patch(
            facecolor=COMPONENT_STYLES[component]["color"],
            edgecolor="#202020",
            linewidth=0.3,
            hatch=COMPONENT_STYLES[component]["hatch"],
            label=COMPONENT_LABELS[component],
        )
        for component in COMPONENTS
    ]
    handles.append(
        Line2D(
            [],
            [],
            color="black",
            linestyle="none",
            marker="v",
            markerfacecolor="none",
            markeredgewidth=0.8,
            markersize=5.4,
            label="Zero direct",
        )
    )
    ax.legend(
        handles=handles,
        ncol=4,
        frameon=False,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.19),
        handlelength=1.7,
        columnspacing=1.6,
        borderaxespad=0.0,
    )

    ax.set_xlim(-0.7, cursor - gap + 0.3)
    ax.set_ylim(0.0, 100.0)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel(r"Share of total transfer [\%]")
    ax.set_xticks(centers, [CITY_LABELS[city] for city in CITY_ORDER])
    ax.set_xlabel("Fixed route (standpoints ordered by distance)", labelpad=4.0)
    ax.grid(axis="y", color="0.86", linewidth=0.45, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", length=0, pad=4.0)
    fig.subplots_adjust(left=0.085, right=0.995, bottom=0.25, top=0.77)
    fig.savefig(HERE / "components.pdf", bbox_inches="tight", pad_inches=0.015)
    fig.savefig(HERE / "components.png", dpi=400, bbox_inches="tight", pad_inches=0.015)
    plt.close(fig)


def _write_audit(manifest: dict, input_hash: str, arrays: dict[str, np.ndarray], audit: dict) -> None:
    pooled = np.concatenate([arrays[city] for city in CITY_ORDER], axis=0)
    dominance = np.argmax(pooled, axis=1)
    zero_diffuse_shares = np.concatenate(
        [
            arrays[city][np.asarray(EXPECTED_ZERO_DIRECT[city], dtype=int), 2]
            for city in CITY_ORDER
            if EXPECTED_ZERO_DIRECT[city]
        ]
    )
    np.testing.assert_array_equal(zero_diffuse_shares, np.ones(6, dtype=np.float64))
    pdf_path = HERE / "components.pdf"
    png_path = HERE / "components.png"
    png_shape = plt.imread(png_path).shape
    audit.update(
        {
            "schema_version": "five_city_component_figure_audit_v1",
            "input": {
                "aggregate": str(INPUT_JSON.relative_to(SEMANTIC_TWIN)),
                "manifest": str(INPUT_MANIFEST.relative_to(SEMANTIC_TWIN)),
                "sha256": input_hash,
                "authenticated_against_manifest": True,
                "result_schema_version": manifest["result_schema_version"],
                "transport_topology": TRANSPORT_TOPOLOGY,
                "components": list(SEALED_COMPONENTS),
            },
            "figure": {
                "artifacts": {
                    "components.pdf": {
                        "bytes": pdf_path.stat().st_size,
                        "sha256": _sha256(pdf_path),
                    },
                    "components.png": {
                        "bytes": png_path.stat().st_size,
                        "height_px": int(png_shape[0]),
                        "sha256": _sha256(png_path),
                        "width_px": int(png_shape[1]),
                    },
                },
                "visual_encoding": {
                    "quantity": "per-standpoint component share of total raw transfer",
                    "order": list(COMPONENTS),
                    "zero_direct_marker": "hollow downward triangle",
                },
            },
            "computed_claims": {
                "standpoints_total": int(pooled.shape[0]),
                "pooled_median_component_share_percent": {
                    component: float(100.0 * np.median(pooled[:, index])) for index, component in enumerate(COMPONENTS)
                },
                "dominant_component_counts": {
                    component: int(np.count_nonzero(dominance == index)) for index, component in enumerate(COMPONENTS)
                },
                "first_diffuse_share_at_zero_direct_points_percent": float(100.0 * zero_diffuse_shares[0]),
                "interpretation": (
                    "Direct transfer is largest at all 67 nonshadowed standpoints. "
                    "First diffuse transfer alone carries the six zero-direct standpoints. "
                    "Exact order-1 specular transfer is not the largest component at any standpoint."
                ),
            },
        }
    )
    (HERE / "components.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    results, manifest, input_hash = _load_authenticated_results()
    arrays, audit = _validated_city_arrays(results)
    _plot(arrays)
    _write_audit(manifest, input_hash, arrays, audit)
    print(
        "Wrote components.pdf, components.png, and components.json from "
        f"{sum(array.shape[0] for array in arrays.values())} authenticated standpoints."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
