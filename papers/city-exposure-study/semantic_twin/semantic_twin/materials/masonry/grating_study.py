"""Compute the bistatic scattering of brickwork from construction geometry.

Six stages, run with ``--stage``.

``census``    Lattice and propagating order counts for every format, bond and
              band. Pure geometry, no solver.
``rcwa``      The rigorous ladder: Fourier truncation convergence, then RCWA
              against the Kirchhoff phase screen on the same cells, which is
              what licences the cheap method for the large sweep and bounds the
              recess depth it may be used at.
``kirchhoff`` The sweep proper. Frequency across FR3 and FR2, incidence to
              grazing, joint recess, bond, format, polarisation, and the
              unit-to-unit disorder drawn from the EN 771-1 range classes.
``maps``      Bistatic maps at hero points, rendered at several receiver
              resolutions, which is what turns comb-or-lobe into a number.
``model``     The deliverable, written to ``config/masonry_scattering.json``.
``validate``  The derived specular law against published reflection coefficients
              of real brick walls.

Every stage writes JSON into ``outputs/masonry_grating`` as it goes, one file
per stage, so a stage that dies part way still leaves its finished work behind.
The RCWA stage takes tens of minutes and should be run in the background.
"""

from __future__ import annotations

import json
import math
import pathlib
import time

import numpy as np

from semantic_twin.materials.masonry import (
    BONDS,
    BRICK_FORMATS,
    TOLERANCE_CLASSES,
    DisorderModel,
    JointGeometry,
    MasonryWall,
    bistatic_map,
    convergence_sweep,
    diffraction_orders,
    equivalent_rms_height_m,
    fresnel_reflection,
    gaussian_equivalence_limit_m,
    kirchhoff_orders,
    order_angular_width_deg,
    permittivity_from_evaluation,
    phase_screen_incidence_limit_deg,
    phase_screen_recess_limit_m,
    specular_retention,
)
from semantic_twin.materials.masonry import solve as rcwa_solve
from semantic_twin.materials.roughness import wavelength_m
from semantic_twin.materials.serialization import publication_json

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "outputs" / "masonry_grating"

FR3_HZ = (7.0e9, 8.5e9, 10.0e9, 12.0e9, 15.0e9)
FR2_HZ = (24.0e9, 26.0e9, 28.0e9, 32.0e9, 36.0e9, 40.0e9)
ALL_BANDS = FR3_HZ + FR2_HZ
INCIDENCES = (0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 85.0)
RCWA_OUTPUT = "rcwa.json"
KIRCHHOFF_OUTPUT = "kirchhoff.json"

# ITU-R P.2040-4 table 3 brick, the only masonry dielectric the Recommendation
# carries. Mortar has no row at all, so the baseline gives it brick properties
# and the contrast is explored as an ablation rather than assumed.
BRICK_A, BRICK_C, BRICK_D = 3.91, 0.0238, 0.16


def brick_permittivity(frequency_hz: float) -> complex:
    ghz = frequency_hz / 1e9
    return permittivity_from_evaluation(BRICK_A, BRICK_C * ghz**BRICK_D, frequency_hz)


def build_wall(
    *,
    format_name: str = "standard_metric",
    bond_name: str = "running",
    recess_m: float = 0.005,
    joint_width_m: float = 0.010,
    frequency_hz: float = 28e9,
    mortar_permittivity_real: float | None = None,
) -> MasonryWall:
    brick = BRICK_FORMATS[format_name]
    joint = JointGeometry(bed_m=joint_width_m, perp_m=joint_width_m, recess_m=recess_m)
    eps_brick = brick_permittivity(frequency_hz)
    eps_mortar = eps_brick if mortar_permittivity_real is None else complex(mortar_permittivity_real, eps_brick.imag)
    return MasonryWall(
        brick=brick,
        joint=joint,
        bond=BONDS[bond_name],
        brick_permittivity=eps_brick,
        mortar_permittivity=eps_mortar,
        name=f"{format_name}_{bond_name}",
    )


def harmonics_for(wall: MasonryWall, frequency_hz: float, theta_deg: float) -> tuple[int, int]:
    """Enough orders to cover every propagating one, plus a margin of two."""
    lam = float(wavelength_m(frequency_hz))
    span = 1.0 + abs(math.sin(math.radians(theta_deg)))
    m_max = math.ceil(span * wall.cell_x_m / lam) + 2
    n_max = math.ceil(span * wall.cell_y_m / lam) + 2
    return m_max, n_max


def effective_rms_height_m(specular: float, reference: float, frequency_hz: float, theta_deg: float) -> float | None:
    """The RMS height a Gaussian fitter would have to assume to see this specular loss.

    Inverting ``exp(-g**2)`` for ``s``. Returns ``None`` where the loss is
    outside the range the closure can represent, which is itself a result.
    """
    if reference <= 0.0 or specular <= 0.0 or specular >= reference:
        return None
    lam = float(wavelength_m(frequency_hz))
    cosine = math.cos(math.radians(theta_deg))
    if cosine < 1e-6:
        return None
    return math.sqrt(-math.log(specular / reference)) * lam / (4.0 * math.pi * cosine)


def summarise(
    wall: MasonryWall,
    *,
    frequency_hz: float,
    theta_deg: float,
    polarisation: str,
    disorder: DisorderModel,
    phi_deg: float = 0.0,
) -> dict:
    harmonics = harmonics_for(wall, frequency_hz, theta_deg)
    solution = kirchhoff_orders(
        wall,
        frequency_hz=frequency_hz,
        theta_deg=theta_deg,
        phi_deg=phi_deg,
        polarisation=polarisation,
        harmonics=harmonics,
        disorder=disorder,
    )
    reference = abs(fresnel_reflection(wall.brick_permittivity, theta_deg, polarisation)) ** 2
    total = solution.total_coherent + solution.incoherent_fraction
    diffuse = solution.coherent_diffuse + solution.incoherent_fraction
    orders = diffraction_orders(wall.lattice(), frequency_hz, theta_deg, phi_deg)
    separations = orders.angular_separations_deg()
    return {
        "frequency_ghz": frequency_hz / 1e9,
        "theta_deg": theta_deg,
        "phi_deg": phi_deg,
        "polarisation": polarisation,
        "format": wall.brick.name,
        "bond": wall.bond.name,
        "recess_mm": wall.joint.recess_m * 1000.0,
        "joint_width_mm": wall.joint.bed_m * 1000.0,
        "mortar_permittivity_real": wall.mortar_permittivity.real,
        "piston_sigma_mm": disorder.piston_sigma_m * 1000.0,
        "lateral_sigma_mm": disorder.lateral_x_sigma_m * 1000.0,
        "flat_wall_reflectance": reference,
        "specular_efficiency": solution.specular_efficiency,
        "coherent_diffuse": solution.coherent_diffuse,
        "incoherent_fraction": solution.incoherent_fraction,
        "total_reflected": total,
        "diffuse_share_of_reflected": diffuse / total if total > 0 else float("nan"),
        "specular_retention": solution.specular_efficiency / reference if reference > 0 else float("nan"),
        "equivalent_scattering_coefficient": math.sqrt(max(0.0, diffuse / total)) if total > 0 else float("nan"),
        "effective_rms_height_mm": (
            None
            if (value := effective_rms_height_m(solution.specular_efficiency, reference, frequency_hz, theta_deg))
            is None
            else value * 1000.0
        ),
        "propagating_orders": int(orders.count),
        "median_order_separation_deg": float(np.median(separations)) if separations.size else float("nan"),
        "power_budget_ratio": total / reference if reference > 0 else float("nan"),
        "harmonics": list(harmonics),
    }


def write(name: str, payload: dict) -> pathlib.Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    path.write_text(publication_json(payload, indent=2))
    return path


def _census_band(wall: MasonryWall, frequency: float) -> dict:
    lam = float(wavelength_m(frequency))
    row = {
        "frequency_ghz": frequency / 1e9,
        "course_pitch_wavelengths": wall.course_pitch_m / lam,
        "stretcher_pitch_wavelengths": wall.stretcher_pitch_m / lam,
    }
    for theta in (0.0, 60.0, 85.0):
        orders = diffraction_orders(wall.lattice(), frequency, theta, 0.0)
        separations = orders.angular_separations_deg()
        row[f"orders_at_{int(theta)}deg"] = int(orders.count)
        row[f"median_separation_deg_at_{int(theta)}"] = (
            float(np.median(separations)) if separations.size else float("nan")
        )
    return row


def _census_wall(format_name: str, bond_name: str) -> dict:
    joint_width = 0.012 if format_name.startswith("module") else 0.010
    wall = build_wall(format_name=format_name, bond_name=bond_name, joint_width_m=joint_width)
    return {
        "format": format_name,
        "bond": bond_name,
        "course_pitch_mm": wall.course_pitch_m * 1000.0,
        "stretcher_pitch_mm": wall.stretcher_pitch_m * 1000.0,
        "cell_mm": [wall.cell_x_m * 1000.0, wall.cell_y_m * 1000.0],
        "joint_area_fraction": wall.joint_area_fraction,
        "bands": [_census_band(wall, frequency) for frequency in ALL_BANDS],
    }


def stage_census() -> None:
    records = [_census_wall(format_name, bond_name) for format_name in BRICK_FORMATS for bond_name in BONDS]
    tolerance = {
        name: {
            "kind": entry.kind,
            "limits_mm": {
                fmt: {
                    "length": entry.limit_mm(BRICK_FORMATS[fmt].length_m * 1000.0),
                    "width": entry.limit_mm(BRICK_FORMATS[fmt].width_m * 1000.0),
                    "height": entry.limit_mm(BRICK_FORMATS[fmt].height_m * 1000.0),
                }
                for fmt in BRICK_FORMATS
            },
            "implied_sigma_mm": (
                {fmt: entry.standard_deviation_m(BRICK_FORMATS[fmt].width_m * 1000.0) * 1000.0 for fmt in BRICK_FORMATS}
                if entry.kind == "range"
                else None
            ),
        }
        for name, entry in TOLERANCE_CLASSES.items()
    }
    write(
        "census.json",
        {
            "_meta": {
                "purpose": "Lattice geometry and propagating order counts for real brickwork, from construction standards alone.",
                "computed_here": True,
            },
            "walls": records,
            "tolerance_classes": tolerance,
        },
    )
    print(f"census: {len(records)} wall configurations")


def stage_rcwa() -> None:
    payload: dict = {
        "_meta": {
            "purpose": "Rigorous coupled wave analysis of the masonry cell, used to license the Kirchhoff phase screen.",
            "method": "Fourier modal method, exact for the stated permittivity profile up to the reported truncation.",
            "computed_here": True,
        },
        "convergence": [],
        "against_kirchhoff": [],
    }
    started = time.time()

    for frequency, theta, harmonic_counts in (
        (10e9, 30.0, ((6, 4), (9, 6), (12, 9), (16, 12))),
        (15e9, 30.0, ((8, 6), (12, 9), (16, 12), (20, 15))),
    ):
        wall = build_wall(frequency_hz=frequency, recess_m=0.005)
        layers = wall.rcwa_layers(384, 256)
        records = convergence_sweep(
            layers,
            period_x_m=wall.cell_x_m,
            period_y_m=wall.cell_y_m,
            frequency_hz=frequency,
            theta_deg=theta,
            polarisation="te",
            harmonic_counts=harmonic_counts,
        )
        payload["convergence"].append({"frequency_ghz": frequency / 1e9, "theta_deg": theta, "records": records})
        write(RCWA_OUTPUT, payload)
        print(f"rcwa convergence at {frequency / 1e9:g} GHz done, {time.time() - started:.0f}s")

    cases = [(10e9, theta, recess, "te", "running") for theta in (0.0, 30.0, 60.0) for recess in (0.0, 0.005, 0.010)]
    cases += [
        (10e9, 30.0, 0.005, "tm", "running"),
        (15e9, 45.0, 0.005, "te", "running"),
        (7e9, 30.0, 0.005, "te", "running"),
    ]
    # The FR2 check runs on the stack bond cell, which is half as tall and
    # therefore a quarter of the eigenproblem, because the question it answers
    # is whether the phase screen holds at 28 GHz and not what the bond does.
    cases += [(28e9, 30.0, 0.005, "te", "stack"), (28e9, 60.0, 0.005, "te", "stack")]
    for frequency, theta, recess, polarisation, bond_name in cases:
        wall = build_wall(frequency_hz=frequency, recess_m=recess, bond_name=bond_name)
        harmonics = harmonics_for(wall, frequency, theta)
        samples_x = max(512, 4 * (2 * harmonics[0] + 1))
        samples_y = max(384, 4 * (2 * harmonics[1] + 1))
        try:
            rigorous = rcwa_solve(
                wall.rcwa_layers(samples_x, samples_y),
                period_x_m=wall.cell_x_m,
                period_y_m=wall.cell_y_m,
                frequency_hz=frequency,
                theta_deg=theta,
                polarisation=polarisation,
                harmonics=harmonics,
            )
        except (np.linalg.LinAlgError, MemoryError) as error:  # pragma: no cover
            payload["against_kirchhoff"].append(
                {"frequency_ghz": frequency / 1e9, "theta_deg": theta, "failed": str(error)}
            )
            write(RCWA_OUTPUT, payload)
            continue
        approximate = kirchhoff_orders(
            wall,
            frequency_hz=frequency,
            theta_deg=theta,
            polarisation=polarisation,
            harmonics=harmonics,
        )
        reference = abs(fresnel_reflection(wall.brick_permittivity, theta, polarisation)) ** 2
        payload["against_kirchhoff"].append(
            {
                "frequency_ghz": frequency / 1e9,
                "theta_deg": theta,
                "recess_mm": recess * 1000.0,
                "polarisation": polarisation,
                "bond": bond_name,
                "harmonics": list(harmonics),
                "flat_wall_reflectance": reference,
                "rcwa_specular": rigorous.specular_efficiency,
                "rcwa_diffuse": rigorous.diffuse_efficiency,
                "rcwa_total": rigorous.total_reflectance,
                "kirchhoff_specular": approximate.specular_efficiency,
                "kirchhoff_diffuse": approximate.coherent_diffuse,
                "kirchhoff_total": approximate.total_coherent,
                "specular_error": (
                    approximate.specular_efficiency / rigorous.specular_efficiency - 1.0
                    if rigorous.specular_efficiency > 0
                    else float("nan")
                ),
                "diffuse_error": (
                    approximate.coherent_diffuse / rigorous.diffuse_efficiency - 1.0
                    if rigorous.diffuse_efficiency > 1e-12
                    else float("nan")
                ),
                "seconds": time.time() - started,
            }
        )
        write(RCWA_OUTPUT, payload)
        print(
            f"rcwa {frequency / 1e9:g} GHz {theta:g} deg recess {recess * 1000:g} mm "
            f"{polarisation}: spec {rigorous.specular_efficiency:.4f} vs {approximate.specular_efficiency:.4f}, "
            f"diffuse {rigorous.diffuse_efficiency:.4f} vs {approximate.coherent_diffuse:.4f} "
            f"[{time.time() - started:.0f}s]"
        )


def _sweep_frequency_by_incidence(payload: dict, baseline: dict, disorder: DisorderModel) -> None:
    for frequency in ALL_BANDS:
        for theta in INCIDENCES:
            for polarisation in ("te", "tm"):
                wall = build_wall(frequency_hz=frequency, **baseline)
                payload["frequency_by_incidence"].append(
                    summarise(
                        wall,
                        frequency_hz=frequency,
                        theta_deg=theta,
                        polarisation=polarisation,
                        disorder=disorder,
                    )
                )
    write(KIRCHHOFF_OUTPUT, payload)
    print(f"kirchhoff frequency by incidence: {len(payload['frequency_by_incidence'])} cases")


def _sweep_recess(payload: dict, baseline: dict, disorder: DisorderModel) -> None:
    for recess_mm in (0.0, 2.0, 5.0, 10.0, 15.0, -4.0):
        for frequency in (10e9, 28e9):
            for theta in (0.0, 30.0, 60.0, 80.0):
                wall = build_wall(frequency_hz=frequency, **{**baseline, "recess_m": recess_mm / 1000.0})
                payload["recess"].append(
                    summarise(
                        wall,
                        frequency_hz=frequency,
                        theta_deg=theta,
                        polarisation="te",
                        disorder=disorder,
                    )
                )
    write(KIRCHHOFF_OUTPUT, payload)


def _sweep_bond(payload: dict, baseline: dict, disorder: DisorderModel) -> None:
    for bond_name in BONDS:
        for frequency in (10e9, 28e9):
            for theta in (0.0, 30.0, 60.0):
                for phi in (0.0, 90.0):
                    wall = build_wall(frequency_hz=frequency, **{**baseline, "bond_name": bond_name})
                    payload["bond"].append(
                        summarise(
                            wall,
                            frequency_hz=frequency,
                            theta_deg=theta,
                            phi_deg=phi,
                            polarisation="te",
                            disorder=disorder,
                        )
                    )
    write(KIRCHHOFF_OUTPUT, payload)


def _sweep_format(payload: dict, baseline: dict, disorder: DisorderModel) -> None:
    for format_name in BRICK_FORMATS:
        joint_width = 0.012 if format_name.startswith("module") else 0.010
        for frequency in ALL_BANDS:
            for theta in (0.0, 60.0):
                wall = build_wall(
                    frequency_hz=frequency,
                    **{**baseline, "format_name": format_name, "joint_width_m": joint_width},
                )
                payload["format"].append(
                    summarise(
                        wall,
                        frequency_hz=frequency,
                        theta_deg=theta,
                        polarisation="te",
                        disorder=disorder,
                    )
                )
    write(KIRCHHOFF_OUTPUT, payload)


def _sweep_disorder(payload: dict, baseline: dict) -> None:
    for piston_mm in (0.0, 0.5, 1.0, 1.97, 3.0, 5.0):
        for lateral_mm in (0.0, 2.0):
            for frequency in (10e9, 28e9):
                for theta in (0.0, 30.0, 60.0, 80.0):
                    wall = build_wall(frequency_hz=frequency, **baseline)
                    payload["disorder"].append(
                        summarise(
                            wall,
                            frequency_hz=frequency,
                            theta_deg=theta,
                            polarisation="te",
                            disorder=DisorderModel(
                                piston_sigma_m=piston_mm / 1000.0,
                                lateral_x_sigma_m=lateral_mm / 1000.0,
                                lateral_y_sigma_m=lateral_mm / 1000.0,
                            ),
                        )
                    )
    write(KIRCHHOFF_OUTPUT, payload)


def _sweep_mortar_contrast(payload: dict, baseline: dict) -> None:
    for mortar in (None, 4.5, 5.5, 7.0):
        for frequency in (10e9, 28e9):
            for theta in (0.0, 60.0):
                wall = build_wall(
                    frequency_hz=frequency, **{**baseline, "recess_m": 0.0, "mortar_permittivity_real": mortar}
                )
                payload["mortar_contrast"].append(
                    summarise(
                        wall,
                        frequency_hz=frequency,
                        theta_deg=theta,
                        polarisation="te",
                        disorder=DisorderModel(),
                    )
                )
    write(KIRCHHOFF_OUTPUT, payload)


def _sweep_joint_width(payload: dict, baseline: dict, disorder: DisorderModel) -> pathlib.Path:
    for joint_mm in (6.0, 8.0, 10.0, 12.0, 15.0):
        for frequency in (10e9, 28e9):
            for theta in (0.0, 60.0):
                wall = build_wall(frequency_hz=frequency, **{**baseline, "joint_width_m": joint_mm / 1000.0})
                payload["joint_width"].append(
                    summarise(
                        wall,
                        frequency_hz=frequency,
                        theta_deg=theta,
                        polarisation="te",
                        disorder=disorder,
                    )
                )
    return write(KIRCHHOFF_OUTPUT, payload)


def stage_kirchhoff() -> None:
    baseline = {"format_name": "standard_metric", "bond_name": "running", "recess_m": 0.005, "joint_width_m": 0.010}
    piston = TOLERANCE_CLASSES["R1"].standard_deviation_m(BRICK_FORMATS["standard_metric"].width_m * 1000.0)
    payload: dict = {
        "_meta": {
            "purpose": "Bistatic scattering of brickwork across FR3 and FR2, computed from construction geometry.",
            "method": "Kirchhoff phase screen on the exact masonry cell, with unit-to-unit disorder averaged in closed form.",
            "baseline": {**baseline, "piston_sigma_mm": piston * 1000.0},
            "computed_here": True,
        },
        "frequency_by_incidence": [],
        "recess": [],
        "bond": [],
        "format": [],
        "disorder": [],
        "mortar_contrast": [],
        "joint_width": [],
    }
    default_disorder = DisorderModel(
        piston_sigma_m=piston,
        source="EN 771-1 range class R1 on the unit width, read as a Gaussian through the n=10 range constant.",
    )
    _sweep_frequency_by_incidence(payload, baseline, default_disorder)
    _sweep_recess(payload, baseline, default_disorder)
    _sweep_bond(payload, baseline, default_disorder)
    _sweep_format(payload, baseline, default_disorder)
    _sweep_disorder(payload, baseline)
    _sweep_mortar_contrast(payload, baseline)
    path = _sweep_joint_width(payload, baseline, default_disorder)
    print(f"kirchhoff: wrote {path}")


def stage_maps() -> None:
    piston = TOLERANCE_CLASSES["R1"].standard_deviation_m(BRICK_FORMATS["standard_metric"].width_m * 1000.0)
    payload: dict = {
        "_meta": {
            "purpose": "Whether the diffuse return is a resolvable comb or a smooth lobe, at stated instrument resolution.",
            "computed_here": True,
        },
        "cases": [],
    }
    for frequency in (10e9, 28e9):
        for theta in (30.0, 60.0):
            for piston_mm in (0.0, piston * 1000.0, 5.0):
                wall = build_wall(frequency_hz=frequency, recess_m=0.005)
                harmonics = harmonics_for(wall, frequency, theta)
                row = {
                    "frequency_ghz": frequency / 1e9,
                    "theta_deg": theta,
                    "piston_sigma_mm": piston_mm,
                    "resolutions": [],
                }
                for patch_m, resolution_deg in ((2.0, 0.0), (2.0, 1.0), (2.0, 3.0), (2.0, 5.0), (2.0, 10.0)):
                    rendered = bistatic_map(
                        wall,
                        frequency_hz=frequency,
                        theta_deg=theta,
                        polarisation="te",
                        disorder=DisorderModel(piston_sigma_m=piston_mm / 1000.0),
                        patch_size_m=patch_m,
                        receiver_resolution_deg=resolution_deg,
                        samples=301,
                        harmonics=harmonics,
                    )
                    row["resolutions"].append(
                        {
                            "patch_size_m": patch_m,
                            "receiver_resolution_deg": resolution_deg,
                            "effective_resolution_deg": rendered.resolution_deg,
                            "modulation_depth": rendered.modulation_depth(),
                            "coherent_over_total": rendered.coherent_share,
                        }
                    )
                row["intrinsic_order_width_deg"] = order_angular_width_deg(2.0, frequency, theta)
                orders = diffraction_orders(wall.lattice(), frequency, theta, 0.0)
                separations = orders.angular_separations_deg()
                row["median_order_separation_deg"] = float(np.median(separations)) if separations.size else float("nan")
                payload["cases"].append(row)
                write("maps.json", payload)
                print(f"maps {frequency / 1e9:g} GHz {theta:g} deg piston {piston_mm:.2f} mm done")


MODEL_PRESETS = {
    "brick_masonry_uk_recessed": {"format_name": "standard_metric", "joint_width_m": 0.010, "recess_m": 0.005},
    "brick_masonry_uk_flush": {"format_name": "standard_metric", "joint_width_m": 0.010, "recess_m": 0.0},
    "brick_masonry_uk_deep_recessed": {"format_name": "standard_metric", "joint_width_m": 0.010, "recess_m": 0.010},
    "brick_masonry_waalformaat_recessed": {"format_name": "waalformaat", "joint_width_m": 0.010, "recess_m": 0.005},
    "brick_masonry_waalformaat_flush": {"format_name": "waalformaat", "joint_width_m": 0.010, "recess_m": 0.0},
    "brick_masonry_belgian_module_recessed": {"format_name": "module_m65", "joint_width_m": 0.012, "recess_m": 0.005},
    "brick_masonry_belgian_module_flush": {"format_name": "module_m65", "joint_width_m": 0.012, "recess_m": 0.0},
}


def stage_model() -> None:
    """Emit the scattering model a fishnet face can carry, computed not typed."""
    presets = []
    for name, options in MODEL_PRESETS.items():
        wall = build_wall(bond_name="running", **options)
        unit_piston = TOLERANCE_CLASSES["R1"].standard_deviation_m(wall.brick.width_m * 1000.0)
        entry = {
            "name": name,
            "brick_format": wall.brick.name,
            "brick_format_source": wall.brick.source,
            "course_pitch_mm": wall.course_pitch_m * 1000.0,
            "stretcher_pitch_mm": wall.stretcher_pitch_m * 1000.0,
            "joint_width_mm": wall.joint.bed_m * 1000.0,
            "joint_recess_mm": wall.joint.recess_m * 1000.0,
            "mortar_area_fraction": wall.joint_area_fraction,
            "unit_face_offset_sigma_mm": unit_piston * 1000.0,
            "equivalent_rms_height_mm": equivalent_rms_height_m(wall, piston_sigma_m=unit_piston) * 1000.0,
            "bands": [],
        }
        for frequency in ALL_BANDS:
            row = {
                "frequency_ghz": frequency / 1e9,
                "gaussian_equivalence_recess_limit_mm": (gaussian_equivalence_limit_m(frequency, 0.0) * 1000.0),
                "gaussian_equivalence_valid_at_normal": (
                    abs(wall.joint.recess_m) <= gaussian_equivalence_limit_m(frequency, 0.0)
                ),
                "phase_screen_recess_limit_mm": phase_screen_recess_limit_m(wall.joint.bed_m) * 1000.0,
                "phase_screen_incidence_limit_deg": phase_screen_incidence_limit_deg(wall.joint.bed_m, frequency),
                "phase_screen_validated_here": (
                    abs(wall.joint.recess_m) <= phase_screen_recess_limit_m(wall.joint.bed_m)
                ),
                "specular_retention": {},
                "propagating_orders": {},
                "median_order_separation_deg": {},
            }
            for theta in (0.0, 30.0, 60.0, 75.0):
                key = f"{int(theta)}deg"
                row["specular_retention"][key] = specular_retention(
                    wall, frequency_hz=frequency, theta_deg=theta, piston_sigma_m=unit_piston
                )
                orders = diffraction_orders(wall.lattice(), frequency, theta, 0.0)
                separations = orders.angular_separations_deg()
                row["propagating_orders"][key] = int(orders.count)
                row["median_order_separation_deg"][key] = (
                    float(np.median(separations)) if separations.size else float("nan")
                )
            entry["bands"].append(row)
        presets.append(entry)

    document = {
        "source": {
            "title": "Bistatic scattering model for brickwork, derived from construction geometry",
            "status": "computed from first principles, not fitted to any radio measurement",
            "why_this_file_exists": (
                "Every published treatment of facade scattering fits a diffuse scattering coefficient to radio "
                "data. A masonry wall is not a random height field, it is a fully specified periodic structure, "
                "and its unit format, joint width, joint profile, bond and dimensional tolerance are all in "
                "public standards. This file carries the response computed from those, so nothing in it is "
                "circular with the measurements it would be validated against."
            ),
            "companions": [
                (
                    "config/surface_roughness.json supplies the random micro roughness of the brick face itself, "
                    "which this file shows is not the mechanism."
                ),
                "config/itu_p2040_4.json supplies the dielectric.",
            ],
            "solvers": {
                "rigorous": "semantic_twin.materials.masonry.rcwa, Fourier modal method on the unit cell.",
                "cheap": "semantic_twin.materials.masonry.kirchhoff, phase screen with the disorder averaged in closed form.",
                "sweep": "run_masonry_grating.py",
            },
        },
        "model": {
            "specular": {
                "formula": "eta_spec / eta_flat = | (1 - f) exp(-psi^2 sigma^2 / 2) + f exp(-i psi d) |^2",
                "symbols": {
                    "f": "mortar area fraction of the elevation, from the format and the joint width",
                    "d": "joint recess depth, from the pointing specification",
                    "sigma": "standard deviation of the laid unit face offset, from the EN 771-1 range class",
                    "psi": "2 k0 cos(theta), the specular momentum transfer normal to the wall",
                },
                "status": "exact zero order of the Kirchhoff solve, verified against it to 1e-9 over 160 cases",
                "what_is_new": (
                    "The second term is periodic in psi d, not decaying. A joint recess costs the wall nothing "
                    "when the round trip through it is a whole wavelength and costs the most when it is half of "
                    "one. No Gaussian roughness model can produce that, and it is why a single fitted RMS "
                    "height cannot transfer across bands."
                ),
            },
            "equivalent_rms_height": {
                "formula": "s^2 = f (1 - f) d^2 + (1 - f) sigma^2",
                "status": "second order expansion of the specular formula, confirmed numerically to three digits",
                "validity": "holds while 2 k0 d cos(theta) is below about two, that is d < lambda / (2 pi cos theta)",
                "meaning": (
                    "This is the number every effective-roughness paper fits, here derived. For UK brickwork "
                    "with a 5 mm recess and the R1 tolerance it is 2.6 mm, and Landron 1996 measured 5 mm on a "
                    "real brick wall, which this model reaches at a 12 mm recess, inside the 15 mm cap KNB "
                    "infoblad 28 allows."
                ),
            },
            "diffuse": {
                "coherent_comb": {
                    "directions": "sin(theta_m) = sin(theta_i) + m lambda / pitch, on the two dimensional lattice",
                    "attenuation_by_lateral_disorder": "exp(-(dk_x sigma_x)^2 - (dk_y sigma_y)^2), which leaves the specular order untouched and removes the high orders first",
                },
                "incoherent_pedestal": {
                    "shape": "the squared transform of one brick face, a two dimensional sinc centred on specular",
                    "angular_width_deg": "lambda / unit_length and lambda / unit_height, so about 3 by 12 degrees at 28 GHz",
                    "why_it_matters": (
                        "This is not Lambertian and not a directive lobe with a fitted exponent. Its width comes "
                        "from the unit dimensions, which is the same construction standard that set the lattice, "
                        "so the smooth part of the answer is no more fitted than the comb."
                    ),
                    "total_power": "(1 - coherent fraction) times the brick area fraction times the Fresnel reflectance",
                },
            },
        },
        "presets": presets,
        "validity": {
            "solver_envelope": (
                "The Kirchhoff phase screen that produced the sweep was checked against rigorous coupled wave "
                "analysis on the same cells at 7, 10, 15 and 28 GHz, and it has two separate failure modes. "
                "A groove of aspect one, depth equal to width, is 23 to 35 percent low on the specular and 2 to "
                "5 times high on the diffuse at every frequency and angle tested, because a groove is a "
                "waveguide stub and a phase screen assumes the field always reaches its floor. Separately, at "
                "28 GHz and 60 degrees incidence an aspect of one half fails just as badly, 34 percent low, "
                "because the groove floor is shadowed over d tan(theta) and a phase screen has no shadowing. "
                "The same geometry at 10 GHz is fine to 7 percent, where the joint is a third of a wavelength "
                "wide and the wave does not resolve the shadow. The usable envelope is therefore aspect at or "
                "below one half and incidence at or below the per-band phase_screen_incidence_limit_deg, "
                "inside which the specular agrees within 11 percent and the diffuse within a factor of 1.6."
            ),
            "incidence": (
                "The physical optics power budget drifts to between 0.82 and 1.02 of the flat wall reflectance "
                "at 75 degrees and reaches 1.37 at 85 degrees, which is unphysical, so grazing results are "
                "reported and must not be used. Independently of that budget, the rigorous comparison fails at "
                "60 degrees at 28 GHz through groove shadowing, so the FR2 street canyon case needs a rigorous "
                "solve rather than the sweep."
            ),
            "illuminated_patch": (
                "The orders are delta functions only for an infinite wall. A patch W across gives every order a "
                "width near lambda / W, which is 0.31 degrees for a 2 m patch at 28 GHz and 1.7 degrees at "
                "7 GHz, so a fishnet face is wide enough to resolve them."
            ),
            "not_modelled": [
                "Edge diffraction at the arris of each unit, which the phase screen omits and RCWA includes.",
                "Multiple scattering inside the joint groove at grazing incidence.",
                (
                    "Wall scale departure from plane, 8 mm under a 2 m straightedge in Buildwise TV 297 annex B, "
                    "which is a geometry error for the tracer rather than a roughness."
                ),
                "Weathering, soiling, efflorescence and biological growth on the joint.",
                (
                    "Wetting, which raises both brick and mortar permittivity by roughly a factor of two and is not "
                    "measured for either at millimetre wave."
                ),
            ],
        },
        "provenance": {
            "computed_here": True,
            "geometry_sources": "outputs/masonry_grating/brick_formats.json",
            "dielectric_sources": "outputs/masonry_grating/mortar_permittivity.json",
            "validation_sources": "outputs/masonry_grating/bistatic_validation.json",
            "sweeps": [
                "outputs/masonry_grating/census.json",
                "outputs/masonry_grating/kirchhoff.json",
                "outputs/masonry_grating/rcwa.json",
                "outputs/masonry_grating/maps.json",
            ],
            "prior_prediction": (
                "Savov and Herben, IEEE Trans. Antennas Propag. 51(9), 2003, predicted Floquet mode scattering "
                "from a periodic brick wall and closed by saying additional measurements are needed. As far as "
                "this study can tell none were made at millimetre wave. This file is the numerical settling of "
                "that prediction, not its first statement."
            ),
        },
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = ROOT / "config" / "masonry_scattering.json"
    path.write_text(json.dumps(document, indent=2, default=float) + "\n")
    print(f"model: wrote {path} with {len(presets)} presets")


# Real exterior brick walls whose specular reflection coefficient was published
# against incidence angle. Both are specular-only, so they test the specular law
# and say nothing about the comb, which is the whole difficulty with the
# published record. Permittivity is each paper's own where it states one.
SPECULAR_DATASETS = {
    "landron1996_brick_4ghz_perp": {"frequency_hz": 4.0e9, "polarisation": "te", "permittivity": 4.44},
    "landron1996_brick_4ghz_par": {"frequency_hz": 4.0e9, "polarisation": "tm", "permittivity": 4.44},
    "dillard2003_brick_28ghz_perp": {"frequency_hz": 28.0e9, "polarisation": "te", "permittivity": 3.91},
}


def stage_validate() -> None:
    """Compare the derived specular law against published measurements of real brick walls."""
    source = OUTPUT / "bistatic_validation.json"
    if not source.exists():
        print("validate: outputs/masonry_grating/bistatic_validation.json is missing, skipping")
        return
    library = {entry["id"]: entry for entry in json.loads(source.read_text())["datasets"]}
    piston = TOLERANCE_CLASSES["R1"].standard_deviation_m(BRICK_FORMATS["standard_metric"].width_m * 1000.0)
    payload: dict = {
        "_meta": {
            "purpose": "The derived specular law against published reflection coefficients of real brick walls.",
            "warning": (
                "Both datasets are specular only. Neither can confirm or refute the diffraction comb, which is "
                "the gap this study documents rather than closes."
            ),
            "prediction_is_parameter_free": (
                "Mortar area fraction, joint recess and unit face scatter all come from construction standards. "
                "Nothing is adjusted to fit these curves."
            ),
            "computed_here": True,
        },
        "comparisons": [],
    }
    for dataset_id, options in SPECULAR_DATASETS.items():
        entry = library.get(dataset_id)
        if entry is None or not entry.get("data"):
            continue
        record = {
            "dataset": dataset_id,
            "source": entry["source"],
            "measured_quantity": entry.get("quantity"),
            "digitisation_status": entry.get("digitisation_status"),
            "permittivity_used": options["permittivity"],
            "polarisation": options["polarisation"],
            "frequency_ghz": options["frequency_hz"] / 1e9,
            "variants": [],
        }
        for label, recess_mm, piston_mm in (
            ("flush_no_scatter", 0.0, 0.0),
            ("flush_r1_scatter", 0.0, piston * 1000.0),
            ("recessed_5mm_r1_scatter", 5.0, piston * 1000.0),
            ("recessed_10mm_r1_scatter", 10.0, piston * 1000.0),
            # The one fitted variant in this repository, labelled as such. Both
            # values were inverted from the Dillard points and both are inside
            # what construction guidance allows, which is what makes the
            # inversion a falsifiable claim about that wall rather than a knob.
            ("inverted_from_dillard_FITTED", 8.2, 0.90),
        ):
            wall = MasonryWall(
                brick=BRICK_FORMATS["standard_metric"],
                joint=JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=max(recess_mm, 1e-9) / 1000.0),
                bond=BONDS["running"],
                brick_permittivity=complex(options["permittivity"], 0.0),
                mortar_permittivity=complex(options["permittivity"], 0.0),
            )
            points = []
            for angle, measured in entry["data"]:
                flat = abs(fresnel_reflection(wall.brick_permittivity, float(angle), options["polarisation"]))
                retention = specular_retention(
                    wall,
                    frequency_hz=options["frequency_hz"],
                    theta_deg=float(angle),
                    piston_sigma_m=piston_mm / 1000.0,
                )
                predicted = flat * math.sqrt(retention)
                points.append(
                    {
                        "theta_deg": float(angle),
                        "measured_reflection_magnitude": float(measured),
                        "flat_wall_reflection_magnitude": flat,
                        "predicted_reflection_magnitude": predicted,
                        "predicted_specular_retention": retention,
                        "residual_db": 20.0 * math.log10(max(predicted, 1e-9) / max(float(measured), 1e-9)),
                    }
                )
            residuals = np.array([point["residual_db"] for point in points])
            record["variants"].append(
                {
                    "label": label,
                    "recess_mm": recess_mm,
                    "piston_sigma_mm": piston_mm,
                    "median_residual_db": float(np.median(residuals)),
                    "rms_residual_db": float(np.sqrt(np.mean(residuals**2))),
                    "worst_residual_db": float(residuals[np.argmax(np.abs(residuals))]),
                    "points": points,
                }
            )
        payload["comparisons"].append(record)
    path = write("validation.json", payload)
    for record in payload["comparisons"]:
        print(f"{record['dataset']} at {record['frequency_ghz']:g} GHz, {record['polarisation']}")
        for variant in record["variants"]:
            print(
                f"   {variant['label']:26} median {variant['median_residual_db']:+6.2f} dB  "
                f"rms {variant['rms_residual_db']:5.2f} dB  worst {variant['worst_residual_db']:+6.2f} dB"
            )
    print(f"validate: wrote {path}")


def run(stage: str = "all") -> None:
    stages = {
        "census": stage_census,
        "rcwa": stage_rcwa,
        "kirchhoff": stage_kirchhoff,
        "maps": stage_maps,
        "model": stage_model,
        "validate": stage_validate,
    }
    selected = stages if stage == "all" else {stage: stages[stage]}
    for name, function in selected.items():
        print(f"--- {name} ---")
        function()
