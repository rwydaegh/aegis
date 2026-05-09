"""
Integrated diffraction effect on Thelonious whole-body absorbed power
=====================================================================

Reports (P_diff - P_simp) / P_simp on the Thelonious phantom at 1, 3,
6, 10, 15, 28, 40, 60, 77, 100 GHz, averaged over 6 cardinal incidence
directions. Both baselines use T_0 (so the entry isolates the
diffraction correction, with no Fresnel-angular contribution).

  - P_simp = T_0 * sum(area * [mu]_+)
  - P_diff = T_0 * sum(area * GELU(mu)) + T_0 * (H/k) * GELU(mu)^2 * area

Mean curvature H is taken from the cotangent Laplacian on the
merged-vertex Thelonious mesh.

Reproduces Table tab:si-diffraction in the SI.
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
from scipy.special import erf

# AEGIS source tree
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "validation" / "scripts"))

from aegis.geometry.mesh import BodyMesh
from aegis.tissue.dielectric import TissueModel
from aegis.constants import C_0
from geometry import compute_curvature_2H

EPS_0 = 8.854187817e-12

MESH = str(Path(__file__).resolve().parents[3] / "data" / "thelonious.stl")

DIRS = {
    "+x": np.array([1, 0, 0]),
    "-x": np.array([-1, 0, 0]),
    "+y": np.array([0, 1, 0]),
    "-y": np.array([0, -1, 0]),
    "+z": np.array([0, 0, 1]),
    "-z": np.array([0, 0, -1]),
}

FREQS_GHZ = [1.0, 3.0, 6.0, 10.0, 15.0, 28.0, 40.0, 60.0, 77.0, 100.0]


def main() -> None:
    body = BodyMesh.load(MESH)
    H_2x = compute_curvature_2H(MESH)
    H = 0.5 * H_2x  # mean curvature 1/m
    H_safe = np.maximum(H, 0.0)

    print(f"Thelonious: {len(body.areas)} triangles, "
          f"area = {body.areas.sum() * 1e4:.1f} cm^2")

    print()
    print("Integrated diffraction effect on Thelonious (6 cardinal dirs averaged)")
    print("-" * 64)
    print(f"{'f [GHz]':>10} {'P_simp [mW/m2]':>16} {'P_diff [mW/m2]':>16} "
          f"{'effect':>10}")

    for f_ghz in FREQS_GHZ:
        f_hz = f_ghz * 1e9
        tis = TissueModel.from_database("Skin", freq_hz=f_hz)
        eps_c = complex(tis.eps_r, -tis.sigma / (2 * np.pi * f_hz * EPS_0))
        n_t = complex(np.sqrt(eps_c))
        T0 = float(1 - abs((1 - n_t) / (1 + n_t)) ** 2)
        wavelength = C_0 / f_hz
        k = 2 * np.pi / wavelength
        sigma_j = np.sqrt(np.maximum(wavelength * H_safe / (4 * np.pi), 1e-20))

        P_simp_list, P_diff_list = [], []
        for k_hat in DIRS.values():
            mu = body.normals @ (-k_hat)
            mu_plus = np.maximum(mu, 0.0)
            P_simp = T0 * float((body.areas * mu_plus).sum())

            ratio = np.divide(mu, sigma_j, where=sigma_j > 0,
                              out=np.zeros_like(mu))
            mu_gelu = mu * 0.5 * (1.0 + erf(ratio))
            sab = T0 * mu_gelu + T0 * (H_safe / k) * mu_gelu ** 2
            P_diff = float((body.areas * np.maximum(sab, 0.0)).sum())

            P_simp_list.append(P_simp)
            P_diff_list.append(P_diff)

        P_simp = float(np.mean(P_simp_list))
        P_diff = float(np.mean(P_diff_list))
        effect = (P_diff / P_simp - 1) * 100
        print(f"{f_ghz:>10.3f} {P_simp * 1e3:>16.4f} {P_diff * 1e3:>16.4f} "
              f"{effect:>+9.2f}%")


if __name__ == "__main__":
    main()
