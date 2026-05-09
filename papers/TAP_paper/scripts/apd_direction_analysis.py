"""
APD Direction and Polarization Analysis

Compute APD distribution on the Thelonious phantom for:
- Many incident wave directions
- Three polarization types: TE, TM, unpolarized

Using the elegant ReLU (positive-part) notation:
    APD(r) = S_inc * T_0 * [μ(r)]₊
    
where [μ]₊ = max(0, μ) and μ = n̂ · (-k̂) is the cosine of local incidence angle.

Generate publication-quality figures showing:
1. Total absorbed power vs direction
2. APD distribution histograms
3. Comparison of polarization effects

Author: PRL EMT Project
Date: 2026-02-06
"""

import scienceplots  # noqa: F401

import matplotlib
# Non-interactive backend (deliverable is the saved figure files).
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import argparse
from dataclasses import dataclass
from typing import Tuple, List
from pathlib import Path

# Shared helpers
from _fresnel import EPS_0, fresnel_transmission, n_complex as n_complex_from_params
from _geom import load_stl_binary, triangle_areas
from _plot_style import apply_monograph_style, fig_size_ieee

# Physical constants
C_0 = 299792458.0


@dataclass
class TissueParams:
    """Tissue electromagnetic properties."""
    name: str
    eps_r: float
    sigma: float
    freq_hz: float
    
    @property
    def n_complex(self) -> complex:
        return n_complex_from_params(self.eps_r, self.sigma, self.freq_hz)
    
    @property
    def T_0(self) -> float:
        n = self.n_complex
        r = (1 - n) / (1 + n)
        return float(1 - np.abs(r)**2)


def compute_apd_for_direction(normals: np.ndarray, areas: np.ndarray,
                               k_hat: np.ndarray, n_complex: complex,
                               polarization: str = 'unpolarized') -> Tuple[np.ndarray, float]:
    """
    Compute APD for a given incident direction and polarization.
    
    Returns APD array and total absorbed power.
    """
    # Compute cos(theta) = n_hat · (-k_hat)
    cos_theta = np.sum(normals * (-k_hat), axis=1)
    
    # Visibility: illuminated if cos_theta > 0
    illuminated = cos_theta > 0
    cos_theta = np.clip(cos_theta, 0, 1)
    
    # Compute Fresnel transmission
    T_s, T_p = fresnel_transmission(cos_theta, n_complex)
    
    if polarization == 'TE':
        T_eff = T_s
    elif polarization == 'TM':
        T_eff = T_p
    else:  # unpolarized
        T_eff = 0.5 * (T_s + T_p)
    
    # APD = S_inc * T_eff * cos(theta) * visibility
    # Assume S_inc = 1 W/m²
    apd = T_eff * cos_theta * illuminated.astype(float)
    
    # Total absorbed power
    P_abs = np.sum(apd * areas)
    
    return apd, P_abs


def generate_directions(n_theta: int = 10, n_phi: int = 20) -> np.ndarray:
    """Generate uniformly distributed directions on the sphere."""
    directions = []
    
    # Use Fibonacci sphere for more uniform distribution
    n_total = n_theta * n_phi
    golden_ratio = (1 + np.sqrt(5)) / 2
    
    for i in range(n_total):
        theta = np.arccos(1 - 2 * (i + 0.5) / n_total)
        phi = 2 * np.pi * i / golden_ratio
        
        k_hat = np.array([
            np.sin(theta) * np.cos(phi),
            np.sin(theta) * np.sin(phi),
            np.cos(theta)
        ])
        directions.append(k_hat)
    
    return np.array(directions)


def main(argv: List[str] | None = None):
    parser = argparse.ArgumentParser(description="APD direction/polarization analysis (Thelonious).")
    parser.add_argument(
        "--mode",
        type=str,
        choices=["png", "pdf"],
        default="png",
        help="Output mode: png uses science+no-latex; pdf uses science+latex.",
    )
    parser.add_argument(
        "--outdir",
        type=str,
        default=str(Path(__file__).parent.parent / "figures"),
        help="Directory to write output figures into.",
    )
    args = parser.parse_args(argv)
    pct = r"\%" if args.mode == "pdf" else "%"

    apply_monograph_style(mode=args.mode)

    # Load mesh
    mesh_paths = [
        Path(__file__).parent.parent / 'data' / 'thelonious.stl',
        Path(__file__).parent.parent.parent / 'data' / 'thelonious.stl',
        Path(__file__).parent.parent.parent.parent / 'data' / 'thelonious.stl',
        Path(__file__).parent / 'thelonious.stl',
    ]
    
    mesh_path = None
    for path in mesh_paths:
        try:
            with open(path, 'rb'):
                mesh_path = path
                break
        except FileNotFoundError:
            continue
    
    if mesh_path is None:
        print("ERROR: Could not find thelonious.stl mesh file")
        return
    
    print(f"Loading mesh: {mesh_path}")
    vertices, normals, centroids = load_stl_binary(mesh_path)
    areas = triangle_areas(vertices)
    n_triangles = len(centroids)
    total_area = np.sum(areas)
    print(f"  {n_triangles} triangles, {total_area*1e6:.1f} mm² total area")
    
    # Tissue parameters
    tissue = TissueParams('Skin 28 GHz', 17.0, 25.0, 28e9)
    n_complex = tissue.n_complex
    T_0 = tissue.T_0
    print(f"\nTissue: {tissue.name}")
    print(f"  n = {n_complex:.4f}, |n| = {np.abs(n_complex):.4f}")
    print(f"  T_0 = {T_0:.4f}")
    
    # Generate directions
    print("\nGenerating incident directions...")
    directions = generate_directions(n_theta=8, n_phi=16)
    n_directions = len(directions)
    print(f"  {n_directions} directions")
    
    # Compute APD for all directions and polarizations
    polarizations = ['TE', 'TM', 'unpolarized']
    
    results = {pol: {'P_abs': [], 'apd_max': [], 'apd_mean': [], 'apd_all': []} 
               for pol in polarizations}
    
    print("\nComputing APD for all directions and polarizations...")
    for i, k_hat in enumerate(directions):
        for pol in polarizations:
            apd, P_abs = compute_apd_for_direction(normals, areas, k_hat, n_complex, pol)
            
            illuminated = apd > 0
            if np.any(illuminated):
                results[pol]['P_abs'].append(P_abs)
                results[pol]['apd_max'].append(np.max(apd))
                results[pol]['apd_mean'].append(np.mean(apd[illuminated]))
                results[pol]['apd_all'].extend(apd[illuminated].tolist())
    
    # Convert to arrays
    for pol in polarizations:
        for key in ['P_abs', 'apd_max', 'apd_mean']:
            results[pol][key] = np.array(results[pol][key])
        results[pol]['apd_all'] = np.array(results[pol]['apd_all'])
    
    # Print statistics
    print("\n" + "="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    
    for pol in polarizations:
        P = results[pol]['P_abs']
        print(f"\n{pol.upper()}:")
        print(f"  Total absorbed power: mean={P.mean()*1e3:.2f} mW, "
              f"std={P.std()*1e3:.2f} mW, range=[{P.min()*1e3:.2f}, {P.max()*1e3:.2f}] mW")
        print(f"  Max APD: mean={results[pol]['apd_max'].mean():.4f} W/m²")
        print(f"  Mean APD (illuminated): mean={results[pol]['apd_mean'].mean():.4f} W/m²")

    # Per-direction simplified prediction P_simp(k_hat) = T_0 * sum(area * [mu]_+),
    # and the bias of P_simp relative to the unpolarized full-Fresnel integral.
    P_simp_per_dir = []
    for k_hat in directions:
        cos_theta = np.maximum(0, np.sum(normals * (-k_hat), axis=1))
        P_simp_per_dir.append(T_0 * np.sum(areas * cos_theta))
    P_simp = np.array(P_simp_per_dir)
    bias = P_simp / results['unpolarized']['P_abs'] - 1
    print(f"\nDirection-averaged bias (P_simp / P_full_unp - 1) across {len(directions)} directions:")
    print(f"  mean = {bias.mean()*100:+.2f}%, std = {bias.std()*100:.2f}%, "
          f"range = [{bias.min()*100:+.2f}%, {bias.max()*100:+.2f}%]")

    # Create figures
    print("\nGenerating figures...")

    # Two separate single-panel figures so each can be a LaTeX subfigure.
    fig_b, ax_b = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.78))
    fig_c, ax_c = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.78))

    # Okabe-Ito color-blind-safe palette. Pair each polarization with a
    # distinguishing line shape so panels remain readable in greyscale.
    colors = {'TE': '#0072B2', 'TM': '#D55E00', 'unpolarized': '#000000'}
    # Use explicit dash patterns so the third line stays visible even at print
    # resolutions where pyplot's ":" can render too thin.
    linestyles = {'TE': '-', 'TM': (0, (5, 2)), 'unpolarized': (0, (1.5, 1.5))}
    pol_labels = {'TE': 'TE', 'TM': 'TM', 'unpolarized': 'unpolarized'}
    box_labels = [pol_labels[p] for p in polarizations]

    def _frame_legend(ax, **kwargs):
        leg = ax.legend(frameon=True, fancybox=False, edgecolor='black',
                        framealpha=1.0, **kwargs)
        leg.get_frame().set_linewidth(1.0)
        return leg

    # Panel: Local APD probability density over illuminated triangles.
    bins = np.linspace(0, 0.6, 40)
    for pol in polarizations:
        ax_b.hist(
            results[pol]['apd_all'], bins=bins,
            histtype='step', linewidth=1.4,
            color=colors[pol], linestyle=linestyles[pol],
            density=True, label=pol_labels[pol],
        )
    ax_b.set_xlabel(r'$\mathrm{APD}$ [W/m$^2$]')
    ax_b.set_ylabel(r'Probability density [m$^2$/W]')
    ax_b.set_xlim(0, 0.6)
    _y0, _y1 = ax_b.get_ylim()
    ax_b.set_ylim(0, _y1 * 1.10)
    _frame_legend(ax_b, loc='upper right')

    # Panel: Box plot of total power by polarization with CV annotations.
    data = [results[pol]['P_abs'] * 1e3 for pol in polarizations]
    bp = ax_c.boxplot(
        data, tick_labels=box_labels, patch_artist=False,
        widths=0.55, showfliers=True,
        medianprops=dict(color='black', linewidth=1.2),
        flierprops=dict(marker='o', markersize=3.5, markerfacecolor='none',
                        markeredgecolor='0.3', linewidth=0.6),
        whiskerprops=dict(linewidth=0.9, color='0.2'),
        capprops=dict(linewidth=0.9, color='0.2'),
    )
    for patch, pol in zip(bp['boxes'], polarizations):
        patch.set_color(colors[pol])
        patch.set_linewidth(1.2)
    ax_c.set_ylabel(r'$P_{\mathrm{abs}}$ [mW]')
    ax_c.set_xlabel(r'Polarization')
    ax_c.grid(True, alpha=0.25, axis='y')

    # Theory line: P_abs = S_inc T_0 A_perp; sphere-averaged A_perp = A_total/4.
    A_perp_avg = total_area / 4
    P_theory = T_0 * A_perp_avg * 1e3
    ax_c.axhline(
        P_theory, color='0.35', linestyle='--', linewidth=1.0,
        label=rf'$T_0 A_\perp = {P_theory:.1f}$ mW',
    )

    # Annotate CV (coefficient of variation) above each box.
    cv_P = {pol: results[pol]['P_abs'].std() / results[pol]['P_abs'].mean() * 100
            for pol in polarizations}
    ymax = max(d.max() for d in data)
    for i, pol in enumerate(polarizations, start=1):
        ax_c.text(i, ymax * 1.06, rf'CV {cv_P[pol]:.1f}{pct}',
                  ha='center', va='bottom', fontsize=8,
                  color=colors[pol])
    ax_c.set_ylim(0, ymax * 1.18)
    _frame_legend(ax_c, loc='lower right')

    output_dir = Path(args.outdir)
    output_dir.mkdir(exist_ok=True)
    ext = ".png" if args.mode == "png" else ".pdf"
    p_b = output_dir / f"apd_direction_panel_pdf{ext}"
    p_c = output_dir / f"apd_direction_panel_box{ext}"
    save_kw = dict(dpi=250, bbox_inches='tight') if args.mode == 'png' else dict(bbox_inches='tight')
    fig_b.tight_layout(pad=0.4)
    fig_c.tight_layout(pad=0.4)
    fig_b.savefig(p_b, **save_kw)
    fig_c.savefig(p_c, **save_kw)
    plt.close(fig_b)
    plt.close(fig_c)
    print(f"  Saved: {p_b}")
    print(f"  Saved: {p_c}")
    
    # Companion figures: APD vs incidence angle.
    # Two separate panels for LaTeX subfigure layout.
    fig_T, ax5 = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.78))
    fig_Sab, ax6 = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.78))

    # Colour-blind-safe palette with line-shape redundancy (rules 4, 6).
    c_TE = "#0072B2"   # blue
    c_TM = "#D55E00"   # vermilion
    c_avg = "#000000"  # black
    c_ref = "#7F7F7F"  # neutral gray for T_0 references

    # Theoretical curves
    theta_deg = np.linspace(0, 85, 400)
    mu = np.cos(np.radians(theta_deg))
    T_s, T_p = fresnel_transmission(mu, n_complex)
    T_avg = 0.5 * (T_s + T_p)

    # Plot order chosen so T_avg sits visually on top of T_0 reference.
    ax5.axhline(T_0, color=c_ref, linestyle=":", linewidth=1.0)
    ax5.plot(theta_deg, T_s, "-", color=c_TE, linewidth=1.6, label=r"$T_s$ (TE)")
    ax5.plot(theta_deg, T_p, "--", color=c_TM, linewidth=1.6, label=r"$T_p$ (TM)")
    ax5.plot(
        theta_deg, T_avg, "-.", color=c_avg, linewidth=1.4,
        label=r"$T_{\mathrm{avg}}$",
    )
    ax5.set_xlabel(r"Incidence angle $\theta$ [deg]")
    ax5.set_ylabel(r"Transmission $T(\theta)$")
    ax5.set_xlim(0, 85)
    ax5.set_ylim(0, 1.05)
    ax5.set_xticks([0, 15, 30, 45, 60, 75])
    ax5.set_yticks([0.0, 0.25, 0.5, 0.75, 1.0])

    # In-panel label for the T_0 reference (no legend entry, no overlap).
    ax5.text(
        2, T_0 - 0.06, rf"$T_0 = {T_0:.3f}$",
        fontsize=8.0, color="black", va="top", ha="left",
    )

    # Annotation: pseudo-Brewster peak (rule 22). Placed just above the
    # T_p maximum to avoid overlap with the descending T_s curve.
    # circa:b1cd21c1-256d-4234-bdc0-f5b6cdf82742 -- relabeled to
    # "Pseudo-Brewster angle" and shifted further left to clear the arrow.
    i_peak = int(np.argmax(T_p))
    ax5.annotate(
        "Pseudo-Brewster angle",
        xy=(theta_deg[i_peak], T_p[i_peak]),
        xytext=(theta_deg[i_peak] - 38, 1.00),
        fontsize=8.0,
        ha="center",
        va="center",
        arrowprops=dict(
            arrowstyle="->", color="black", lw=0.6,
            shrinkA=2.0, shrinkB=2.0,
            connectionstyle="arc3,rad=-0.2",
        ),
    )

    # Add legend to upper panel (Transmission vs angle).
    leg5 = ax5.legend(loc="lower left", frameon=True, fancybox=False,
                      edgecolor="black", framealpha=1.0,
                      handlelength=2.0, handletextpad=0.4,
                      borderpad=0.3, fontsize=8)
    leg5.get_frame().set_linewidth(1.0)

    # Second figure: APD = T * cos(theta)
    apd_s = T_s * mu
    apd_p = T_p * mu
    apd_avg = T_avg * mu
    apd_simple = T_0 * mu

    ax6.plot(
        theta_deg, apd_simple, ":", color=c_ref, linewidth=1.2,
        label=r"$T_0\cos\theta$",
    )
    ax6.plot(theta_deg, apd_s, "-", color=c_TE, linewidth=1.6, label=r"$T_s\cos\theta$ (TE)")
    ax6.plot(theta_deg, apd_p, "--", color=c_TM, linewidth=1.6, label=r"$T_p\cos\theta$ (TM)")
    ax6.plot(theta_deg, apd_avg, "-.", color=c_avg, linewidth=1.4, label=r"$T_{\mathrm{avg}}\cos\theta$")
    ax6.set_xlabel(r"Incidence angle $\theta$ [deg]")
    ax6.set_ylabel(r"$\mathrm{APD}/\mathrm{IPD}$")
    ax6.set_xlim(0, 85)
    ax6.set_ylim(0, 0.62)
    ax6.set_xticks([0, 15, 30, 45, 60, 75])
    ax6.set_yticks([0.0, 0.2, 0.4, 0.6])
    # Identify the simplified reference curve in-panel; the polarization
    # styles are keyed by the shared legend below the figure. The dotted
    # grey curve is placed in the empty lower-right region.
    ax6.annotate(
        r"$T_0\cos\theta$",
        xy=(70, T_0 * np.cos(np.radians(70))),
        xytext=(55, 0.07),
        fontsize=8.0, color="black", ha="center", va="center",
        arrowprops=dict(
            arrowstyle="->", color="black", lw=0.5,
            shrinkA=1.0, shrinkB=2.0,
            connectionstyle="arc3,rad=-0.2",
        ),
    )

    # Save the two angle-dependence panels separately for LaTeX subfigure layout.
    fig_T.tight_layout(pad=0.4)
    fig_Sab.tight_layout(pad=0.4)
    p_T = output_dir / f"apd_angle_panel_T{ext}"
    p_Sab = output_dir / f"apd_angle_panel_APD{ext}"
    fig_T.savefig(p_T, **save_kw)
    fig_Sab.savefig(p_Sab, **save_kw)
    plt.close(fig_T)
    plt.close(fig_Sab)
    print(f"  Saved: {p_T}")
    print(f"  Saved: {p_Sab}")
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)
    
    # Print key findings
    print("\nKEY FINDINGS:")
    print(f"1. Unpolarized light: Total power varies by only {cv_P['unpolarized']:.1f}% across directions")
    print(f"2. TE polarized: Total power varies by {cv_P['TE']:.1f}% across directions")
    print(f"3. TM polarized: Total power varies by {cv_P['TM']:.1f}% across directions")
    print(f"4. The simplified formula APD = T0*cos(theta) is accurate for unpolarized light")
    print(f"5. For polarized sources, use full Fresnel formula")


if __name__ == '__main__':
    main()
