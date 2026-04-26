"""Compare AEGIS surface absorption (Sab map) against FDTD-derived per-triangle
SAPD on the same skin mesh. Produces NRMSE, peak ratio, integrated power
ratio, and 3D-painted error map.

The comparison is the Tier 1+ headline: not "do peaks agree" but "are AEGIS
and FDTD pointing to the same patches of skin as the most-illuminated, with
matching magnitudes, integrated to the same total absorbed power".

Inputs (NumPy arrays of length M = n_triangles, both on the same skin mesh):
  s_aegis : Sab from AEGIS at Sinc=1 W/m² incident, in W/m²
  s_fdtd  : SAPD from FDTD (post-renorm to Sinc=1 W/m²), in W/m²
  areas   : per-triangle areas, in m²

Metrics returned (dict):
  'nrmse'              : sqrt(<(d)²>_A) / <s_fdtd>_A
  'corr'               : Pearson correlation, area-weighted
  'peak_ratio_4cm2'    : peak_aegis_4cm2 / peak_fdtd_4cm2 (ICNIRP averaged)
  'integrated_ratio'   : ∫ s_aegis dA / ∫ s_fdtd dA
  'rmse_w_m2'          : RMSE in absolute W/m² (un-normalised)
  'r2'                 : R² of regression aegis ~ fdtd (area-weighted)

Plots (optional):
  paint_error(body, ratio) → 3D phantom coloured by ratio AEGIS / FDTD
  scatter_plot(s_aegis, s_fdtd) → log-log scatter

Usage from a notebook or driver script:
    from surface_apd_compare import compare, paint_error
    metrics = compare(s_aegis, s_fdtd, areas)
    paint_error(body, s_aegis / s_fdtd, "aegis_over_fdtd_5p8GHz_xpos.png")
"""

from __future__ import annotations
from typing import Optional
import numpy as np


def _area_weighted_mean(x: np.ndarray, areas: np.ndarray) -> float:
    return float(np.sum(x * areas) / np.sum(areas))


def _peak_4cm2(s: np.ndarray, body, area_target_cm2: float = 4.0) -> float:
    """Approximation of ICNIRP-style spatial averaging on a triangulated
    surface: for each triangle, average s within an expanding ring of
    geodesic neighbours until the ring area exceeds `area_target_cm2`.
    Return the peak of these averages.

    For a true triangulated APD comparison this is what should be reported,
    not the raw per-triangle peak (which depends on mesh resolution).
    """
    target_m2 = area_target_cm2 * 1e-4
    centroids = body.centroids
    areas = body.areas

    # For each triangle, find neighbours within radius √(target_m2/π).
    # Use a single-pass kNN in centroid coordinates.
    R = np.sqrt(target_m2 / np.pi) * 1.5  # over-estimate so we always cover area
    from scipy.spatial import cKDTree

    tree = cKDTree(centroids)

    M = len(s)
    s_avg = np.zeros(M)
    for i in range(M):
        idx = tree.query_ball_point(centroids[i], R)
        if not idx:
            s_avg[i] = s[i]
            continue
        d = np.linalg.norm(centroids[idx] - centroids[i], axis=1)
        order = np.argsort(d)
        idx = np.array(idx)[order]
        cum = np.cumsum(areas[idx])
        cutoff = np.searchsorted(cum, target_m2)
        cutoff = max(cutoff, 1)
        sel = idx[: cutoff + 1]
        s_avg[i] = np.sum(s[sel] * areas[sel]) / max(np.sum(areas[sel]), 1e-30)
    return float(np.max(s_avg))


def compare(s_aegis: np.ndarray, s_fdtd: np.ndarray, areas: np.ndarray, *, body=None) -> dict:
    """Compute NRMSE, peak ratio, integrated ratio, and other comparison
    metrics between AEGIS and FDTD surface power densities on the same
    triangulated skin mesh.

    `body` is optional; required only for the 4-cm² peak metric.
    """
    s_aegis = np.asarray(s_aegis, dtype=np.float64)
    s_fdtd = np.asarray(s_fdtd, dtype=np.float64)
    areas = np.asarray(areas, dtype=np.float64)
    if not (s_aegis.shape == s_fdtd.shape == areas.shape):
        raise ValueError(f"shape mismatch: aegis={s_aegis.shape}, fdtd={s_fdtd.shape}, areas={areas.shape}")

    # Area-weighted means and RMSE
    diff = s_aegis - s_fdtd
    mean_fdtd = _area_weighted_mean(s_fdtd, areas)
    rmse = np.sqrt(_area_weighted_mean(diff**2, areas))
    nrmse = rmse / max(mean_fdtd, 1e-30)

    # Pearson correlation (area-weighted)
    a = s_aegis - _area_weighted_mean(s_aegis, areas)
    f = s_fdtd - mean_fdtd
    num = _area_weighted_mean(a * f, areas)
    den = np.sqrt(_area_weighted_mean(a**2, areas)) * np.sqrt(_area_weighted_mean(f**2, areas)) + 1e-30
    corr = num / den

    # R² from linear regression aegis ~ slope * fdtd  (area-weighted, no
    # intercept — treats the analytical relationship as y = αx)
    slope = _area_weighted_mean(s_aegis * s_fdtd, areas) / max(_area_weighted_mean(s_fdtd**2, areas), 1e-30)
    pred = slope * s_fdtd
    ss_res = _area_weighted_mean((s_aegis - pred) ** 2, areas)
    ss_tot = _area_weighted_mean((s_aegis - _area_weighted_mean(s_aegis, areas)) ** 2, areas)
    r2 = 1 - ss_res / max(ss_tot, 1e-30)

    integrated_aegis = float(np.sum(s_aegis * areas))
    integrated_fdtd = float(np.sum(s_fdtd * areas))
    integrated_ratio = integrated_aegis / max(integrated_fdtd, 1e-30)

    out = {
        "nrmse": float(nrmse),
        "rmse_w_m2": float(rmse),
        "corr": float(corr),
        "r2": float(r2),
        "slope": float(slope),
        "integrated_aegis_W": integrated_aegis,
        "integrated_fdtd_W": integrated_fdtd,
        "integrated_ratio": float(integrated_ratio),
        "mean_fdtd_w_m2": mean_fdtd,
        "mean_aegis_w_m2": float(_area_weighted_mean(s_aegis, areas)),
    }
    if body is not None:
        out["peak_aegis_4cm2_w_m2"] = _peak_4cm2(s_aegis, body)
        out["peak_fdtd_4cm2_w_m2"] = _peak_4cm2(s_fdtd, body)
        out["peak_ratio_4cm2"] = out["peak_aegis_4cm2_w_m2"] / max(out["peak_fdtd_4cm2_w_m2"], 1e-30)
        out["peak_aegis_raw"] = float(np.max(s_aegis))
        out["peak_fdtd_raw"] = float(np.max(s_fdtd))
        out["peak_ratio_raw"] = out["peak_aegis_raw"] / max(out["peak_fdtd_raw"], 1e-30)
    return out


def paint_error(
    body,
    scalar: np.ndarray,
    out_path: str,
    *,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    cmap: str = "RdBu_r",
    title: str = "",
    elev: float = 15,
    azim: float = -60,
    log_scale: bool = False,
) -> None:
    """3D phantom map painted by a per-triangle scalar (e.g. AEGIS/FDTD ratio)."""
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    tris = body.vertices.reshape(-1, 3, 3)
    fig = plt.figure(figsize=(7.5, 9))
    ax = fig.add_subplot(111, projection="3d")
    if log_scale:
        scalar = np.log10(np.maximum(scalar, 1e-30))
    norm = plt.Normalize(
        vmin=vmin if vmin is not None else float(np.percentile(scalar, 2)),
        vmax=vmax if vmax is not None else float(np.percentile(scalar, 98)),
    )
    facecolors = cm.get_cmap(cmap)(norm(scalar))
    poly = Poly3DCollection(tris, facecolors=facecolors, edgecolors="none", linewidths=0)
    ax.add_collection3d(poly)
    v = body.vertices.reshape(-1, 3)
    ax.set_xlim(v[:, 0].min(), v[:, 0].max())
    ax.set_ylim(v[:, 1].min(), v[:, 1].max())
    ax.set_zlim(v[:, 2].min(), v[:, 2].max())
    try:
        ax.set_box_aspect(np.ptp(v, axis=0))
    except AttributeError:
        pass
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title)
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, shrink=0.6, fraction=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def scatter_plot(s_aegis: np.ndarray, s_fdtd: np.ndarray, areas: np.ndarray, out_path: str, *, title: str = "") -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.scatter(s_fdtd, s_aegis, s=3 * 1e6 * areas, alpha=0.4, c=np.log10(np.maximum(areas * 1e6, 1e-3)), cmap="viridis")
    lo = max(min(s_aegis.min(), s_fdtd.min()), 1e-6)
    hi = max(s_aegis.max(), s_fdtd.max())
    ax.plot([lo, hi], [lo, hi], "k--", lw=1, label="1:1")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("FDTD SAPD [W/m²]")
    ax.set_ylabel("AEGIS Sab [W/m²]")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _self_test():
    """Sanity check the metric definitions against analytical cases."""
    rng = np.random.default_rng(0)

    # Case 1: identical fields → NRMSE=0, ratio=1, R²=1
    s = rng.uniform(0, 5, size=2000)
    a = rng.uniform(0, 0.01, size=2000)
    m = compare(s, s, a)
    assert abs(m["nrmse"]) < 1e-12, m
    assert abs(m["integrated_ratio"] - 1) < 1e-12, m
    assert m["r2"] > 0.999, m

    # Case 2: aegis = 1.2 × fdtd → integrated_ratio=1.2, r2=1, slope=1.2.
    # NRMSE = sqrt(<(0.2 s)²>) / <s> = 0.2 RMS(s) / mean(s) (≠ 0.2 unless s is constant).
    m = compare(1.2 * s, s, a)
    assert abs(m["integrated_ratio"] - 1.2) < 1e-9, m
    assert abs(m["slope"] - 1.2) < 1e-9, m
    assert m["r2"] > 0.999, m
    expected_nrmse = 0.2 * np.sqrt(np.mean(s**2)) / np.mean(s)
    assert abs(m["nrmse"] - expected_nrmse) < 0.05, (m, expected_nrmse)

    # Case 3: aegis = fdtd + N(0, σ); NRMSE ≈ σ / mean
    sigma = 0.3 * s.mean()
    noise = rng.normal(0, sigma, size=s.shape)
    m = compare(s + noise, s, a)
    expected = sigma / s.mean()
    assert abs(m["nrmse"] - expected) / expected < 0.10, (m, expected)

    print("[surface_apd_compare self-test] PASS")


if __name__ == "__main__":
    _self_test()
