"""
Task 03: Non-isotropic angular power spectra examples using D(k_hat).

Goal: demonstrate that directional averaging is a normalization tool.
Once D(k_hat) is known, absorbed-power scaling for any angular spectrum rho(k_hat)
is a cheap integral:

  F = (1/(4*pi)) * integral_{S^2} rho(k_hat) * D(k_hat) dOmega

Normalization convention:
  integral rho dOmega = 4*pi  (so isotropic rho = 1).

Discrete approximation:
  If k_hat directions sample S^2 uniformly, then
    F ~= mean_i [ rho_i * D_i ].
  If the sampler is not uniform, provide quadrature weights w_i and use
    weighted averages.

Acceptance:
  python scripts/angular_spectrum_examples.py --lut artifacts/body/thelonious/A_perp_lut.npz
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt


def _weighted_mean(x: np.ndarray, w: Optional[np.ndarray]) -> float:
    x = np.asarray(x, dtype=float).reshape(-1)
    if w is None:
        return float(np.mean(x))
    w = np.asarray(w, dtype=float).reshape(-1)
    if w.shape != x.shape:
        raise ValueError(f"weights shape {w.shape} must match x shape {x.shape}")
    s = float(np.sum(w))
    if not np.isfinite(s) or s <= 0:
        raise ValueError("weights must sum to a positive finite number")
    return float(np.sum(w * x) / s)


def _normalize_rho(rho_raw: np.ndarray, w: Optional[np.ndarray]) -> np.ndarray:
    """Normalize rho so that weighted_mean(rho) == 1 (proxy for integral rho dOmega = 4*pi)."""
    rho_raw = np.asarray(rho_raw, dtype=float).reshape(-1)
    m = _weighted_mean(rho_raw, w)
    if not np.isfinite(m) or m <= 0:
        raise ValueError("rho_raw must have positive finite mean to be normalized")
    return rho_raw / m


def _load_npz(path: Path) -> Dict[str, np.ndarray]:
    with np.load(path) as data:
        return {k: np.asarray(v) for k, v in data.items()}


def _load_directivity(
    *, lut_path: Optional[Path], directivity_path: Optional[Path]
) -> Tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    if (lut_path is None) == (directivity_path is None):
        raise ValueError("Provide exactly one of --lut or --directivity")

    path = lut_path or directivity_path
    assert path is not None
    if not path.exists():
        raise FileNotFoundError(path)

    data = _load_npz(path)

    if "k_hat" not in data:
        raise ValueError(f"{path} missing required array 'k_hat'")
    k_hat = np.asarray(data["k_hat"], dtype=float)
    if k_hat.ndim != 2 or k_hat.shape[1] != 3:
        raise ValueError(f"'k_hat' must have shape (N,3); got {k_hat.shape}")

    w = None
    for key in ("weights", "w", "omega_w"):
        if key in data:
            w = np.asarray(data[key], dtype=float).reshape(-1)
            break
    if w is not None and w.shape != (k_hat.shape[0],):
        raise ValueError(f"weights must have shape (N,); got {w.shape}")

    if directivity_path is not None:
        if "D" not in data:
            raise ValueError(f"{path} missing required array 'D' for --directivity")
        D = np.asarray(data["D"], dtype=float).reshape(-1)
        if D.shape != (k_hat.shape[0],):
            raise ValueError(f"'D' must have shape (N,); got {D.shape}")
        return k_hat, D, w

    # LUT path: compute D from A_perp
    if "A_perp" not in data:
        raise ValueError(f"{path} missing required array 'A_perp' for --lut")
    A_perp = np.asarray(data["A_perp"], dtype=float).reshape(-1)
    if A_perp.shape != (k_hat.shape[0],):
        raise ValueError(f"'A_perp' must have shape (N,); got {A_perp.shape}")
    A_mean = _weighted_mean(A_perp, w)
    if not np.isfinite(A_mean) or A_mean <= 0:
        raise ValueError(f"mean(A_perp) must be positive finite; got {A_mean}")
    D = A_perp / A_mean
    return k_hat, D, w


@dataclass(frozen=True)
class SpectrumCase:
    key: str
    label: str
    rho_raw: np.ndarray
    note: str


def _build_cases(k_hat: np.ndarray, args: argparse.Namespace) -> Dict[str, SpectrumCase]:
    kz = np.asarray(k_hat[:, 2], dtype=float)
    el = np.arcsin(np.clip(kz, -1.0, 1.0))  # elevation above horizon in [-pi/2, pi/2]

    # 1) Isotropic
    rho_iso = np.ones_like(kz)

    # 2) Upper hemisphere uniform
    rho_upper = (kz > 0).astype(float)

    # 3) Elevation-concentrated Gaussian
    el0 = np.deg2rad(args.elev0_deg)
    sigma = np.deg2rad(max(args.elev_sigma_deg, 1e-6))
    rho_elev = np.exp(-0.5 * ((el - el0) / sigma) ** 2)
    if args.elev_upper_only:
        rho_elev = rho_elev * (kz > 0)

    cases: Dict[str, SpectrumCase] = {
        "isotropic": SpectrumCase(
            key="isotropic",
            label="Isotropic (rho=1)",
            rho_raw=rho_iso,
            note="Sanity check: since mean(D)=1 by construction, isotropic gives F=1.",
        ),
        "upper": SpectrumCase(
            key="upper",
            label="Upper hemisphere (kz>0)",
            rho_raw=rho_upper,
            note="Differs from 1 because the body is not directionally symmetric (above vs below).",
        ),
        "elev": SpectrumCase(
            key="elev",
            label=f"Elevation Gaussian (mean={args.elev0_deg:.0f} deg, sigma={args.elev_sigma_deg:.0f} deg)",
            rho_raw=rho_elev,
            note="Toy base-station-like spectrum concentrated at a preferred elevation angle.",
        ),
    }

    if args.include_urban_ring:
        sigma_kz = max(args.urban_sigma_kz, 1e-6)
        rho_urban = np.exp(-0.5 * (kz / sigma_kz) ** 2)
        cases["urban"] = SpectrumCase(
            key="urban",
            label=f"Urban ring (kz~0, sigma_kz={args.urban_sigma_kz:.2f})",
            rho_raw=rho_urban,
            note="Toy urban-canyon spectrum concentrated near the horizontal plane.",
        )

    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Angular spectrum examples using D(k_hat).")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--lut", type=Path, help="Path to A_perp LUT .npz (expects k_hat and A_perp).")
    src.add_argument("--directivity", type=Path, help="Path to directivity .npz (expects k_hat and D).")

    parser.add_argument("--elev0-deg", dest="elev0_deg", type=float, default=15.0)
    parser.add_argument("--elev-sigma-deg", dest="elev_sigma_deg", type=float, default=7.5)
    parser.add_argument("--elev-upper-only", action="store_true")

    parser.add_argument("--include-urban-ring", action="store_true")
    parser.add_argument("--urban-sigma-kz", type=float, default=0.15)

    parser.add_argument(
        "--outfig",
        type=Path,
        default=Path("figures") / "angular_spectrum_examples.png",
        help="Output figure path (default: figures/angular_spectrum_examples.png).",
    )

    args = parser.parse_args()

    try:
        k_hat, D, w = _load_directivity(lut_path=args.lut, directivity_path=args.directivity)
    except FileNotFoundError as e:
        p = Path(str(e))
        print(f"ERROR: input file not found: {p}")
        print("Tip: generate a LUT with `python scripts/compute_projected_area_table.py --stl data/thelonious.stl --n 4096`.")
        return 2

    D_mean = _weighted_mean(D, w)
    print(f"Loaded N={k_hat.shape[0]} directions")
    if args.lut is not None:
        print(f"Source LUT: {args.lut}")
    if args.directivity is not None:
        print(f"Source directivity: {args.directivity}")
    print(f"mean(D) = {D_mean:.6f}  (should be ~1.0 by construction)")

    cases = _build_cases(k_hat, args)

    print("\nNormalization: integral rho dOmega = 4*pi  (discrete: weighted mean(rho)=1)")
    print("Compute F = (1/(4*pi)) * integral rho(k) D(k) dOmega  (discrete: weighted mean(rho*D))\n")

    rows = []
    for case in cases.values():
        rho = _normalize_rho(case.rho_raw, w)
        F = _weighted_mean(rho * D, w)
        rows.append((case.label, F, case.key, case.note))
        print(f"- {case.label}: F = {F:.6f}")
        if case.key == "upper":
            print(f"  Explanation: {case.note}")

    # Plot
    outfig: Path = args.outfig
    outfig.parent.mkdir(parents=True, exist_ok=True)

    labels = [r[0] for r in rows]
    Fs = np.array([r[1] for r in rows], dtype=float)

    plt.figure(figsize=(10, 5))
    x = np.arange(len(labels))
    bars = plt.bar(x, Fs, color="#377eb8", edgecolor="black", linewidth=0.7, alpha=0.85)
    plt.axhline(1.0, color="gray", linestyle="--", linewidth=1.5, label="Isotropic baseline (F=1)")
    plt.xticks(x, labels, rotation=20, ha="right")
    plt.ylabel("Normalized factor F")
    plt.title("Angular spectrum examples: F = (1/(4*pi)) * integral rho(k) D(k) dOmega")
    plt.grid(True, axis="y", alpha=0.25)

    for b in bars:
        h = b.get_height()
        plt.text(b.get_x() + b.get_width() / 2, h, f"{h:.3f}", ha="center", va="bottom", fontsize=10)

    plt.tight_layout()
    plt.savefig(outfig, dpi=150, bbox_inches="tight")
    print(f"\nSaved figure: {outfig}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

