"""CLI batch runner for reproducible dosimetry simulations.

Usage:
    py -3.12 -m aegis.run --config config.yaml
    py -3.12 -m aegis.run --body duke --level 3 --frequency 28e9
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from aegis.config import SimulationConfig
from aegis.engine import DosimetryEngine
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import TissueModel


def _find_data_dir() -> Path:
    """Find the data/ directory, respecting AEGIS_DATA_DIR env var."""
    import os

    env = os.environ.get("AEGIS_DATA_DIR")
    if env:
        return Path(env)
    return Path(__file__).parent.parent.parent / "data"


def _load_body(cfg: SimulationConfig):
    """Load body mesh from config."""
    from aegis.geometry.mesh import BodyMesh

    data_dir = _find_data_dir()
    stl_path = data_dir / f"{cfg.body.name}.stl"
    if not stl_path.exists():
        raise FileNotFoundError(f"Body mesh not found: {stl_path}")
    return BodyMesh.load(stl_path)


def _load_tissue(cfg: SimulationConfig) -> TissueModel:
    """Load tissue model from config."""
    return TissueModel.from_database(cfg.tissue.name, cfg.tissue.frequency_hz)


def _generate_paths(cfg: SimulationConfig) -> PropagationPaths:
    """Generate propagation paths based on configured backend."""
    tx_pos = np.array(cfg.antenna.positions, dtype=np.float64)
    power_w = 10 ** ((cfg.antenna.power_dbm - 30) / 10)

    if cfg.raytracer.backend == "synthetic":
        return _synthetic_paths(tx_pos, power_w)
    elif cfg.raytracer.backend == "differt":
        from aegis.integration.differt import paths_from_differt_scene

        if cfg.raytracer.scene_path is None:
            raise ValueError("scene_path required for differt backend")
        return paths_from_differt_scene(
            scene_path=cfg.raytracer.scene_path,
            tx_positions=tx_pos,
            rx_position=np.zeros(3),
            freq_hz=cfg.tissue.frequency_hz,
            max_bounces=cfg.raytracer.max_bounces,
            tx_power_dbm=cfg.antenna.power_dbm,
            initial_polarisation=cfg.antenna.polarisation,
        )
    elif cfg.raytracer.backend == "sionna":
        from aegis.integration.sionna import paths_from_sionna_scene

        if cfg.raytracer.scene_path is None:
            raise ValueError("scene_path required for sionna backend")
        import sionna.rt

        scene = sionna.rt.load_scene(cfg.raytracer.scene_path)
        return paths_from_sionna_scene(
            scene=scene,
            tx_positions=tx_pos,
            rx_position=np.zeros(3),
            freq_hz=cfg.tissue.frequency_hz,
            max_bounces=cfg.raytracer.max_bounces,
            tx_power_dbm=cfg.antenna.power_dbm,
            tx_pattern=cfg.antenna.pattern,
        )
    else:
        raise ValueError(f"Unknown backend: {cfg.raytracer.backend}")


def _synthetic_paths(tx_pos: np.ndarray, power_w: float) -> PropagationPaths:
    """Generate synthetic paths for testing (no ray tracer needed)."""
    n_elements = tx_pos.shape[0]
    k_hats = []
    powers = []
    for i in range(n_elements):
        direction = -tx_pos[i]
        dist = np.linalg.norm(direction)
        if dist < 1e-10:
            continue
        k_hat = direction / dist
        s_inc = power_w / (4 * np.pi * dist**2)
        k_hats.append(k_hat)
        powers.append(s_inc)

    if not k_hats:
        return PropagationPaths.from_powers(k_hat=np.zeros((0, 3)), power=np.zeros(0))
    return PropagationPaths.from_powers(
        k_hat=np.array(k_hats),
        power=np.array(powers),
    )


def _save_results(cfg: SimulationConfig, result, elapsed: float) -> Path:
    """Save config, result arrays, and summary JSON to output directory."""
    from aegis.compliance import ICNIRP_2020

    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_dir = Path(cfg.output_dir) / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    cfg.to_yaml(run_dir / "config.yaml")

    np.savez(
        run_dir / "result.npz",
        sab=result.sab,
        p_abs=np.array(result.p_abs),
    )

    peak_sab = float(np.max(result.sab)) if len(result.sab) > 0 else 0.0
    summary = {
        "peak_sab": peak_sab,
        "p_abs": float(result.p_abs),
        "compliant": peak_sab < ICNIRP_2020.sab_peak,
        "compliant_note": "conservative (no spatial averaging)",
        "level": cfg.dosimetry.level,
        "n_triangles": len(result.sab),
        "elapsed_s": round(elapsed, 3),
    }
    with (run_dir / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    return run_dir


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aegis-run", description="AEGIS batch dosimetry runner")
    p.add_argument("--config", type=str, help="Path to YAML config file")
    p.add_argument("--body", type=str, help="Body phantom name (e.g. thelonious, duke)")
    p.add_argument("--frequency", type=float, help="Frequency in Hz (e.g. 28e9)")
    p.add_argument("--level", type=int, help="Fidelity level 0-8")
    p.add_argument("--power-dbm", type=float, help="TX power in dBm")
    p.add_argument("--antenna-pos", type=str, help="TX position as 'x,y,z'")
    p.add_argument("--backend", type=str, help="Ray tracer backend: differt, sionna, synthetic")
    p.add_argument("--max-bounces", type=int, help="Max ray bounces")
    p.add_argument("--scene-path", type=str, help="Scene file path")
    p.add_argument("--output-dir", type=str, help="Output directory")
    return p


def _apply_overrides(cfg_dict: dict, args: argparse.Namespace) -> dict:
    """Apply CLI overrides to config dict."""
    if args.body is not None:
        cfg_dict.setdefault("body", {})["name"] = args.body
    if args.frequency is not None:
        cfg_dict.setdefault("tissue", {})["frequency_hz"] = args.frequency
    if args.level is not None:
        cfg_dict.setdefault("dosimetry", {})["level"] = args.level
    if args.power_dbm is not None:
        cfg_dict.setdefault("antenna", {})["power_dbm"] = args.power_dbm
    if args.antenna_pos is not None:
        pos = [float(x) for x in args.antenna_pos.split(",")]
        cfg_dict.setdefault("antenna", {})["positions"] = [pos]
    if args.backend is not None:
        cfg_dict.setdefault("raytracer", {})["backend"] = args.backend
    if args.max_bounces is not None:
        cfg_dict.setdefault("raytracer", {})["max_bounces"] = args.max_bounces
    if args.scene_path is not None:
        cfg_dict.setdefault("raytracer", {})["scene_path"] = args.scene_path
    if args.output_dir is not None:
        cfg_dict["output_dir"] = args.output_dir
    return cfg_dict


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Load base config from YAML or empty dict
    if args.config:
        import yaml

        with open(args.config) as f:
            cfg_dict = yaml.safe_load(f) or {}
    else:
        cfg_dict = {}

    cfg_dict = _apply_overrides(cfg_dict, args)

    cfg = SimulationConfig.from_dict(cfg_dict) if cfg_dict else SimulationConfig()

    print(f"AEGIS batch run: level={cfg.dosimetry.level}, backend={cfg.raytracer.backend}")

    body = _load_body(cfg)
    tissue = _load_tissue(cfg)
    paths = _generate_paths(cfg)
    engine = DosimetryEngine(tissue)

    t0 = time.monotonic()
    result = engine.compute(body, paths, level=cfg.dosimetry.level)
    elapsed = time.monotonic() - t0

    run_dir = _save_results(cfg, result, elapsed)
    peak = float(np.max(result.sab)) if len(result.sab) > 0 else 0.0
    print(f"Done in {elapsed:.2f}s. Peak Sab={peak:.4f} W/m^2. Results: {run_dir}")


if __name__ == "__main__":
    main()
