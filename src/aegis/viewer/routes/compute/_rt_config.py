"""Ray-tracer config parsing for compute routes."""

from __future__ import annotations


def _safe_int(val, default: int) -> int:
    """Convert to int, returning *default* on failure."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _parse_rt_config(params: dict, cache: dict) -> dict:
    """Extract rt_config from request params, with backward-compatible fallbacks."""
    rt = params.get("rt_config", {})
    if not isinstance(rt, dict):
        rt = {}

    rt_defaults = cache["config"]["raytracer"]["defaults"]
    d_max = rt_defaults["max_depth"]
    d_max_min = rt_defaults["max_depth_min"]
    d_max_max = rt_defaults["max_depth_max"]
    r_def = rt_defaults["rays_per_source"]
    r_min = rt_defaults["rays_per_source_min"]
    r_max = rt_defaults["rays_per_source_max"]
    mp_def = rt_defaults["max_paths_per_source"]
    c_def = rt_defaults["chunk_size"]
    c_max = rt_defaults["chunk_size_max"]

    max_depth = _safe_int(rt.get("max_depth", params.get("max_order", d_max)), d_max)
    max_depth = max(d_max_min, min(max_depth, d_max_max))

    rays_per_source = _safe_int(rt.get("rays_per_source", r_def), r_def)
    rays_per_source = max(r_min, min(rays_per_source, r_max))

    max_paths_per_source = _safe_int(rt.get("max_paths_per_source", mp_def), mp_def)
    max_paths_per_source = max(r_min, min(max_paths_per_source, r_max))

    chunk_size = rt.get("chunk_size")
    if chunk_size is not None:
        chunk_size = max(1, min(_safe_int(chunk_size, c_def), c_max))

    return {
        "max_depth": max_depth,
        "method": rt.get("method", "exhaustive"),
        "rays_per_source": rays_per_source,
        "max_paths_per_source": max_paths_per_source,
        "chunk_size": chunk_size,
        "los": rt.get("los", True),
        "specular_reflection": rt.get("specular_reflection", True),
        "diffuse_reflection": rt.get("diffuse_reflection", False),
        "refraction": rt.get("refraction", True),
        "diffraction": rt.get("diffraction", False),
        "edge_diffraction": rt.get("edge_diffraction", False),
        "diffraction_lit_region": rt.get("diffraction_lit_region", True),
        "reflection_loss_per_order": rt.get(
            "reflection_loss_per_order",
            cache["config"]["raytracer"]["reflection_loss_per_order"],
        ),
        "synthetic_array": rt.get("synthetic_array", True),
        "seed": rt.get("seed", 42),
    }
