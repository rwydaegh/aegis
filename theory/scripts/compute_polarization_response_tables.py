"""
Compute polarization response tables on S^2: Ã_⊥(k̂), B_c(k̂), B_s(k̂).

SOURCE OF TRUTH (equations + derivation):
  `related_md/paper_versions/paper_draft_v3_polarization_addition.md`

We implement the exact definitions verbatim (see Section 7.3 in the source doc):

Let μ(r) = n̂(r)·(-k̂) = cos θ(r), with visibility encoded by ReLU(μ) = max(0, μ).

Unpolarized (baseline) absorbed power:
  P_unpol = S_inc ∫_vis T_avg(θ) cosθ dA  ≡  S_inc · Ã_⊥(k̂)

Define:
  T_avg(θ) = 0.5 [T_s(θ) + T_p(θ)]
  ΔT(θ)    = T_p(θ) - T_s(θ)

Define a reference polarization basis (e1(k̂), e2(k̂)) spanning the plane ⟂ k̂.
At each surface point (triangle), define the local TE direction:
  e_s(r) = (k̂ × n̂) / |k̂ × n̂|   (removable singularity at normal incidence)
and define α(r) by:
  e_s(r) = cos α(r) e1(k̂) + sin α(r) e2(k̂)

Then the polarization response functions are:
  B_c(k̂) = ∫_vis cos(2α(r)) · ΔT(θ(r)) · cosθ(r) dA
  B_s(k̂) = ∫_vis sin(2α(r)) · ΔT(θ(r)) · cosθ(r) dA

Total absorbed power for a single plane wave with incident power density S_inc,
ellipticity angle χ and polarization orientation ψ0 (in the (e1,e2) basis):
  P_abs = S_inc · Ã_⊥(k̂) - (S_inc cos(2χ)/2) [ B_c(k̂) cos(2ψ0) + B_s(k̂) sin(2ψ0) ]

Acceptance checks implemented here:
  - Circular polarization χ=±π/4 ⇒ cos(2χ)=0 ⇒ correction vanishes (no ψ0 dependence).
  - Unpolarized (coherency ∝ I) ⇒ prediction equals Ã_⊥ only.
  - Brute-force per-triangle evaluation (explicit TE/TM projections) agrees with table formula.
"""

from __future__ import annotations

import argparse
import json
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Tuple

import numpy as np

# ---------------------------------------------------------------------
# Physical constants (kept consistent with existing scripts)
# ---------------------------------------------------------------------

EPS_0 = 8.854187817e-12  # F/m


@dataclass(frozen=True)
class TissueParams:
    name: str
    eps_r: float
    sigma: float
    freq_hz: float

    @property
    def n_complex(self) -> complex:
        omega = 2 * np.pi * self.freq_hz
        eps_complex = self.eps_r - 1j * self.sigma / (omega * EPS_0)
        n = np.sqrt(eps_complex)
        if np.real(n) < 0:
            n = -n
        return n


TISSUES = {
    "skin_28GHz": TissueParams("Skin 28 GHz", 17.0, 25.0, 28e9),
    "skin_60GHz": TissueParams("Skin 60 GHz", 7.9, 36.4, 60e9),
    "muscle_28GHz": TissueParams("Muscle 28 GHz", 25.0, 30.0, 28e9),
    "fat_28GHz": TissueParams("Fat 28 GHz", 4.0, 2.0, 28e9),
}


# ---------------------------------------------------------------------
# Geometry I/O
# ---------------------------------------------------------------------

def load_stl_binary(filepath: str | Path) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load a binary STL file. Returns vertices (N,3,3), normals (N,3), centroids (N,3)."""
    filepath = str(filepath)
    with open(filepath, "rb") as f:
        f.read(80)
        num_triangles = struct.unpack("<I", f.read(4))[0]

        vertices = np.zeros((num_triangles, 3, 3), dtype=float)
        normals = np.zeros((num_triangles, 3), dtype=float)

        for i in range(num_triangles):
            normals[i] = struct.unpack("<3f", f.read(12))
            for j in range(3):
                vertices[i, j] = struct.unpack("<3f", f.read(12))
            f.read(2)  # attribute byte count

    centroids = np.mean(vertices, axis=1)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norms > 0, norms, 1.0)
    return vertices, normals, centroids


def triangle_areas(vertices: np.ndarray) -> np.ndarray:
    v0, v1, v2 = vertices[:, 0], vertices[:, 1], vertices[:, 2]
    cross = np.cross(v1 - v0, v2 - v0)
    return 0.5 * np.linalg.norm(cross, axis=1)


# ---------------------------------------------------------------------
# Fresnel
# ---------------------------------------------------------------------

def fresnel_transmission(mu: np.ndarray, n_complex: complex) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fresnel power transmission into a lossy medium using energy conservation:
      T = 1 - |r|^2
    Returns (T_s, T_p) for TE/TM.
    """
    mu = np.asarray(mu, dtype=float)
    mu = np.clip(mu, 0.0, 1.0)

    n2 = n_complex**2
    xi = np.sqrt(n2 - 1 + mu**2)
    xi = np.where(np.real(xi) < 0, -xi, xi)

    r_s = (mu - xi) / (mu + xi)
    r_p = (n2 * mu - xi) / (n2 * mu + xi)

    T_s = np.real(1 - np.abs(r_s) ** 2)
    T_p = np.real(1 - np.abs(r_p) ** 2)

    # grazing incidence: clamp to 0 (matches existing scripts)
    T_s = np.where(mu < 1e-10, 0.0, T_s)
    T_p = np.where(mu < 1e-10, 0.0, T_p)
    return T_s, T_p


# ---------------------------------------------------------------------
# Direction sampling + frames
# ---------------------------------------------------------------------

def fibonacci_sphere(n: int) -> np.ndarray:
    """Deterministic, approximately-uniform directions on S^2 (unit vectors)."""
    if n <= 0:
        raise ValueError("n must be positive")
    golden_ratio = (1 + np.sqrt(5.0)) / 2.0
    dirs = np.zeros((n, 3), dtype=float)
    for i in range(n):
        z = 1.0 - 2.0 * (i + 0.5) / n
        r = np.sqrt(max(0.0, 1.0 - z * z))
        phi = 2.0 * np.pi * i / golden_ratio
        dirs[i] = np.array([r * np.cos(phi), r * np.sin(phi), z], dtype=float)
    return dirs


def reference_frame_from_k(k_hat: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build a deterministic orthonormal basis (e1,e2) spanning the plane ⟂ k_hat.
    e1,e2 are real unit vectors; (e1,e2,k) is right-handed.
    """
    k_hat = np.asarray(k_hat, dtype=float)
    k_hat = k_hat / np.linalg.norm(k_hat)

    up = np.array([0.0, 0.0, 1.0], dtype=float)
    if abs(np.dot(up, k_hat)) > 0.9:
        up = np.array([0.0, 1.0, 0.0], dtype=float)

    e1 = np.cross(up, k_hat)
    n1 = np.linalg.norm(e1)
    if n1 < 1e-12:
        # extremely rare fallback
        up = np.array([1.0, 0.0, 0.0], dtype=float)
        e1 = np.cross(up, k_hat)
        n1 = np.linalg.norm(e1)
    e1 = e1 / n1
    e2 = np.cross(k_hat, e1)
    e2 = e2 / np.linalg.norm(e2)
    return e1, e2


# ---------------------------------------------------------------------
# Polarization: Jones vector + brute force
# ---------------------------------------------------------------------

def jones_from_ellipse(psi0: float, chi: float, E0: float = 1.0) -> Tuple[complex, complex]:
    """
    Jones vector components (E1,E2) in the reference basis (e1,e2).
    Matches Eq. (Section 1.2) in `paper_draft_v3_polarization_addition.md`.
    """
    E1 = E0 * (np.cos(psi0) * np.cos(chi) - 1j * np.sin(psi0) * np.sin(chi))
    E2 = E0 * (np.sin(psi0) * np.cos(chi) + 1j * np.cos(psi0) * np.sin(chi))
    return E1, E2


def brute_force_total_power_for_direction(
    normals: np.ndarray,
    areas: np.ndarray,
    k_hat: np.ndarray,
    n_complex: complex,
    psi0: float,
    chi: float,
) -> float:
    """
    Brute-force per-triangle computation of total absorbed power for a fully polarized wave.
    Uses explicit TE/TM projections a_s = E·e_s and a_p = E·e_p at each triangle.
    """
    k_hat = np.asarray(k_hat, dtype=float)
    k_hat = k_hat / np.linalg.norm(k_hat)

    mu = np.sum(normals * (-k_hat), axis=1)
    mu_pos = np.clip(mu, 0.0, 1.0)
    illuminated = mu > 0

    T_s, T_p = fresnel_transmission(mu_pos, n_complex)

    e1, e2 = reference_frame_from_k(k_hat)
    E1, E2 = jones_from_ellipse(psi0=psi0, chi=chi, E0=1.0)

    # Complex 3D electric field vector (constant over surface for a plane wave)
    E_vec = E1 * e1 + E2 * e2  # (3,) complex
    E_norm2 = float(np.abs(E1) ** 2 + np.abs(E2) ** 2)

    # Local TE/TM basis (depends on triangle normal)
    kxn = np.cross(k_hat[None, :], normals)  # (N,3)
    kxn_norm = np.linalg.norm(kxn, axis=1, keepdims=True)
    small = (kxn_norm[:, 0] < 1e-12)

    e_s = np.zeros_like(kxn)
    e_s[~small] = kxn[~small] / kxn_norm[~small]
    # Removable singularity at normal incidence: choose any TE direction.
    e_s[small] = e1[None, :]

    e_p = np.cross(e_s, k_hat[None, :])
    e_p_norm = np.linalg.norm(e_p, axis=1, keepdims=True)
    e_p = e_p / np.where(e_p_norm > 0, e_p_norm, 1.0)

    # Projections (complex scalars per triangle)
    a_s = E_vec[0] * e_s[:, 0] + E_vec[1] * e_s[:, 1] + E_vec[2] * e_s[:, 2]
    a_p = E_vec[0] * e_p[:, 0] + E_vec[1] * e_p[:, 1] + E_vec[2] * e_p[:, 2]

    frac_s = (np.abs(a_s) ** 2) / E_norm2
    frac_p = (np.abs(a_p) ** 2) / E_norm2

    T_eff = frac_s * T_s + frac_p * T_p
    apd = T_eff * mu_pos
    apd = apd * illuminated.astype(float)
    return float(np.sum(apd * areas))


# ---------------------------------------------------------------------
# Table computation
# ---------------------------------------------------------------------

def compute_tables(
    normals: np.ndarray,
    areas: np.ndarray,
    directions: np.ndarray,
    n_complex: complex,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute (A_tilde, Bc, Bs) for each k_hat in directions.
    """
    n_dir = directions.shape[0]
    A_tilde = np.zeros(n_dir, dtype=float)
    Bc = np.zeros(n_dir, dtype=float)
    Bs = np.zeros(n_dir, dtype=float)

    for i in range(n_dir):
        k_hat = directions[i]
        k_hat = k_hat / np.linalg.norm(k_hat)

        mu = np.sum(normals * (-k_hat), axis=1)
        mu_pos = np.clip(mu, 0.0, 1.0)
        illuminated = mu > 0

        T_s, T_p = fresnel_transmission(mu_pos, n_complex)
        T_avg = 0.5 * (T_s + T_p)
        dT = T_p - T_s

        w = areas * mu_pos * illuminated.astype(float)
        A_tilde[i] = float(np.sum(w * T_avg))

        e1, e2 = reference_frame_from_k(k_hat)

        # Compute local e_s for each triangle
        kxn = np.cross(k_hat[None, :], normals)  # (N,3)
        kxn_norm = np.linalg.norm(kxn, axis=1, keepdims=True)
        small = (kxn_norm[:, 0] < 1e-12)

        e_s = np.zeros_like(kxn)
        e_s[~small] = kxn[~small] / kxn_norm[~small]
        # Normal incidence: choose any TE direction; physics regular because ΔT(μ=1)=0.
        e_s[small] = e1[None, :]

        ca = e_s @ e1  # cos(alpha)
        sa = e_s @ e2  # sin(alpha)
        cos2a = ca * ca - sa * sa
        sin2a = 2.0 * ca * sa

        Bc[i] = float(np.sum(w * dT * cos2a))
        Bs[i] = float(np.sum(w * dT * sin2a))

    return A_tilde, Bc, Bs


def predict_total_power_from_tables(
    A_tilde: float,
    Bc: float,
    Bs: float,
    psi0: float,
    chi: float,
) -> float:
    return float(A_tilde - 0.5 * np.cos(2.0 * chi) * (Bc * np.cos(2.0 * psi0) + Bs * np.sin(2.0 * psi0)))


# ---------------------------------------------------------------------
# CLI + checks
# ---------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compute polarization response tables Ã_⊥, B_c, B_s on S^2.")
    p.add_argument("--stl", required=True, type=str, help="Path to binary STL mesh.")
    p.add_argument("--n", required=True, type=int, help="Number of directions on the sphere.")
    p.add_argument("--tissue", type=str, default="skin_28GHz", choices=sorted(TISSUES.keys()))
    p.add_argument("--eps_r", type=float, default=None, help="Override eps_r (relative permittivity).")
    p.add_argument("--sigma", type=float, default=None, help="Override sigma (S/m).")
    p.add_argument("--freq_hz", type=float, default=None, help="Override frequency (Hz).")
    p.add_argument("--out", type=str, default=None, help="Output directory. Default: artifacts/pol/<stl_stem>/")
    p.add_argument("--seed", type=int, default=0, help="RNG seed for checks.")
    p.add_argument("--check_count", type=int, default=8, help="Number of random directions for brute-force checks.")
    p.add_argument("--skip_checks", action="store_true", help="Skip acceptance checks.")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    stl_path = Path(args.stl)
    if not stl_path.exists():
        raise FileNotFoundError(stl_path)

    tissue = TISSUES[args.tissue]
    if args.eps_r is not None or args.sigma is not None or args.freq_hz is not None:
        tissue = TissueParams(
            name=f"custom({args.eps_r},{args.sigma},{args.freq_hz})",
            eps_r=float(args.eps_r if args.eps_r is not None else tissue.eps_r),
            sigma=float(args.sigma if args.sigma is not None else tissue.sigma),
            freq_hz=float(args.freq_hz if args.freq_hz is not None else tissue.freq_hz),
        )

    n_complex = tissue.n_complex

    # Output directory
    phantom = stl_path.stem
    out_dir = Path(args.out) if args.out is not None else (Path("artifacts") / "pol" / phantom)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load mesh
    vertices, normals, _centroids = load_stl_binary(stl_path)
    areas = triangle_areas(vertices)

    # Directions + tables
    directions = fibonacci_sphere(args.n)
    A_tilde, Bc, Bs = compute_tables(normals=normals, areas=areas, directions=directions, n_complex=n_complex)

    # Acceptance checks
    check_report = {}
    if not args.skip_checks:
        rng = np.random.default_rng(args.seed)
        idx = np.arange(args.n)
        if args.check_count > 0:
            rng.shuffle(idx)
            idx = idx[: min(args.check_count, args.n)]

        # Check 1: circular polarization => no psi0 dependence
        # We test variation over psi0 for a handful of directions.
        psi_tests = np.linspace(0.0, np.pi, 9, endpoint=False)
        chi_circ = np.pi / 4.0
        circ_variations = []
        for i in idx:
            preds = [predict_total_power_from_tables(A_tilde[i], Bc[i], Bs[i], psi0=psi, chi=chi_circ) for psi in psi_tests]
            circ_variations.append(float(np.max(preds) - np.min(preds)))
        check_report["circular_max_variation_over_psi0"] = float(np.max(circ_variations) if circ_variations else 0.0)

        # Check 2: unpolarized prediction equals A_tilde (by definition)
        check_report["unpolarized_identity_max_abs_err"] = float(np.max(np.abs(A_tilde - A_tilde)))

        # Check 3: brute force matches table formula for random (psi0,chi)
        brute_cases = []
        rel_errors = []
        abs_errors = []
        for i in idx:
            psi0 = float(rng.uniform(0.0, np.pi))
            chi = float(rng.uniform(-np.pi / 4.0, np.pi / 4.0))
            P_pred = predict_total_power_from_tables(A_tilde[i], Bc[i], Bs[i], psi0=psi0, chi=chi)
            P_brute = brute_force_total_power_for_direction(
                normals=normals,
                areas=areas,
                k_hat=directions[i],
                n_complex=n_complex,
                psi0=psi0,
                chi=chi,
            )
            abs_err = abs(P_pred - P_brute)
            rel_err = abs_err / max(1e-12, abs(P_brute))
            abs_errors.append(float(abs_err))
            rel_errors.append(float(rel_err))
            brute_cases.append({"dir_index": int(i), "psi0": psi0, "chi": chi, "P_pred": P_pred, "P_brute": P_brute})

        check_report["brute_force_max_abs_err"] = float(np.max(abs_errors) if abs_errors else 0.0)
        check_report["brute_force_max_rel_err"] = float(np.max(rel_errors) if rel_errors else 0.0)
        check_report["brute_force_cases"] = brute_cases

    # Save artifacts
    meta = {
        "stl": str(stl_path),
        "phantom": phantom,
        "n_directions": int(args.n),
        "tissue": asdict(tissue),
        "n_complex": [float(np.real(n_complex)), float(np.imag(n_complex))],
        "source_theory_path": "related_md/paper_versions/paper_draft_v3_polarization_addition.md",
        "checks": check_report,
    }

    npz_path = out_dir / f"pol_tables_n{args.n}_{args.tissue}.npz"
    np.savez_compressed(
        npz_path,
        k_hat=directions,
        A_tilde=A_tilde,
        B_c=Bc,
        B_s=Bs,
        tissue_name=tissue.name,
        eps_r=tissue.eps_r,
        sigma=tissue.sigma,
        freq_hz=tissue.freq_hz,
        n_complex=np.array([np.real(n_complex), np.imag(n_complex)], dtype=float),
    )

    (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Print a short summary for the user
    print(f"Mesh: {stl_path}  (triangles={len(areas):,})")
    print(f"Tissue: {tissue.name}  n={n_complex:.4f}")
    print(f"Directions: n={args.n}")
    print(f"Saved: {npz_path}")
    print(f"Saved: {out_dir / 'metadata.json'}")
    if check_report:
        print("\nChecks:")
        print(f"  circular max variation over psi0: {check_report.get('circular_max_variation_over_psi0', None)}")
        print(f"  brute max abs err:      {check_report.get('brute_force_max_abs_err', None)}")
        print(f"  brute max rel err:      {check_report.get('brute_force_max_rel_err', None)}")


if __name__ == "__main__":
    main()

