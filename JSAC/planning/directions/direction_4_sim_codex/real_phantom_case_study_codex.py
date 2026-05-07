"""Reproducible case study for direction 4 spatial compliance.

Builds a local 4 cm^2 operator family on a real AEGIS phantom and compares
its worst patch against the whole-body exposure operator for a simple coherent
cone-illumination model.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from aegis.coherent.body_channel import compute_body_channel
from aegis.coherent.exposure_operator import compute_exposure_operator
from aegis.geometry.averaging import precompute_averaging_matrix
from aegis.geometry.mesh import BodyMesh
from aegis.paths import PropagationPaths
from aegis.tissue.dielectric import SKIN_28GHZ


PUBLIC_SAB_4CM2_LIMIT = 20.0
PUBLIC_SAR_WB_LIMIT = 0.08
AVERAGING_AREA_M2 = 4e-4


def cone_directions(center: np.ndarray, spread_deg: float, n_paths: int) -> np.ndarray:
    """Return equally spaced directions on a cone around ``center``."""
    center = np.asarray(center, dtype=np.float64)
    center = center / np.linalg.norm(center)

    ref = np.array([0.0, 0.0, 1.0]) if abs(center[2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(center, ref)
    u = u / np.linalg.norm(u)
    v = np.cross(center, u)

    if n_paths == 1:
        return center[None, :]

    ang = np.deg2rad(spread_deg)
    dirs = np.empty((n_paths, 3), dtype=np.float64)
    for k in range(n_paths):
        phi = 2.0 * np.pi * k / n_paths
        d = center * np.cos(ang) + (u * np.cos(phi) + v * np.sin(phi)) * np.sin(ang)
        dirs[k] = d / np.linalg.norm(d)
    return dirs


def local_operator_family(
    G_avg,
    G_tilde: np.ndarray,
) -> np.ndarray:
    """Build ``Q_local[m] = sum_i G_avg[m, i] G_i^H G_i`` for every patch center."""
    gram_per_triangle = np.einsum("mia,mib->mab", np.conj(G_tilde), G_tilde)
    n_triangles, _, n_ant = G_tilde.shape
    q_local = np.empty((n_triangles, n_ant, n_ant), dtype=complex)
    for a in range(n_ant):
        for b in range(n_ant):
            q_local[:, a, b] = G_avg @ gram_per_triangle[:, a, b]
    return q_local


def hotspot_metrics(
    body: BodyMesh,
    G_avg,
    *,
    center: np.ndarray,
    spread_deg: float,
    n_paths: int,
) -> dict[str, float | int | str | dict[str, bool]]:
    """Compute the worst-patch local operator metrics for one coherent cone."""
    paths = PropagationPaths.from_powers(
        k_hat=cone_directions(center, spread_deg=spread_deg, n_paths=n_paths),
        power=np.ones(n_paths, dtype=np.float64),
    )
    G_tilde = np.asarray(
        compute_body_channel(
            body.normals,
            body.centroids,
            paths.k_hat,
            paths.psi,
            paths.element_index,
            SKIN_28GHZ.n_complex,
            SKIN_28GHZ.sigma,
            SKIN_28GHZ.freq_hz,
            n_elements=paths.n_elements,
        )
    )
    Q = np.asarray(compute_exposure_operator(G_tilde, body.areas))
    Q_local = local_operator_family(G_avg, G_tilde)

    local_eigs = np.linalg.eigvalsh(Q_local)
    local_lambda_max = local_eigs[:, -1]
    patch_index = int(np.argmax(local_lambda_max))

    _, patch_vecs = np.linalg.eigh(Q_local[patch_index])
    x_star = patch_vecs[:, -1]
    x_star = x_star / np.linalg.norm(x_star)

    peak_patch_apd = float(np.real(x_star.conj() @ Q_local[patch_index] @ x_star))
    p_abs = float(np.real(x_star.conj() @ Q @ x_star))
    mean_apd_whole_body = p_abs / body.total_area
    eta_4cm2 = peak_patch_apd / mean_apd_whole_body

    thresholds = {
        "adult": PUBLIC_SAB_4CM2_LIMIT * 1.8 / (70.0 * PUBLIC_SAR_WB_LIMIT),
        "child": PUBLIC_SAB_4CM2_LIMIT * 0.8 / (20.0 * PUBLIC_SAR_WB_LIMIT),
        "infant": PUBLIC_SAB_4CM2_LIMIT * 0.4 / (8.0 * PUBLIC_SAR_WB_LIMIT),
    }
    binds_before_sar = {name: eta_4cm2 > thr for name, thr in thresholds.items()}

    return {
        "n_paths": n_paths,
        "center_label": "minus_x_cone",
        "spread_deg": spread_deg,
        "peak_patch_apd_w_m2": peak_patch_apd,
        "p_abs_w": p_abs,
        "whole_body_mean_apd_w_m2": mean_apd_whole_body,
        "eta_4cm2": eta_4cm2,
        "lambda_max_Q": float(np.linalg.eigvalsh(Q)[-1]),
        "worst_patch_index": patch_index,
        "binds_before_sar": binds_before_sar,
    }


def run_case_study() -> dict:
    """Run the labeled real-phantom case study and return a JSON-able dict."""
    body = BodyMesh.load(REPO_ROOT / "data" / "thelonious.stl")
    G_avg = precompute_averaging_matrix(body.centroids, body.areas, AVERAGING_AREA_M2)

    center = np.array([-1.0, 0.0, 0.0], dtype=np.float64)
    rows = [
        hotspot_metrics(body, G_avg, center=center, spread_deg=20.0, n_paths=n)
        for n in [1, 2, 4, 8, 16]
    ]

    return {
        "body": {
            "name": body.name,
            "n_triangles": body.n_triangles,
            "total_area_m2": body.total_area,
            "height_m": body.height,
        },
        "tissue": {
            "name": "SKIN_28GHZ",
            "freq_hz": SKIN_28GHZ.freq_hz,
        },
        "limits": {
            "sab_4cm2_public_w_m2": PUBLIC_SAB_4CM2_LIMIT,
            "sar_wb_public_w_kg": PUBLIC_SAR_WB_LIMIT,
            "eta_thresholds": {
                "adult": PUBLIC_SAB_4CM2_LIMIT * 1.8 / (70.0 * PUBLIC_SAR_WB_LIMIT),
                "child": PUBLIC_SAB_4CM2_LIMIT * 0.8 / (20.0 * PUBLIC_SAR_WB_LIMIT),
                "infant": PUBLIC_SAB_4CM2_LIMIT * 0.4 / (8.0 * PUBLIC_SAR_WB_LIMIT),
            },
        },
        "case_study": rows,
    }


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    out_path = out_dir / "real_phantom_case_study_codex.json"
    data = run_case_study()
    out_path.write_text(json.dumps(data, indent=2))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
