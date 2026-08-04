"""Sensitivity of street level exposure to how vegetation is treated.

The question this answers is not "what does foliage do at Korenmarkt", because
foliage is 2.0% of solid angle there and the answer is 2%. The question is at
what canopy fraction the three available treatments stop agreeing, so the ten
city acquisition can tell in advance which sites need a vegetation model and
which do not.

Three treatments, all run through the same estimator on the same geometry:

``cut``               vegetation deleted. The honest null.
``surface_specular``  the canopy hull kept as an opaque Fresnel surface with the
                      P.2040-4 ``wood`` row and the ``wood_cladding`` RMS height
                      of 0.05 mm. This is what the pipeline does today through
                      ``MATERIAL_SUBSTITUTION``, and at 15 GHz that surface is
                      radio-smooth, so the canopy behaves as a mirror.
``surface_diffuse``   the same row with a metre scale RMS height, so the hull
                      scatters diffusely. The charitable reading of the same
                      choice, since the photogrammetric blob really is lumpy at
                      half metre scale.
``medium``            the canopy hull kept as the boundary of a participating
                      medium with no dielectric interface, extinction, albedo
                      and two lobe phase function from Recommendation
                      ITU-R P.833-10 section 3.2.1.4.

Only the medium treatment has an optical depth, so only it is swept over one.

Stages
------
``sweep``  the canopy fraction by optical depth grid, writes ``sensitivity.json``
``leaf``   the half space against thin slab leaf reflectance, writes ``leaf.json``
``figure`` draws from whatever JSON exists

Run with no arguments to do all three.
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from semantic_twin import paths
from semantic_twin.materials.foliage import (
    LEAF_AREA_INDEX,
    CanopyCanyonGeometry,
    FoliageMedium,
    FoliageTracer,
    canopy_boundary_reflectance,
    figure2_specific_attenuation_db_per_m,
    leaf_reflectance_ratio_db,
    ret_parameter_envelope,
    ret_parameters,
)
from semantic_twin.illumination import MODELS

OUTPUT = paths.output("foliage_study")

#: The study band. 15 GHz sits in FR3 and is the tracer's own default carrier.
FREQUENCY_HZ = 15.0e9

#: Recommendation ITU-R P.2040-4 ``wood`` row evaluated at 15 GHz, which is what
#: ``semantic_twin.materials.catalogue`` substitutes for ``vegetation_effective``
#: today. eps_r = a = 1.99, sigma = c f_GHz^d = 0.0047 * 15^1.0718 S/m, and
#: eps_imag = sigma / (2 pi f eps_0).
WOOD_PERMITTIVITY_15GHZ = complex(1.99, -0.1005)

#: ``wood_cladding`` from ``config/surface_roughness.json``, 0.05 mm.
WOOD_RMS_M = 5.0e-5

#: The photogrammetric blob's own lumpiness. Half a metre is the scale at which
#: Photorealistic 3D Tiles resolves a canopy, so this is a geometry fact rather
#: than a material one, and it makes the hull fully diffuse at every frequency.
BLOB_RMS_M = 0.5

#: Ground and facade materials, held fixed so the only thing that moves is the
#: canopy. Concrete and asphalt at 15 GHz from ``config/itu_p2040_4.json``.
GROUND_PERMITTIVITY = complex(3.66, -0.09)
FACADE_PERMITTIVITY = complex(3.91, -0.14)
GROUND_RMS_M = 4.5e-4
FACADE_RMS_M = 3.0e-4

#: Measured at the two sites that exist. Vegetation share of classified solid
#: angle over the four horizontal crops of the fused fishnet vistas.
SITE_CANOPY_FRACTION = {"Korenmarkt": 0.020, "Milan Duomo": 0.009}

CANOPY_DEPTH_M = 6.0
CANOPY_BASE_M = 4.0
STREET_WIDTH_M = 18.0
OBSERVER = np.array([0.0, 0.0, 1.5])

OPTICAL_DEPTHS = (0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0)

#: Every trace evaluates all three at once, so this costs nothing extra. The
#: isotropic model is the one the figures use, because it is the only one whose
#: estimator variance is below 0.3% at the ray counts here. The two site models
#: put most of their weight within a few degrees of the horizon, where a canyon
#: lets almost nothing through, so a handful of grazing escapes carry the whole
#: estimate and the relative standard error stays near 2%. That is fine for a
#: 5 dB effect and not fine for a 0.5 dB threshold, so they are reported and
#: not used to set the thresholds.
ILLUMINATION = ("isotropic", "rooftop", "street_small_cell")

#: Canopy half widths in metres. The low end is fine because the two sites that
#: exist sit at 0.9% and 2.0% of solid angle and the threshold this study is
#: looking for is in the same decade.
HALF_WIDTHS_M = (0.0, 0.05, 0.1, 0.2, 0.35, 0.6, 1.0, 1.6, 2.6, 4.0, 6.0, 9.0)


def _geometry(half_width_m: float) -> CanopyCanyonGeometry:
    return CanopyCanyonGeometry(
        street_width_m=STREET_WIDTH_M,
        street_length_m=160.0,
        facade_height_m=18.0,
        canopy_half_width_m=half_width_m,
        canopy_base_m=CANOPY_BASE_M,
        canopy_depth_m=CANOPY_DEPTH_M,
    )


def _arrays(canopy_permittivity: complex, canopy_rms_m: float) -> tuple[np.ndarray, np.ndarray]:
    permittivity = np.array([GROUND_PERMITTIVITY, FACADE_PERMITTIVITY, FACADE_PERMITTIVITY, canopy_permittivity])
    rms = np.array([GROUND_RMS_M, FACADE_RMS_M, FACADE_RMS_M, canopy_rms_m])
    return permittivity, rms


def _trace(
    geometry: CanopyCanyonGeometry,
    *,
    medium: FoliageMedium | None,
    canopy_permittivity: complex,
    canopy_rms_m: float,
    rays: int,
    seed: int,
) -> dict:
    permittivity, rms = _arrays(canopy_permittivity, canopy_rms_m)
    tracer = FoliageTracer(
        geometry,
        permittivity=permittivity,
        rms_height_m=rms,
        frequency_hz=FREQUENCY_HZ,
        medium=medium,
        rays=rays,
        seed=seed,
    )
    result = tracer.trace(OBSERVER, {name: MODELS[name] for name in ILLUMINATION})
    return result.as_dict()


def stage_sweep(rays: int, seed: int) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    envelope = ret_parameter_envelope(FREQUENCY_HZ)
    reference = ret_parameters(FREQUENCY_HZ, species="london_plane", leaf_state="in_leaf")

    # The cut case has no canopy at all, so it does not depend on the canopy
    # half width and is run once at four times the rays rather than eleven
    # times at noise.
    cut = _trace(
        _geometry(0.0),
        medium=None,
        canopy_permittivity=WOOD_PERMITTIVITY_15GHZ,
        canopy_rms_m=WOOD_RMS_M,
        rays=4 * rays,
        seed=seed,
    )

    records: list[dict] = []
    for index, half_width in enumerate(HALF_WIDTHS_M):
        geometry = _geometry(half_width)
        # Canopy solid angle fraction is a property of the geometry alone, so it
        # is measured once with the canopy opaque and reused as the x axis for
        # every treatment including the one where the canopy is not there.
        probe = _trace(
            geometry,
            medium=None,
            canopy_permittivity=WOOD_PERMITTIVITY_15GHZ,
            canopy_rms_m=BLOB_RMS_M,
            rays=max(rays // 4, 20_000),
            seed=seed + 977,
        )
        fraction = probe["canopy_solid_angle_fraction"]

        records.append(
            {
                "treatment": "cut",
                "canopy_half_width_m": half_width,
                "canopy_fraction": fraction,
                "optical_depth": None,
                **cut,
            }
        )

        for label, rms_m in (("surface_specular", WOOD_RMS_M), ("surface_diffuse", BLOB_RMS_M)):
            surface = _trace(
                geometry,
                medium=None,
                canopy_permittivity=WOOD_PERMITTIVITY_15GHZ,
                canopy_rms_m=rms_m,
                rays=rays,
                seed=seed + index,
            )
            records.append(
                {
                    "treatment": label,
                    "canopy_half_width_m": half_width,
                    "canopy_fraction": fraction,
                    "optical_depth": None,
                    **surface,
                }
            )

        for tau in OPTICAL_DEPTHS:
            medium = FoliageMedium(
                extinction_per_m=tau / CANOPY_DEPTH_M,
                albedo=reference.albedo,
                forward_fraction=reference.alpha,
                phase_beamwidth_deg=reference.phase_beamwidth_deg,
                provenance=reference.provenance(),
            )
            traced = _trace(
                geometry,
                medium=medium,
                canopy_permittivity=WOOD_PERMITTIVITY_15GHZ,
                canopy_rms_m=WOOD_RMS_M,
                rays=rays,
                seed=seed + index,
            )
            records.append(
                {
                    "treatment": "medium",
                    "canopy_half_width_m": half_width,
                    "canopy_fraction": fraction,
                    "optical_depth": tau,
                    **traced,
                }
            )
        print(f"half width {half_width:5.2f} m -> canopy fraction {fraction:.4f}", flush=True)

    gamma = float(figure2_specific_attenuation_db_per_m(FREQUENCY_HZ))
    document = {
        "frequency_hz": FREQUENCY_HZ,
        "rays": rays,
        "seed": seed,
        "geometry": {
            "street_width_m": STREET_WIDTH_M,
            "facade_height_m": 18.0,
            "canopy_base_m": CANOPY_BASE_M,
            "canopy_depth_m": CANOPY_DEPTH_M,
            "observer_m": OBSERVER.tolist(),
        },
        "canopy_reference_parameters": reference.provenance()
        | {
            "alpha": reference.alpha,
            "phase_beamwidth_deg": reference.phase_beamwidth_deg,
            "albedo": reference.albedo,
            "sigma_tau_per_m": reference.sigma_tau_per_m,
            "implied_optical_depth_over_canopy_depth": reference.sigma_tau_per_m * CANOPY_DEPTH_M,
        },
        "p833_parameter_envelope_at_frequency": {k: list(v) for k, v in envelope.items()},
        "p833_envelope_optical_depth_over_canopy_depth": [
            envelope["sigma_tau_per_m"][0] * CANOPY_DEPTH_M,
            envelope["sigma_tau_per_m"][1] * CANOPY_DEPTH_M,
        ],
        "figure2_specific_attenuation_db_per_m": gamma,
        "figure2_implied_optical_depth_over_canopy_depth": gamma / 8.685889638065035 * CANOPY_DEPTH_M,
        "site_canopy_fraction": SITE_CANOPY_FRACTION,
        "records": records,
    }
    (OUTPUT / "sensitivity.json").write_text(json.dumps(document, indent=1))
    print(f"wrote {OUTPUT / 'sensitivity.json'} with {len(records)} records")


def stage_leaf() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    incidence = np.linspace(0.0, 85.0, 86)
    frequencies = [7.0e9, 15.0e9, 28.0e9]
    curves = {}
    for f in frequencies:
        r = leaf_reflectance_ratio_db(f, incidence)
        curves[f"{f / 1e9:g}"] = {
            "incidence_deg": incidence.tolist(),
            "half_space_reflectance": r["half_space_reflectance"].tolist(),
            "slab_reflectance": r["slab_reflectance"].tolist(),
            "excess_db": r["excess_db"].tolist(),
            "electrical_thickness_rad": r["electrical_thickness_rad"].tolist(),
            "permittivity": [float(np.real(r["permittivity"])), float(np.imag(r["permittivity"]))],
        }
    boundary = {species: canopy_boundary_reflectance(lai, CANOPY_DEPTH_M) for species, lai in LEAF_AREA_INDEX.items()}
    document = {
        "leaf_thickness_m": 2.0e-4,
        "leaf_thickness_source": "ITU-R P.833-10 Table 9, Boxtel oak, leaves 0.02 cm thick",
        "permittivity_source": "ITU-R P.833-10 Table 10, wood at 40% moisture and 20 C, a lower bound on a leaf",
        "curves": curves,
        "canopy_boundary_reflectance": boundary,
    }
    (OUTPUT / "leaf.json").write_text(json.dumps(document, indent=1))
    print(f"wrote {OUTPUT / 'leaf.json'}")


def _divergence(records: list[dict], model: str, tau: float) -> dict:
    """dB separation between treatments as a function of canopy fraction."""
    by_fraction: dict[float, dict[str, float]] = {}
    for record in records:
        if record["treatment"] == "medium" and record["optical_depth"] != tau:
            continue
        key = round(record["canopy_fraction"], 6)
        by_fraction.setdefault(key, {})[record["treatment"]] = record["susceptibility"][model]
    fractions = sorted(by_fraction)
    out: dict[str, list[float]] = {"canopy_fraction": fractions}
    for treatment in ("cut", "surface_specular", "surface_diffuse", "medium"):
        out[treatment] = [by_fraction[f].get(treatment, float("nan")) for f in fractions]
    for pair in (
        ("medium", "cut"),
        ("surface_specular", "cut"),
        ("surface_diffuse", "cut"),
        ("surface_specular", "medium"),
    ):
        a, b = pair
        out[f"{a}_vs_{b}_db"] = [
            float(10.0 * np.log10(x / y)) if (x > 0 and y > 0) else float("nan")
            for x, y in zip(out[a], out[b], strict=True)
        ]
    return out


def _threshold_crossing(fractions: list[float], separation: list[float], threshold_db: float) -> float | None:
    """Smallest canopy fraction at which |separation| first exceeds the threshold."""
    previous_f, previous_s = None, None
    for f, s in zip(fractions, separation, strict=True):
        if not np.isfinite(s):
            continue
        if abs(s) >= threshold_db:
            if previous_f is None or abs(previous_s) >= threshold_db:
                return float(f)
            span = abs(s) - abs(previous_s)
            if span <= 0.0:
                return float(f)
            return float(previous_f + (f - previous_f) * (threshold_db - abs(previous_s)) / span)
        previous_f, previous_s = f, s
    return None


def stage_figure() -> None:
    sys.path.insert(0, "/home/user/aegis/theory/scripts")
    import matplotlib.pyplot as plt
    from _plot_style import apply_monograph_style, fig_size_ieee

    apply_monograph_style()
    path = OUTPUT / "sensitivity.json"
    if not path.exists():
        print(f"missing {path}, run the sweep stage first")
        return
    document = json.loads(path.read_text())
    records = document["records"]
    model = "isotropic"
    reference_tau = 2.0

    curves = _divergence(records, model, reference_tau)
    envelope_low, envelope_high = document["p833_envelope_optical_depth_over_canopy_depth"]
    band_low = _divergence(records, model, min(OPTICAL_DEPTHS, key=lambda t: abs(t - envelope_low)))
    band_high = _divergence(records, model, min(OPTICAL_DEPTHS, key=lambda t: abs(t - envelope_high)))
    fractions = np.asarray(curves["canopy_fraction"])
    # The zero canopy point cannot be drawn on a log axis, and the interesting
    # decade is 0.5% to 40%, where both existing sites and the boulevards the
    # ten city set will add all sit.
    # The widest canopy spans the whole street and touches both facades, which
    # is a different geometry rather than a denser canopy, so it is measured
    # and kept in the JSON but not drawn.
    keep = (fractions > 0.0) & (fractions < 0.40)

    width, height = fig_size_ieee(columns=2, aspect=0.38)
    figure, axes = plt.subplots(1, 3, figsize=(width, height))

    colours = {
        "cut": "#444444",
        "surface_specular": "#c1272d",
        "surface_diffuse": "#e08a1e",
        "medium": "#1b6ca8",
    }
    labels = {
        "cut": "cut out (null)",
        "surface_specular": "surface, P.2040 wood, smooth",
        "surface_diffuse": "surface, P.2040 wood, lumpy",
        "medium": rf"medium, P.833 RET, $\tau$ = {reference_tau:g}",
    }

    def sites(ax: object, y: float) -> None:
        for name, value in document["site_canopy_fraction"].items():
            ax.axvline(100.0 * value, color="0.55", ls=":", lw=0.7)
            ax.annotate(name, (100.0 * value, y), rotation=90, fontsize=4.5, color="0.4", va="bottom", ha="right")

    ax = axes[0]
    ax.fill_between(
        100.0 * fractions[keep],
        np.asarray(band_low["medium"])[keep],
        np.asarray(band_high["medium"])[keep],
        color=colours["medium"],
        alpha=0.18,
        lw=0,
        label=r"medium, P.833 $\tau$ envelope",
    )
    for treatment in ("cut", "surface_specular", "surface_diffuse", "medium"):
        ax.plot(
            100.0 * fractions[keep],
            np.asarray(curves[treatment])[keep],
            color=colours[treatment],
            label=labels[treatment],
            marker="o",
            ms=2.2,
            lw=1.2,
        )
    ax.set_xscale("log")
    sites(ax, 0.002)
    ax.set_xlabel("canopy share of solid angle (%)")
    ax.set_ylabel(r"susceptibility $\chi$, isotropic")
    ax.set_title("(a) what the treatment costs", loc="left")
    ax.legend(fontsize=4.5, frameon=False, loc="lower left")

    ax = axes[1]
    for pair, style, colour in (
        (("medium", "cut"), "-", colours["medium"]),
        (("surface_specular", "cut"), "--", colours["surface_specular"]),
        (("surface_diffuse", "cut"), "-.", colours["surface_diffuse"]),
        (("surface_specular", "medium"), ":", "#6a3d9a"),
    ):
        a, b = pair
        values = np.abs(np.asarray(curves[f"{a}_vs_{b}_db"]))[keep]
        ax.plot(100.0 * fractions[keep], values, style, lw=1.2, color=colour, label=f"{a} vs {b}")
    for level, text in ((0.5, "0.5 dB"), (1.0, "1 dB")):
        ax.axhline(level, color="0.6", lw=0.7)
        ax.annotate(text, (12.0, level), fontsize=4.5, color="0.45", va="bottom")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_ylim(0.02, 30.0)
    sites(ax, 0.022)
    ax.set_xlabel("canopy share of solid angle (%)")
    ax.set_ylabel(r"$|10\log_{10}$ ratio$|$ (dB)")
    ax.set_title("(b) when the choice matters", loc="left")
    ax.legend(fontsize=4.5, frameon=False, loc="lower right")

    ax = axes[2]
    dense_fraction = sorted({r["canopy_fraction"] for r in records})[-3]
    dense = [r for r in records if abs(r["canopy_fraction"] - dense_fraction) < 1e-9]
    taus = [r["optical_depth"] for r in dense if r["treatment"] == "medium"]
    chis = [r["susceptibility"][model] for r in dense if r["treatment"] == "medium"]
    order = np.argsort(taus)
    ax.semilogx(
        np.asarray(taus)[order],
        np.asarray(chis)[order],
        color=colours["medium"],
        marker="o",
        ms=2.6,
        lw=1.3,
        label="medium",
    )
    for treatment in ("cut", "surface_specular", "surface_diffuse"):
        value = next(r["susceptibility"][model] for r in dense if r["treatment"] == treatment)
        ax.axhline(value, color=colours[treatment], ls="--", lw=1.0, label=labels[treatment])
    ax.axvspan(envelope_low, envelope_high, color="#1b6ca8", alpha=0.15, lw=0)
    top = ax.get_ylim()[1]
    ax.annotate(
        "P.833 Tables 5-8\nspread across species",
        (np.sqrt(envelope_low * envelope_high), 0.86 * top),
        fontsize=4.5,
        color="#1b6ca8",
        ha="center",
        va="top",
    )
    ax.axvline(document["figure2_implied_optical_depth_over_canopy_depth"], color="#1b6ca8", ls=":", lw=1.0)
    ax.annotate(
        "P.833 Fig. 2",
        (document["figure2_implied_optical_depth_over_canopy_depth"], 0.45 * top),
        fontsize=4.5,
        color="#1b6ca8",
        rotation=90,
        ha="right",
        va="center",
    )
    ax.set_xlabel(r"canopy optical depth $\tau$ over 6 m of canopy")
    ax.set_ylabel(r"susceptibility $\chi$, isotropic")
    ax.set_title(f"(c) at {100 * dense_fraction:.0f}% canopy", loc="left")
    ax.legend(fontsize=4.5, frameon=False, loc="lower left")

    figure.tight_layout(pad=0.4)
    for suffix in ("pdf", "png"):
        figure.savefig(OUTPUT / f"foliage_sensitivity.{suffix}", dpi=320)
    plt.close(figure)
    print(f"wrote {OUTPUT / 'foliage_sensitivity.pdf'}")

    summary = {
        "illumination_model": model,
        "illumination_models_reported": list(ILLUMINATION),
        "reference_optical_depth": reference_tau,
        "crossings": {},
    }
    for tau in OPTICAL_DEPTHS:
        c = _divergence(records, model, tau)
        f = c["canopy_fraction"]
        summary["crossings"][str(tau)] = {
            pair: {
                "0.5_dB": _threshold_crossing(f, c[f"{pair}_db"], 0.5),
                "1.0_dB": _threshold_crossing(f, c[f"{pair}_db"], 1.0),
                "max_db": float(np.nanmax(np.abs(c[f"{pair}_db"]))),
            }
            for pair in (
                "medium_vs_cut",
                "surface_specular_vs_cut",
                "surface_diffuse_vs_cut",
                "surface_specular_vs_medium",
            )
        }
    (OUTPUT / "crossings.json").write_text(json.dumps(summary, indent=1))
    print(f"wrote {OUTPUT / 'crossings.json'}")

    leaf_path = OUTPUT / "leaf.json"
    if not leaf_path.exists():
        return
    leaf = json.loads(leaf_path.read_text())
    width, height = fig_size_ieee(columns=1, aspect=0.7)
    figure, ax = plt.subplots(figsize=(width, height))
    for name, curve in leaf["curves"].items():
        ax.plot(curve["incidence_deg"], curve["excess_db"], lw=1.2, label=f"{name} GHz")
    ax.set_xlabel("incidence angle (deg)")
    ax.set_ylabel("half space over slab (dB)")
    ax.set_title("cost of modelling a leaf as a half space", loc="left")
    ax.legend(fontsize=6, frameon=False)
    figure.tight_layout(pad=0.4)
    for suffix in ("pdf", "png"):
        figure.savefig(OUTPUT / f"foliage_leaf_slab.{suffix}", dpi=320)
    plt.close(figure)
    print(f"wrote {OUTPUT / 'foliage_leaf_slab.pdf'}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stages", nargs="*", default=None, help="sweep, leaf, figure")
    parser.add_argument("--rays", type=int, default=400_000)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    stages = args.stages or ["sweep", "leaf", "figure"]
    if "sweep" in stages:
        stage_sweep(args.rays, args.seed)
    if "leaf" in stages:
        stage_leaf()
    if "figure" in stages:
        stage_figure()


if __name__ == "__main__":
    main()
