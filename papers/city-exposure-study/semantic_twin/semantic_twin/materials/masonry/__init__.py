"""Brickwork as a specified periodic structure.

A masonry facade is not a random height field. Its unit format is a
manufacturing standard, its joint width and profile are workmanship
specifications, its bond is a named pattern and its unit-to-unit scatter is a
declared tolerance class. Every input a scattering calculation needs is in a
construction document, which is what makes a rigorous treatment possible here
and hopeless for most surfaces.

Reading order. :mod:`~.wall` turns those documents into a lattice and a
permittivity map on the unit cell. :mod:`~.floquet` gives the discrete set of
directions any periodic surface can scatter into, fixed by the lattice and the
wavelength alone. :mod:`~.rcwa` solves the cell rigorously. :mod:`~.kirchhoff`
solves it cheaply by physical optics and, unlike the rigorous method, can carry
the ensemble average over unit-to-unit disorder in closed form.

Status. None of this reaches a published number, and only one function is
offered to the live material layer:
:func:`~.kirchhoff.equivalent_rms_height_m`, through
:func:`semantic_twin.materials.roughness.masonry_equivalent_rms_height`, and
not as a default. That route is closed form algebra over the wall geometry and
touches neither :mod:`~.rcwa` nor the Kirchhoff order machinery, which carry
findings 5 and 6 of ``docs/BUGS.md`` between them. The RCWA mode-selection
failure in finding 10 is fixed, while its Fourier factorisation failure remains.
"""

from __future__ import annotations

from .floquet import (
    DiffractionOrders,
    Lattice,
    centred_rectangular_lattice,
    diffraction_orders,
    grating_order_angles_deg,
    incident_wavevector,
    rectangular_lattice,
)
from .kirchhoff import (
    BistaticMap,
    DisorderModel,
    KirchhoffSolution,
    bistatic_map,
    equivalent_rms_height_m,
    fresnel_reflection,
    gaussian_equivalence_limit_m,
    hemisphere_grid,
    incoherent_differential,
    incoherent_power_fraction,
    kirchhoff_orders,
    order_angular_width_deg,
    phase_screen_incidence_limit_deg,
    phase_screen_recess_limit_m,
    specular_retention,
)
from .rcwa import Layer, RcwaSolution, convergence_sweep, convolution_matrix, harmonic_indices, solve
from .wall import (
    BELGIAN_JOINT,
    BONDS,
    BRICK_FORMATS,
    BUCKET_HANDLE_JOINT,
    DEEP_RECESSED_JOINT,
    ENGLISH_BOND,
    FLEMISH_BOND,
    JOINT_PROFILES,
    PROUD_JOINT,
    RANGE_CONSTANT_N10,
    RECESSED_JOINT,
    RUNNING_BOND,
    STACK_BOND,
    STANDARD_JOINT,
    TOLERANCE_CLASSES,
    VACUUM_PERMITTIVITY,
    WALL_FLATNESS_TOLERANCE_MM,
    BondPattern,
    BrickFormat,
    JointGeometry,
    MasonryWall,
    ToleranceClass,
    permittivity_from_evaluation,
)

__all__ = [
    "BELGIAN_JOINT",
    "BONDS",
    "BRICK_FORMATS",
    "BUCKET_HANDLE_JOINT",
    "DEEP_RECESSED_JOINT",
    "ENGLISH_BOND",
    "FLEMISH_BOND",
    "JOINT_PROFILES",
    "PROUD_JOINT",
    "RANGE_CONSTANT_N10",
    "RECESSED_JOINT",
    "RUNNING_BOND",
    "STACK_BOND",
    "STANDARD_JOINT",
    "TOLERANCE_CLASSES",
    "VACUUM_PERMITTIVITY",
    "WALL_FLATNESS_TOLERANCE_MM",
    "BistaticMap",
    "BondPattern",
    "BrickFormat",
    "DiffractionOrders",
    "DisorderModel",
    "JointGeometry",
    "KirchhoffSolution",
    "Lattice",
    "Layer",
    "MasonryWall",
    "RcwaSolution",
    "ToleranceClass",
    "bistatic_map",
    "centred_rectangular_lattice",
    "convergence_sweep",
    "convolution_matrix",
    "diffraction_orders",
    "equivalent_rms_height_m",
    "fresnel_reflection",
    "gaussian_equivalence_limit_m",
    "grating_order_angles_deg",
    "harmonic_indices",
    "hemisphere_grid",
    "incident_wavevector",
    "incoherent_differential",
    "incoherent_power_fraction",
    "kirchhoff_orders",
    "order_angular_width_deg",
    "permittivity_from_evaluation",
    "phase_screen_incidence_limit_deg",
    "phase_screen_recess_limit_m",
    "rectangular_lattice",
    "solve",
    "specular_retention",
]
