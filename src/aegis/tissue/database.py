"""IT'IS v5.0 tissue database loader.

Reads Gabriel model parameters from the SQLite database and computes
frequency-dependent tissue properties via the 4-pole Cole-Cole model.
"""

from __future__ import annotations

import cmath
import os
import sqlite3
import struct
from pathlib import Path

import numpy as np

from aegis.constants import EPS_0
from aegis.tissue.cole_cole import cole_cole_permittivity


def find_database() -> Path:
    """Locate the IT'IS v5.0 SQLite database.

    Search order:
    1. AEGIS_DATA_DIR environment variable
    2. Default data directory (../../data relative to aegis/)
    """
    candidates: list[Path] = []

    env_path = os.environ.get("AEGIS_DATA_DIR")
    if env_path:
        candidates.append(Path(env_path) / "itis_v5.db")

    # Default: aegis/../../data/ (Geometric Dosimetry/data/)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    candidates.append(repo_root.parent / "data" / "itis_v5.db")

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError("Could not find itis_v5.db. Set AEGIS_DATA_DIR or place it in ../data/.")


def get_gabriel_params(tissue_name: str, db_path: Path | None = None) -> dict | None:
    """Extract Gabriel model parameters (14 doubles) from the database.

    Parameters
    ----------
    tissue_name
        Tissue name as stored in the database (e.g. "Skin", "Muscle").
    db_path
        Explicit path to itis_v5.db. Auto-detected if None.

    Returns
    -------
    Dict with keys: ef, del1..del4, tau1..tau4, alf1..alf4, sig.
    None if tissue not found.
    """
    if db_path is None:
        db_path = find_database()

    conn = sqlite3.connect(str(db_path))
    try:
        c = conn.cursor()

        c.execute("SELECT prop_id FROM properties WHERE name = ?", ("Gabriel Parameters",))
        row = c.fetchone()
        if row is None:
            return None
        prop_id = row[0]

        c.execute(
            """SELECT v.vals
               FROM materials m
               JOIN vectors v ON m.mat_id = v.mat_id
               WHERE m.name = ? AND v.prop_id = ?
               LIMIT 1""",
            (tissue_name, prop_id),
        )
        row = c.fetchone()
        if row is None:
            return None

        blob = row[0]
        if len(blob) < 14 * 8:
            return None

        values = struct.unpack("d" * 14, blob[: 14 * 8])
        return {
            "ef": values[0],
            "del1": values[1],
            "tau1": values[2],
            "alf1": values[3],
            "del2": values[4],
            "tau2": values[5],
            "alf2": values[6],
            "del3": values[7],
            "tau3": values[8],
            "alf3": values[9],
            "del4": values[10],
            "tau4": values[11],
            "alf4": values[12],
            "sig": values[13],
        }
    finally:
        conn.close()


def get_tissue_properties(tissue_name: str, freq_hz: float, db_path: Path | None = None) -> dict:
    """Full tissue EM properties at a given frequency from the IT'IS database.

    Parameters
    ----------
    tissue_name
        Tissue name (e.g. "Skin").
    freq_hz
        Frequency in Hz.
    db_path
        Explicit path to itis_v5.db. Auto-detected if None.

    Returns
    -------
    Dict with keys: freq_hz, eps_r, sigma, m (complex refractive index),
    n, kappa, abs_m, T0.
    """
    params = get_gabriel_params(tissue_name, db_path=db_path)
    if params is None:
        raise ValueError(f"Could not load Gabriel parameters for '{tissue_name}'")

    eps_complex = cole_cole_permittivity(freq_hz, params)

    # Complex refractive index
    m = cmath.sqrt(eps_complex)
    if m.real < 0:
        m = -m

    n = m.real
    kappa = -m.imag  # positive for absorption

    # Normal-incidence transmission
    T0 = 4 * n / ((1 + n) ** 2 + kappa**2)

    # Recover real eps_r and effective conductivity
    omega = 2 * np.pi * freq_hz
    eps_r = eps_complex.real
    sigma = -eps_complex.imag * omega * EPS_0

    return {
        "freq_hz": freq_hz,
        "eps_r": eps_r,
        "sigma": sigma,
        "m": m,
        "n": n,
        "kappa": kappa,
        "abs_m": abs(m),
        "T0": T0,
    }
