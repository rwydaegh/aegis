"""Closed-form checks for the exposure transport driver."""

from __future__ import annotations

import pathlib

import numpy as np

from semantic_twin.illumination import IlluminationModel
from semantic_twin.materials import CLASS_NAMES, load_table
from semantic_twin.propagation.closed_form import PEC_PERMITTIVITY, ground_plane_susceptibility
from semantic_twin.propagation.geometry import PlaneGeometry
from semantic_twin.transport.tracer import SbrTracer, TraceConfig


def validate(
    models: dict[str, IlluminationModel],
    config_dir: pathlib.Path,
    rays: int = 400_000,
) -> dict[str, object]:
    """Run the section 11.1 checks and the free-space identity."""
    report: dict[str, object] = {}
    config = TraceConfig(rays=rays, local_cells=256, exit_bands=18, seed=11)

    class Empty:
        def intersect(self, origins, directions):  # noqa: ANN001, ANN202
            count = origins.shape[0]
            return (
                np.zeros(count, dtype=bool),
                np.full(count, 1.0e30),
                np.zeros((count, 3)),
                np.zeros(count, dtype=np.int64),
            )

    tracer = SbrTracer(Empty(), None, np.array([PEC_PERMITTIVITY]), np.array([0.0]), config)
    free = tracer.trace(np.array([0.0, 0.0, 1.5]), models)
    report["free_space"] = {
        "chi": free.susceptibility,
        "exit_profile_max_abs_error": float(np.max(np.abs(free.exit_profile - 1.0))),
    }

    tracer = SbrTracer(PlaneGeometry(0.0), None, np.array([PEC_PERMITTIVITY]), np.array([0.0]), config)
    pec = tracer.trace(np.array([0.0, 0.0, 1.5]), models, ground_z_m=0.0)
    upper = pec.exit_profile[config.exit_bands // 2 :]
    lower = pec.exit_profile[: config.exit_bands // 2]
    report["pec_ground_plane"] = {
        "target_upper_hemisphere": 2.0,
        "measured_upper_mean": float(upper.mean()),
        "measured_upper_max_abs_error": float(np.max(np.abs(upper - 2.0))),
        "measured_lower_max": float(lower.max()),
        "chi": pec.susceptibility,
    }

    binding = load_table(config_dir, 15.0e9)
    concrete = binding.permittivity[CLASS_NAMES.index("roof")]
    tracer = SbrTracer(PlaneGeometry(0.0), None, np.array([concrete]), np.array([0.0]), config)
    dielectric = tracer.trace(np.array([0.0, 0.0, 1.5]), models, ground_z_m=0.0)
    centres = 0.5 * (dielectric.exit_sin_edges[:-1] + dielectric.exit_sin_edges[1:])
    elevation = np.degrees(np.arcsin(centres))
    target = ground_plane_susceptibility(elevation, concrete)
    above = elevation > 0.0
    report["dielectric_ground_plane"] = {
        "permittivity": [float(concrete.real), float(concrete.imag)],
        "elevation_deg": [float(x) for x in elevation[above]],
        "closed_form": [float(x) for x in target[above]],
        "measured": [float(x) for x in dielectric.exit_profile[above]],
        "max_abs_error": float(np.max(np.abs(dielectric.exit_profile[above] - target[above]))),
        "max_rel_error": float(np.max(np.abs(dielectric.exit_profile[above] / target[above] - 1.0))),
    }
    return report
