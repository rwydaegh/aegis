"""Compatibility imports for the bystander geometry and study modules.

New code should import geometry from :mod:`bystander_geometry`, execution from
:mod:`semantic_twin.exposure.bystander_study`, and reporting from
:mod:`semantic_twin.report.bystanders`.
"""

from __future__ import annotations

from .bystander_geometry import *  # noqa: F403
from .bystander_geometry import (
    CrowdGeometryConfig,
    TransmittanceConfig,
    crowd_geometry as _crowd_geometry,
    crowd_transmittance as _crowd_transmittance,
)
from ..exposure.bystander_study import (  # noqa: F401
    ADULT_STATURE_MEAN_M,
    ADULT_STATURE_SD_M,
    ARMS,
    STATURE_MODES,
    BystanderStudyConfig,
    NoiseFloorConfig,
    StudyRunConfig,
    ground_datum,
    noise_floor as _noise_floor,
    run_bystander_study,
    run_study as _run_study,
    site_mesh,
    stature_library,
)
from ..report.bystanders import plot_mechanism, plot_study, summarise_study  # noqa: F401
from ..transport.tracer import DEFAULT_MAX_BOUNCES  # noqa: F401


def crowd_geometry(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    """Call the geometry API with its historical argument list."""
    names = ("site", "crowd", "library", "site_face_class", "body_class_index")
    if len(args) > len(names):
        raise TypeError(f"crowd_geometry() takes {len(names)} positional arguments but {len(args)} were given")
    values = dict(zip(names, args, strict=False))
    for name in names[len(args) :]:
        if name not in kwargs:
            raise TypeError(f"crowd_geometry() missing required argument: {name!r}")
        values[name] = kwargs.pop(name)
    duplicate = next((name for name in names[: len(args)] if name in kwargs), None)
    if duplicate is not None:
        raise TypeError(f"crowd_geometry() got multiple values for argument {duplicate!r}")
    return _crowd_geometry(CrowdGeometryConfig(**values, **kwargs))


def crowd_transmittance(directions, **kwargs):  # noqa: ANN001, ANN003, ANN201
    """Call the analytic API with its historical keyword inputs."""
    return _crowd_transmittance(directions, TransmittanceConfig(**kwargs))


def run_study(**kwargs):  # noqa: ANN003, ANN201
    """Call the study runner with its historical keyword inputs."""
    return _run_study(StudyRunConfig(**kwargs))


def noise_floor(**kwargs):  # noqa: ANN003, ANN201
    """Call the variance runner with its historical keyword inputs."""
    return _noise_floor(NoiseFloorConfig(**kwargs))
