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

    max_depth = _safe_int(rt.get("max_depth", params.get("max_order", 3)), 3)
    max_depth = max(0, min(max_depth, 10))

    rays_per_source = _safe_int(rt.get("rays_per_source", 1_000_000), 1_000_000)
    rays_per_source = max(100, min(rays_per_source, 10_000_000))

    max_paths_per_source = _safe_int(rt.get("max_paths_per_source", 1_000_000), 1_000_000)
    max_paths_per_source = max(100, min(max_paths_per_source, 10_000_000))

    chunk_size = rt.get("chunk_size")
    if chunk_size is not None:
        chunk_size = max(1, min(_safe_int(chunk_size, 100_000), 1_000_000))

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
