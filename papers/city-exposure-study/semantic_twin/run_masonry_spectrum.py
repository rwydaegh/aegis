"""Converged rigorous bistatic spectra of brickwork, against the phase screen.

Two stages, both resumable, both writing after every case so an interrupted run
keeps its finished work.

``converge``  Push the Fourier truncation up at fixed geometry and record what
              the answer does, with the retained mode count, the dense matrix
              size, the wall clock and the peak resident memory attached to every
              level. A single large order count is not evidence of anything. The
              curve is.
``spectrum``  At the truncation the curve justifies, record the efficiency of
              every propagating order from both solvers, which is the object a
              bistatic figure is drawn from.

Memory scales as the square of the retained order count and time as its cube, so
elliptic truncation is the default: it drops the box corners, which are the most
deeply evanescent orders in the set, for 30 percent fewer modes and less than
half the time at the same reach.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import resource
import time

import numpy as np

from semantic_twin.materials.masonry import fresnel_reflection, kirchhoff_orders
from semantic_twin.materials.masonry import (
    BONDS,
    BRICK_FORMATS,
    JointGeometry,
    MasonryWall,
    permittivity_from_evaluation,
)
from semantic_twin.materials.roughness import wavelength_m
from semantic_twin.materials.masonry import harmonic_indices
from semantic_twin.materials.masonry import solve as rcwa_solve

ROOT = pathlib.Path(__file__).resolve().parent
OUTPUT = ROOT / "outputs" / "masonry_grating"

BRICK_A, BRICK_C, BRICK_D = 3.91, 0.0238, 0.16

WORKING_SET_MULTIPLE = 32.0
"""Peak resident memory as a multiple of one dense scattering matrix.

Measured, not guessed: a 2397 mode solve holds 0.34 GiB in one dense matrix and
peaked at 10.7 GiB. The eigenvalue decomposition, the LAPACK workspace, the
layer inverses and the Redheffer products are all the same size, so the whole
solve is a fixed number of copies. Memory is therefore quadratic in the retained
order count and time is cubic, which is why elliptic truncation is worth having
and why a run has to be given a budget rather than a mode count.
"""


def brick_permittivity(frequency_hz: float) -> complex:
    ghz = frequency_hz / 1e9
    return permittivity_from_evaluation(BRICK_A, BRICK_C * ghz**BRICK_D, frequency_hz)


def build_wall(*, recess_m: float, frequency_hz: float, bond_name: str = "stack") -> MasonryWall:
    eps = brick_permittivity(frequency_hz)
    return MasonryWall(
        brick=BRICK_FORMATS["standard_metric"],
        joint=JointGeometry(bed_m=0.010, perp_m=0.010, recess_m=max(recess_m, 1e-9)),
        bond=BONDS[bond_name],
        brick_permittivity=eps,
        mortar_permittivity=eps,
        name=f"uk_{bond_name}",
    )


def propagating_reach(wall: MasonryWall, frequency_hz: float, theta_deg: float) -> tuple[int, int]:
    """Smallest truncation that contains every propagating order."""
    lam = float(wavelength_m(frequency_hz))
    span = 1.0 + abs(math.sin(math.radians(theta_deg)))
    return int(math.ceil(span * wall.cell_x_m / lam)), int(math.ceil(span * wall.cell_y_m / lam))


def peak_memory_gib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20


def write(name: str, payload: dict) -> pathlib.Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / name
    path.write_text(json.dumps(payload, indent=2, default=float))
    return path


HERO_CASES = (
    dict(label="fr2_28ghz_30deg", frequency_hz=28e9, theta_deg=30.0, recess_m=0.005),
    dict(label="fr2_28ghz_60deg", frequency_hz=28e9, theta_deg=60.0, recess_m=0.005),
    dict(label="fr3_10ghz_30deg", frequency_hz=10e9, theta_deg=30.0, recess_m=0.005),
    dict(label="fr3_10ghz_30deg_deep", frequency_hz=10e9, theta_deg=30.0, recess_m=0.010),
)

CONVERGENCE_MULTIPLIERS = (0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0)


def stage_converge(memory_budget_gib: float, time_budget_s: float) -> None:
    name = "rcwa_convergence.json"
    path = OUTPUT / name
    payload: dict = (
        json.loads(path.read_text())
        if path.exists()
        else {
            "_meta": {
                "purpose": "Fourier truncation convergence of the rigorous solve, with cost attached to every level.",
                "truncation": "elliptic",
                "reach_definition": "multiplier times the smallest truncation containing every propagating order",
                "computed_here": True,
            },
            "cases": [],
        }
    )
    done = {case["label"] for case in payload["cases"]}
    for hero in HERO_CASES:
        if hero["label"] in done:
            print(f"converge: {hero['label']} already recorded, skipping")
            continue
        wall = build_wall(recess_m=hero["recess_m"], frequency_hz=hero["frequency_hz"])
        base_m, base_n = propagating_reach(wall, hero["frequency_hz"], hero["theta_deg"])
        record = {
            "label": hero["label"],
            "frequency_ghz": hero["frequency_hz"] / 1e9,
            "theta_deg": hero["theta_deg"],
            "recess_mm": hero["recess_m"] * 1000.0,
            "bond": wall.bond.name,
            "cell_mm": [wall.cell_x_m * 1000.0, wall.cell_y_m * 1000.0],
            "propagating_reach": [base_m, base_n],
            "levels": [],
        }
        flat = abs(fresnel_reflection(wall.brick_permittivity, hero["theta_deg"], "te")) ** 2
        record["flat_wall_reflectance"] = flat
        for multiplier in CONVERGENCE_MULTIPLIERS:
            harmonics = (max(2, int(round(multiplier * base_m))), max(2, int(round(multiplier * base_n))))
            modes = harmonic_indices(*harmonics)[0].size
            projected = (2 * modes) ** 2 * 16.0 / 2**30
            if projected * WORKING_SET_MULTIPLE > memory_budget_gib:
                record["stopped_because"] = (
                    f"projected working set {projected * WORKING_SET_MULTIPLE:.1f} GiB at reach {harmonics} "
                    f"exceeds the {memory_budget_gib:.0f} GiB budget"
                )
                break
            samples_x = max(512, 4 * (2 * harmonics[0] + 1))
            samples_y = max(384, 4 * (2 * harmonics[1] + 1))
            started = time.time()
            solution = rcwa_solve(
                wall.rcwa_layers(samples_x, samples_y),
                period_x_m=wall.cell_x_m,
                period_y_m=wall.cell_y_m,
                frequency_hz=hero["frequency_hz"],
                theta_deg=hero["theta_deg"],
                polarisation="te",
                harmonics=harmonics,
            )
            elapsed = time.time() - started
            record["levels"].append(
                {
                    "multiplier": multiplier,
                    "harmonics": list(harmonics),
                    "modes": int(modes),
                    "matrix_dimension": int(2 * modes),
                    "dense_matrix_gibibytes": projected,
                    "seconds": elapsed,
                    "peak_rss_gibibytes": peak_memory_gib(),
                    "propagating_orders": int(np.count_nonzero(solution.propagating)),
                    "specular_efficiency": solution.specular_efficiency,
                    "diffuse_efficiency": solution.diffuse_efficiency,
                    "total_reflectance": solution.total_reflectance,
                }
            )
            print(
                f"converge {hero['label']} x{multiplier}: {modes} modes, "
                f"spec {solution.specular_efficiency:.5f} diff {solution.diffuse_efficiency:.5f} "
                f"[{elapsed:.0f}s, peak {peak_memory_gib():.1f} GiB]",
                flush=True,
            )
            payload["cases"] = [entry for entry in payload["cases"] if entry["label"] != hero["label"]] + [record]
            write(name, payload)
            if elapsed > time_budget_s:
                record["stopped_because"] = f"level took {elapsed:.0f} s, above the {time_budget_s:.0f} s budget"
                break
        levels = record["levels"]
        if len(levels) >= 2:
            record["specular_change_last_step"] = abs(
                levels[-1]["specular_efficiency"] / max(levels[-2]["specular_efficiency"], 1e-30) - 1.0
            )
            record["diffuse_change_last_step"] = abs(
                levels[-1]["diffuse_efficiency"] / max(levels[-2]["diffuse_efficiency"], 1e-30) - 1.0
            )
        payload["cases"] = [entry for entry in payload["cases"] if entry["label"] != hero["label"]] + [record]
        write(name, payload)
    print(f"converge: wrote {OUTPUT / name}")


def stage_spectrum(multiplier: float) -> None:
    name = "rcwa_spectrum.json"
    path = OUTPUT / name
    payload: dict = (
        json.loads(path.read_text())
        if path.exists()
        else {
            "_meta": {
                "purpose": "Per-order bistatic efficiency of brickwork, rigorous against the Kirchhoff phase screen.",
                "truncation": "elliptic",
                "computed_here": True,
            },
            "cases": [],
        }
    )
    done = {case["label"] for case in payload["cases"]}
    for hero in HERO_CASES:
        if hero["label"] in done:
            print(f"spectrum: {hero['label']} already recorded, skipping")
            continue
        wall = build_wall(recess_m=hero["recess_m"], frequency_hz=hero["frequency_hz"])
        base_m, base_n = propagating_reach(wall, hero["frequency_hz"], hero["theta_deg"])
        harmonics = (max(2, int(round(multiplier * base_m))), max(2, int(round(multiplier * base_n))))
        samples_x = max(512, 4 * (2 * harmonics[0] + 1))
        samples_y = max(384, 4 * (2 * harmonics[1] + 1))
        started = time.time()
        rigorous = rcwa_solve(
            wall.rcwa_layers(samples_x, samples_y),
            period_x_m=wall.cell_x_m,
            period_y_m=wall.cell_y_m,
            frequency_hz=hero["frequency_hz"],
            theta_deg=hero["theta_deg"],
            polarisation="te",
            harmonics=harmonics,
        )
        approximate = kirchhoff_orders(
            wall,
            frequency_hz=hero["frequency_hz"],
            theta_deg=hero["theta_deg"],
            polarisation="te",
            harmonics=harmonics,
        )
        k0 = 2.0 * math.pi / float(wavelength_m(hero["frequency_hz"]))
        rigorous_index = {(int(m), int(n)): i for i, (m, n) in enumerate(zip(rigorous.m, rigorous.n, strict=True))}
        orders = []
        for i, (m, n) in enumerate(zip(approximate.m, approximate.n, strict=True)):
            if not approximate.propagating[i]:
                continue
            key = (int(m), int(n))
            if key not in rigorous_index:
                continue
            j = rigorous_index[key]
            sine = float(np.hypot(approximate.kx[i], approximate.ky[i]) / k0)
            orders.append(
                {
                    "m": int(m),
                    "n": int(n),
                    "scatter_theta_deg": math.degrees(math.asin(min(sine, 1.0))),
                    "scatter_phi_deg": math.degrees(math.atan2(float(approximate.ky[i]), float(approximate.kx[i]))),
                    "signed_theta_deg": math.degrees(math.asin(min(sine, 1.0)))
                    * (1.0 if approximate.kx[i] >= 0 else -1.0),
                    "rcwa_efficiency": float(rigorous.efficiency[j]),
                    "kirchhoff_efficiency": float(approximate.efficiency[i]),
                }
            )
        flat = abs(fresnel_reflection(wall.brick_permittivity, hero["theta_deg"], "te")) ** 2
        payload["cases"].append(
            {
                "label": hero["label"],
                "frequency_ghz": hero["frequency_hz"] / 1e9,
                "theta_deg": hero["theta_deg"],
                "recess_mm": hero["recess_m"] * 1000.0,
                "joint_width_mm": wall.joint.bed_m * 1000.0,
                "groove_aspect": hero["recess_m"] / wall.joint.bed_m,
                "bond": wall.bond.name,
                "cell_mm": [wall.cell_x_m * 1000.0, wall.cell_y_m * 1000.0],
                "harmonics": list(harmonics),
                "modes": int(rigorous.m.size),
                "convergence_multiplier": multiplier,
                "flat_wall_reflectance": flat,
                "rcwa_specular": rigorous.specular_efficiency,
                "rcwa_diffuse": rigorous.diffuse_efficiency,
                "kirchhoff_specular": approximate.specular_efficiency,
                "kirchhoff_diffuse": approximate.coherent_diffuse,
                "seconds": time.time() - started,
                "peak_rss_gibibytes": peak_memory_gib(),
                "orders": orders,
            }
        )
        write(name, payload)
        print(
            f"spectrum {hero['label']}: {len(orders)} propagating orders, "
            f"spec {rigorous.specular_efficiency:.5f} vs {approximate.specular_efficiency:.5f}, "
            f"diffuse {rigorous.diffuse_efficiency:.5f} vs {approximate.coherent_diffuse:.5f} "
            f"[{time.time() - started:.0f}s, peak {peak_memory_gib():.1f} GiB]",
            flush=True,
        )
    print(f"spectrum: wrote {OUTPUT / name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("converge", "spectrum", "all"), default="all")
    parser.add_argument("--memory-budget-gib", type=float, default=18.0)
    parser.add_argument("--time-budget-s", type=float, default=2400.0)
    parser.add_argument("--multiplier", type=float, default=1.5)
    arguments = parser.parse_args()
    if arguments.stage in ("converge", "all"):
        stage_converge(arguments.memory_budget_gib, arguments.time_budget_s)
    if arguments.stage in ("spectrum", "all"):
        stage_spectrum(arguments.multiplier)


if __name__ == "__main__":
    main()
