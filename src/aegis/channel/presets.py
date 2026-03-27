"""Parse QuaDRiGa .conf files and manage channel presets."""

from __future__ import annotations

import contextlib
import math
import re
from pathlib import Path

from aegis.defaults import DEFAULT_FREQ_HZ

KNOWN_PARAMS: dict[str, type] = {
    "DS_mu": float,
    "DS_sigma": float,
    "DS_omega": float,
    "DS_gamma": float,
    "DS_delta": float,
    "KF_mu": float,
    "KF_sigma": float,
    "SF_sigma": float,
    "AS_D_mu": float,
    "AS_D_sigma": float,
    "AS_D_omega": float,
    "AS_D_gamma": float,
    "AS_D_delta": float,
    "AS_A_mu": float,
    "AS_A_sigma": float,
    "AS_A_omega": float,
    "AS_A_gamma": float,
    "AS_A_delta": float,
    "ES_D_mu": float,
    "ES_D_sigma": float,
    "ES_D_omega": float,
    "ES_D_gamma": float,
    "ES_D_delta": float,
    "ES_A_mu": float,
    "ES_A_sigma": float,
    "ES_A_omega": float,
    "ES_A_gamma": float,
    "ES_A_delta": float,
    "XPR_mu": float,
    "XPR_sigma": float,
    "NumClusters": int,
    "NumSubPaths": int,
    "r_DS": float,
    "LNS_ksi": float,
    "PerClusterDS": float,
    "PerClusterAS_D": float,
    "PerClusterAS_A": float,
    "PerClusterES_D": float,
    "PerClusterES_A": float,
    "SC_lambda": float,
    "PL_model": str,
    "PL_A": float,
    "PL_B": float,
    "PL_C": float,
    "PL_A1": float,
    "PL_A2": float,
    "PL_E": float,
    "PL_hE": float,
    "PL_D": float,
    "PL_An": float,
    "PL_Bn": float,
    "PL_Cn": float,
    "PL_E3n": float,
}

_LINE_RE = re.compile(r"^(\w+)\s*=\s*(.+?)(?:\s*%.*)?$")


def parse_conf(path: Path | str) -> dict:
    """Parse a QuaDRiGa .conf file into a flat dict of typed values."""
    path = Path(path)
    params: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        key, raw_val = m.group(1), m.group(2).strip()
        if key in KNOWN_PARAMS:
            typ = KNOWN_PARAMS[key]
            with contextlib.suppress(ValueError, TypeError):
                params[key] = typ(raw_val)
    return params


def scale_param(
    mu: float,
    omega: float = 1.0,
    gamma: float = 0.0,
    freq_ghz: float = DEFAULT_FREQ_HZ / 1e9,
) -> float:
    """Apply frequency-dependent scaling: mu + gamma * log10(omega + freq)."""
    return mu + gamma * math.log10(omega + freq_ghz)


def load_preset(name: str, preset_dir: Path | str) -> dict:
    """Load a named preset from the preset directory."""
    preset_dir = Path(preset_dir)
    path = preset_dir / f"{name}.conf"
    if not path.exists():
        raise FileNotFoundError(f"Preset not found: {path}")
    params = parse_conf(path)
    return {"name": name, "params": params}


def list_presets(preset_dir: Path | str) -> list[str]:
    """List available preset names (stem of .conf files)."""
    preset_dir = Path(preset_dir)
    return sorted(p.stem for p in preset_dir.glob("*.conf"))
