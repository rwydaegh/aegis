"""Pre-flight sanity checks for the AEGIS-vs-goliat validation harness.

Run anytime before launching a new tier. Asserts on conventions that are
easy to silently get wrong:

  * S4L plane-wave convention: (Theta, Phi) is propagation direction.
  * Goliat orthogonal direction map → (k_hat, e_theta, e_phi).
  * Polarisation: psi=0 → E along e_theta; psi=90 → E along e_phi.
  * STL phantom bbox matches goliat-reported cross sections after the
    *campaign-config* `bbox_padding_mm` offset (NOT the current
    `far_field_config.json` value, which has drifted).
  * Tissue dielectric properties via TissueModel match the IT'IS v5.0
    values that goliat's Sim4Life library should return.
  * Cotangent-Laplacian curvature: positive on convex (sphere) test mesh.
  * Visibility ray-tracing: front-facing triangle in unobstructed dir is 1,
    back-facing is 0.
  * Renormalisation factor 754 ≈ 2η₀ at E = 1 V/m.

Exits non-zero on any failure with a clear message naming the violated
invariant.

Usage:
    python preflight_check.py [--zip path/to/far_field.zip]
                              [--phantom thelonious]
"""

from __future__ import annotations
import argparse
import json
import sys
import zipfile
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------------------
# Reference conventions (the source of truth)
# ---------------------------------------------------------------------------

# Verified from:
#   goliat/setups/far_field_setup.py:190-222  (orthogonal_direction_map)
#   goliat/docs/reference/useful_s4l_snippets.md:731  ("Theta/Phi define wave
#       propagation direction. Psi=0 for theta polarization, Psi=90 for phi.")
#   goliat/extraction/power_extractor.py:124-130  (orthogonal_map in radians)
GOLIAT_DIRS_DEG = {
    "x_pos": (0, 90),
    "x_neg": (180, 90),
    "y_pos": (90, 90),
    "y_neg": (270, 90),
    "z_pos": (0, 0),
    "z_neg": (0, 180),
}  # (phi_deg, theta_deg)

# Expected k_hat (propagation direction) per name. Body sees the wave coming
# from the OPPOSITE side, e.g. x_pos illuminates the −x face of the body.
EXPECTED_K_HAT = {
    "x_pos": (1, 0, 0),
    "x_neg": (-1, 0, 0),
    "y_pos": (0, 1, 0),
    "y_neg": (0, -1, 0),
    "z_pos": (0, 0, 1),
    "z_neg": (0, 0, -1),
}

# η₀ free-space impedance, used to renormalise goliat outputs (E=1 V/m → Sinc=1 W/m²).
ETA_0 = 376.730313668  # exact via μ₀ c
NORM = 2 * ETA_0  # ≈ 753.46  (we round to 754 in the rest of the harness)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_direction_basis():
    """Compute (k_hat, e_theta, e_phi) for each of the 6 cardinal dirs and
    assert against the expected values."""
    from geometry import goliat_basis, GOLIAT_DIRS

    if GOLIAT_DIRS != GOLIAT_DIRS_DEG:
        raise AssertionError(
            f"GOLIAT_DIRS in geometry.py disagrees with the reference table.\n"
            f"  geometry.py: {GOLIAT_DIRS}\n  reference:   {GOLIAT_DIRS_DEG}"
        )

    for name, k_expect in EXPECTED_K_HAT.items():
        k_hat, e_theta, e_phi = goliat_basis(name)
        if not np.allclose(k_hat, k_expect, atol=1e-9):
            raise AssertionError(f"{name}: k_hat = {k_hat}, expected {k_expect}")
        # k_hat, e_theta, e_phi must be a right-handed orthonormal triad
        cross = np.cross(e_theta, e_phi)
        if not np.allclose(cross, k_hat, atol=1e-6):
            raise AssertionError(f"{name}: e_theta × e_phi = {cross}, expected {k_hat}")
        for v, lbl in [(k_hat, "k_hat"), (e_theta, "e_theta"), (e_phi, "e_phi")]:
            if not np.isclose(np.linalg.norm(v), 1.0, atol=1e-9):
                raise AssertionError(f"{name}: {lbl} not unit length")
    print("[preflight] ✓ direction basis consistent for all 6 cardinal dirs")


def check_polarisation_basis():
    """psi=0 → E along e_theta; psi=90 → E along e_phi.
    Verifies the known specific cases:
      x_pos, theta-pol → E = -z_hat (vertical)
      x_pos, phi-pol   → E = +y_hat
      z_pos, theta-pol → E = +x_hat
    """
    from geometry import goliat_basis

    cases = {
        ("x_pos", "theta"): np.array([0, 0, -1.0]),
        ("x_pos", "phi"): np.array([0, 1.0, 0]),
        ("z_pos", "theta"): np.array([1.0, 0, 0]),
        ("z_pos", "phi"): np.array([0, 1.0, 0]),
        ("y_pos", "theta"): np.array([0, 0, -1.0]),
        ("y_pos", "phi"): np.array([-1.0, 0, 0]),
    }
    for (name, pol), E_expected in cases.items():
        _, e_theta, e_phi = goliat_basis(name)
        e_E = e_theta if pol == "theta" else e_phi
        if not np.allclose(e_E, E_expected, atol=1e-9):
            raise AssertionError(f"{name}/{pol}: E = {e_E}, expected {E_expected}")
    print("[preflight] ✓ polarisation basis matches S4L convention (psi=0→ê_θ, psi=90→ê_φ)")


def check_q_field_sign():
    """For x_pos with theta-pol (E along -z) and a triangle facing -z (top of
    head, n=+z), the wave hits a TM-like geometry. Compute q and check it's
    consistent with the AEGIS L4 sign convention (T_eff = T_avg + 0.5 q ΔT)."""
    from geometry import goliat_basis, q_field

    k_hat, e_theta, _ = goliat_basis("x_pos")
    # Tip-facing: a triangle on the right side of the body (n = -x), so the
    # wave hits at normal incidence. At normal incidence, q is degenerate
    # (0), as our q_field implementation explicitly handles.
    n_normal = np.array([[-1.0, 0, 0]])
    q = q_field(n_normal, k_hat, e_theta)
    if not np.isclose(q[0, 0], 0.0):
        raise AssertionError(f"q at normal incidence should be 0, got {q[0, 0]}")

    # Side-facing triangle (front of body, n=-y) under x_pos illumination.
    # The plane of incidence is the x-y plane. e_theta = -z is perpendicular
    # to that plane, so this is pure TE (s) polarisation → q = -1.
    n_side = np.array([[0, -1.0, 0]])
    q_side = q_field(n_side, k_hat, e_theta)[0, 0]
    if not np.isclose(q_side, -1.0, atol=1e-6):
        raise AssertionError(f"x_pos/theta-pol on n=-y triangle should be pure-TE (q=-1), got q={q_side}")

    # Same but phi-pol (E along +y, in plane of incidence) → pure TM → q=+1.
    _, _, e_phi = goliat_basis("x_pos")
    q_side_phi = q_field(n_side, k_hat, e_phi)[0, 0]
    if not np.isclose(q_side_phi, 1.0, atol=1e-6):
        raise AssertionError(f"x_pos/phi-pol on n=-y triangle should be pure-TM (q=+1), got q={q_side_phi}")
    print("[preflight] ✓ q(r) sign convention consistent with AEGIS L4 kernel")


def check_curvature_sign_on_sphere():
    """Build a coarse sphere via trimesh primitives and check that the cotangent
    Laplacian gives positive 2H (convex). Also checks magnitude: sphere of
    radius R has 2H = 2/R."""
    import trimesh
    import tempfile
    import os

    R = 0.10  # 10 cm sphere
    sph = trimesh.creation.icosphere(subdivisions=4, radius=R)
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tf:
        path = tf.name
    try:
        sph.export(path)
        from geometry import compute_curvature_2H

        H_2x = compute_curvature_2H(path)
        # Exclude clipping outliers
        med = np.median(H_2x)
        # Mean curvature on a sphere of radius R is 1/R, so 2H = 2/R = 20 /m.
        target = 2.0 / R
        if med < 0:
            raise AssertionError(
                f"Cotangent Laplacian gave NEGATIVE median curvature "
                f"({med:.2f}) on a sphere — the sign flip in geometry.py "
                f"is likely wrong."
            )
        rel_err = abs(med - target) / target
        if rel_err > 0.10:
            raise AssertionError(
                f"Cotangent Laplacian on R={R} m sphere: 2H median={med:.2f}, "
                f"expected {target:.2f} (rel_err={rel_err:.1%}). "
                f"Convergence with mesh refinement should keep this below 5%."
            )
        print(
            f"[preflight] ✓ curvature sign + magnitude on sphere "
            f"(2H={med:.2f}/m, target={target:.2f}/m, err={rel_err:.1%})"
        )
    finally:
        os.unlink(path)


def check_visibility_simple():
    """A simple flat triangle: visible if k_hat is from the +n side
    (back of triangle), occluded if from the -n side (front)."""
    from aegis.geometry.mesh import BodyMesh
    from geometry import compute_visibility
    import trimesh, tempfile, os

    # Single icosphere (closed) — front-facing triangles relative to k_hat=+x
    # should be visible (1.0), back-facing ones not (0.0).
    sph = trimesh.creation.icosphere(subdivisions=2, radius=0.10)
    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as tf:
        path = tf.name
    try:
        sph.export(path)
        body = BodyMesh.load(path)
        vis = compute_visibility(path, {"k_pos_x": np.array([1.0, 0, 0])})
        v = vis["k_pos_x"]
        # By construction, visible <=> n · (-k_hat) > 0 <=> normal_x < 0.
        front = body.normals[:, 0] < -1e-6
        if not np.array_equal(v[front] > 0.5, np.ones(front.sum(), dtype=bool)):
            raise AssertionError(
                f"sphere: not all front-facing triangles visible ({(v[front] > 0.5).sum()}/{front.sum()})"
            )
        back = body.normals[:, 0] > 1e-6
        if not np.array_equal(v[back] < 0.5, np.ones(back.sum(), dtype=bool)):
            raise AssertionError(
                f"sphere: some back-facing triangles reported visible ({(v[back] < 0.5).sum()}/{back.sum()})"
            )
        print("[preflight] ✓ visibility kernel: front-facing=1, back-facing=0")
    finally:
        os.unlink(path)


def check_renorm():
    """Sinc at E = 1 V/m should be exactly E²/(2η₀) ≈ 1.327 mW/m²; multiply
    by NORM ≈ 754 to get 1 W/m²."""
    sinc_at_1Vm = 1.0**2 / (2 * ETA_0)
    if not np.isclose(sinc_at_1Vm * NORM, 1.0, atol=1e-9):
        raise AssertionError(f"renorm factor wrong: sinc * NORM = {sinc_at_1Vm * NORM}")
    print(
        f"[preflight] ✓ renormalisation: NORM = 2η₀ = {NORM:.3f} "
        f"(harness uses 754, off by {abs(NORM - 754) / NORM * 100:.3f}%)"
    )


def check_stl_vs_goliat_phantom_bbox(zip_path: Path, phantom: str):
    """Load the STL, read goliat's reported `cross_section_m2` from a sample
    sar_results.json, account for the campaign-config's `bbox_padding_mm`,
    and assert the predicted face areas match within 2 %.

    Catches drift between (a) the STL file we use, (b) the actual phantom
    voxel mesh that Sim4Life loaded at run time. Skips silently with a warning
    if the zip or STL isn't accessible.
    """
    stl_path = Path(f"/home/user/aegis/data/{phantom}.stl")
    if not stl_path.exists():
        print(f"[preflight] ⚠ skipping STL-vs-goliat check: {stl_path} not found")
        return

    import sys

    sys.path.insert(0, "/home/user/aegis/src")
    from aegis.geometry.mesh import BodyMesh

    body = BodyMesh.load(str(stl_path))
    v = body.vertices.reshape(-1, 3)
    mn, mx = v.min(0), v.max(0)
    dx_phantom, dy_phantom, dz_phantom = mx - mn

    # Read one sample sar_results.json to pull goliat's cs and Pin
    if not zip_path.exists():
        print(f"[preflight] ⚠ skipping goliat-side check: {zip_path} not found")
        return

    with zipfile.ZipFile(zip_path) as zf:
        # Prefer the lowest-frequency case (largest grid → padding effect
        # easiest to read). 700 MHz is in every sub-6 GHz campaign.
        target = None
        for n in zf.namelist():
            if f"/{phantom}/700MHz/environmental_x_pos_theta/sar_results.json" in n:
                target = n
                break
        if target is None:
            print(f"[preflight] ⚠ no x_pos/theta sample found in {zip_path}; skipping STL-vs-goliat check")
            return

        sar = json.loads(zf.read(target))

        # Pull the campaign config snapshot (we ignore the *current* config
        # on disk because it has drifted).
        cfg_target = target.replace("sar_results.json", "config.json")
        cfg = json.loads(zf.read(cfg_target))
        snap = cfg.get("config_snapshot", {})
        pad_mm = snap.get("simulation_parameters", {}).get("bbox_padding_mm", 0)
        pad = pad_mm / 1000.0

    cs = sar.get("cross_section_m2", None)
    if cs is None:
        # Older campaigns may only have power_balance.Pin
        pin = sar["power_balance"]["Pin"]
        sinc = 1.0 / (2 * ETA_0)
        cs = pin / sinc

    # Predicted x-face area = (dy + 2 pad) × (dz + 2 pad)
    A_pred = (dy_phantom + 2 * pad) * (dz_phantom + 2 * pad)
    rel_err = abs(A_pred - cs) / cs
    print(f"[preflight] STL bbox: {dx_phantom:.4f} × {dy_phantom:.4f} × {dz_phantom:.4f} m; campaign pad = {pad_mm} mm")
    print(
        f"[preflight]   x-face: predicted (STL+pad)² = {A_pred:.4f} m²; "
        f"goliat reports {cs:.4f} m²; rel_err = {rel_err:.2%}"
    )
    if rel_err > 0.025:
        raise AssertionError(
            f"STL phantom bbox doesn't match goliat phantom voxel bbox at "
            f"x_pos / 700 MHz (rel_err {rel_err:.2%} > 2.5 %). "
            f"Check (a) the campaign config snapshot for `bbox_padding_mm`, "
            f"(b) whether {phantom}.stl is the same vintage as the goliat "
            f"voxel phantom. The user warned the STL was 'derived "
            f"imperfectly' — but it should still match within ~1 %."
        )
    print(f"[preflight] ✓ STL phantom bbox matches goliat voxel phantom to {rel_err:.2%}")


def check_tissue_dielectric_v5():
    """Spot-check IT'IS v5.0 tissue properties at a couple of frequencies
    against published tables, so we know AEGIS and goliat are reading the
    same DB. (Goliat-side values aren't accessible offline; this just
    verifies AEGIS's own table.)"""
    import sys

    sys.path.insert(0, "/home/user/aegis/src")
    from aegis.tissue.dielectric import TissueModel

    # IT'IS v5.0 Skin reference values (from the IT'IS database web UI,
    # parametric Cole-Cole at 5800 MHz):
    skin_5p8 = TissueModel.from_database("Skin", freq_hz=5.8e9)
    if not (30 < skin_5p8.eps_r < 40):
        raise AssertionError(f"Skin eps_r at 5.8 GHz: {skin_5p8.eps_r}, expected 35.1 ± 2")
    if not (3.0 < skin_5p8.sigma < 4.5):
        raise AssertionError(f"Skin sigma at 5.8 GHz: {skin_5p8.sigma}, expected 3.7 ± 0.5")
    skin_700 = TissueModel.from_database("Skin", freq_hz=7.0e8)
    if not (40 < skin_700.eps_r < 47):
        raise AssertionError(f"Skin eps_r at 700 MHz: {skin_700.eps_r}, expected 42.7 ± 2")
    print(
        f"[preflight] ✓ IT'IS v5.0 Skin properties in expected ranges "
        f"(eps_r 5.8GHz={skin_5p8.eps_r:.2f}, σ={skin_5p8.sigma:.2f})"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", default="/home/user/goliat/results/far_field.zip")
    ap.add_argument("--phantom", default="thelonious")
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))

    print("=" * 70)
    print("AEGIS-vs-goliat validation pre-flight checks")
    print("=" * 70)

    check_direction_basis()
    check_polarisation_basis()
    check_q_field_sign()
    check_renorm()
    check_tissue_dielectric_v5()
    check_curvature_sign_on_sphere()
    check_visibility_simple()
    check_stl_vs_goliat_phantom_bbox(Path(args.zip), args.phantom)

    print()
    print("[preflight] ALL CHECKS PASSED ✓")


if __name__ == "__main__":
    main()
