"""Body geometry: mesh loading, occlusion, projected area, directivity."""

from aegis.geometry.averaging import apply_spatial_averaging
from aegis.geometry.cauchy import cauchy_projected_area, cauchy_relative_error, mean_projected_area
from aegis.geometry.directivity import (
    compute_directivity,
    eval_sh,
    fit_sh,
    sh_reconstruction_error,
    spherical_angles_from_k_hat,
)
from aegis.geometry.mesh import BodyMesh, load_stl_binary, triangle_areas
from aegis.geometry.occlusion import compute_ambient_occlusion
from aegis.geometry.projected_area import compute_projected_area, fibonacci_sphere

__all__ = [
    "BodyMesh",
    "apply_spatial_averaging",
    "cauchy_projected_area",
    "cauchy_relative_error",
    "compute_ambient_occlusion",
    "compute_directivity",
    "compute_projected_area",
    "eval_sh",
    "fibonacci_sphere",
    "fit_sh",
    "load_stl_binary",
    "mean_projected_area",
    "sh_reconstruction_error",
    "spherical_angles_from_k_hat",
    "triangle_areas",
]
