"""Body-mesh preload helpers used by the app factory."""

from __future__ import annotations

import threading
from pathlib import Path

from aegis.viewer.scene_data import body_to_binary, load_body


def _load_phantom_overrides(data_dir: str) -> dict:
    """Read phantoms.yaml for per-phantom device_offset overrides."""
    import yaml

    phantoms_path = Path(data_dir) / "phantoms.yaml"
    phantom_overrides: dict = {}
    if not phantoms_path.exists():
        return phantom_overrides
    with open(phantoms_path) as f:
        phantom_data = yaml.safe_load(f) or {}
    for name, info in phantom_data.items():
        if "device_offset" in info:
            phantom_overrides[name] = info["device_offset"]
    return phantom_overrides


def _resolve_device_offset(
    name: str,
    body,
    overrides: dict,
    forward_distance: float,
) -> list[float]:
    """Manual override if present, otherwise auto-detect from vertices."""
    from aegis.geometry.device_offset import estimate_device_offset

    if name in overrides:
        return [float(v) for v in overrides[name]]
    return estimate_device_offset(body.vertices, forward_distance=forward_distance)


def _cache_body_entry(cache: dict, name: str, body, offset: list[float]) -> None:
    binary, meta = body_to_binary(body)
    cache["bodies"][name] = {"body": body, "binary": binary, "meta": meta}
    cache["body_device_offsets"][name] = offset


def _load_stl_bodies(
    data_dir: str,
    cache: dict,
    overrides: dict,
    forward_distance: float,
) -> list[str]:
    """Load every .stl in data_dir into the cache. Return the list of names."""
    available = [p.stem for p in Path(data_dir).glob("*.stl")]
    for name in available:
        try:
            body = load_body(name, data_dir)
            offset = _resolve_device_offset(name, body, overrides, forward_distance)
            _cache_body_entry(cache, name, body, offset)
            print(f"  Body: {body.name}, {body.n_triangles:,} triangles, device_offset={offset}")
        except FileNotFoundError as e:
            print(f"  Warning: {e}")
    return available


def _resolve_phantom_dir(data_dir: str, cfg: dict) -> Path:
    phantom_dir_cfg = cfg.get("body", {}).get("phantom_dir", "")
    if phantom_dir_cfg and Path(phantom_dir_cfg).is_absolute():
        return Path(phantom_dir_cfg)
    return Path(data_dir) / "phantoms"


def _load_glb_phantoms(
    data_dir: str,
    cfg: dict,
    cache: dict,
    overrides: dict,
    forward_distance: float,
) -> None:
    """Load GLB animated phantoms that aren't shadowed by an STL."""
    phantom_dir = _resolve_phantom_dir(data_dir, cfg)
    if not phantom_dir.is_dir():
        return
    for glb_path in sorted(phantom_dir.glob("*.glb")):
        glb_name = glb_path.stem
        if glb_name in cache["bodies"]:
            continue
        try:
            from aegis.geometry.skeleton import GltfSkeleton

            skel = GltfSkeleton.load(glb_path)
            body = skel.pose_to_body(name=glb_name)
            offset = _resolve_device_offset(glb_name, body, overrides, forward_distance)
            _cache_body_entry(cache, glb_name, body, offset)
            print(f"  Body (GLB): {glb_name}, {body.n_triangles:,} triangles, device_offset={offset}")
        except Exception as e:
            print(f"  Warning: failed to load GLB phantom {glb_path.name}: {e}")


def _set_default_body_aliases(
    data_dir: str,
    body_name: str,
    cache: dict,
    overrides: dict,
    forward_distance: float,
) -> None:
    """Populate ``body``, ``body_binary``, ``body_meta`` for the default phantom."""
    default_entry = cache["bodies"].get(body_name)
    if default_entry is not None:
        cache["body"] = default_entry["body"]
        cache["body_binary"] = default_entry["binary"]
        cache["body_meta"] = default_entry["meta"]
        return

    try:
        body = load_body(body_name, data_dir)
        offset = _resolve_device_offset(body_name, body, overrides, forward_distance)
        _cache_body_entry(cache, body_name, body, offset)
        cache["body"] = body
        cache["body_binary"] = cache["bodies"][body_name]["binary"]
        cache["body_meta"] = cache["bodies"][body_name]["meta"]
        print(f"  Body (fallback): {body.name}, {body.n_triangles:,} triangles, device_offset={offset}")
    except FileNotFoundError as e:
        print(f"  Warning: {e}")
        cache["body"] = None
        cache["body_binary"] = None
        cache["body_meta"] = None


def preload_bodies(
    data_dir: str,
    body_name: str,
    cache: dict,
    cache_lock: threading.RLock,
) -> None:
    """Load all available body meshes from data_dir into cache."""
    overrides = _load_phantom_overrides(data_dir)
    cfg = cache.get("config", {})
    forward_distance = cfg.get("body", {}).get("smartphone", {}).get("forward_distance", 0.30)

    with cache_lock:
        cache["bodies"] = {}
        cache["body_device_offsets"] = {}
        cache["default_body"] = body_name

        stl_names = _load_stl_bodies(data_dir, cache, overrides, forward_distance)
        _load_glb_phantoms(data_dir, cfg, cache, overrides, forward_distance)

        cache["gltf_bodies"] = sorted(name for name in cache["bodies"] if name not in stl_names)

        _set_default_body_aliases(data_dir, body_name, cache, overrides, forward_distance)
