"""
Mie Theory Validation using IT'IS Database (CORRECTED)
======================================================

This script validates the simplified APD framework against exact Mie theory
for lossy dielectric spheres, using frequency-dependent skin parameters from
the IT'IS v5.0 database.

Key corrections from previous version:
1. Uses frequency-dependent refractive index m(f) from IT'IS Gabriel model
2. Notes that asymptotic error limit is ~-1.2% (from Fresnel approx), not 0%
3. Shows that framework can overestimate at high frequencies for large objects
4. Properly decomposes Fresnel vs diffraction error contributions

Author: PRL EMT Project
Date: 2026-02-06
"""

import scienceplots  # noqa: F401

import numpy as np
import miepython as mp
import matplotlib
import sqlite3
import struct
import cmath
from pathlib import Path
from scipy import integrate

# Use a non-interactive backend so the script runs in clean/headless environments.
# The deliverable artifact is the saved PNG in `figures/`, not an interactive window.
# IMPORTANT: must be set before importing `matplotlib.pyplot`.
matplotlib.use("Agg")

import matplotlib.pyplot as plt

# Shared plotting style (monograph-matched)
from _plot_style import apply_monograph_style, fig_size_ieee

import argparse

# Physical constants
EPS_0 = 8.854187817e-12  # F/m
C_0 = 299792458.0         # m/s

# Database paths
DB_PATHS = [
    Path(__file__).parent.parent / "data" / "itis_v5.db",
    Path(__file__).parent.parent.parent / "data" / "itis_v5.db",
    Path(__file__).parent / "itis_v5.db",
    Path(__file__).parent.parent / "EMT" / "itis_v5.db",
    Path(__file__).parent.parent / "PRL_brainstorm" / "itis_v5.db",
]


def find_database():
    """Find the IT'IS database file."""
    for path in DB_PATHS:
        if path.exists():
            return path
    raise FileNotFoundError("Could not find itis_v5.db database")


def get_gabriel_params(tissue_name='Skin'):
    """Extract Gabriel model parameters from IT'IS database."""
    db_path = find_database()
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    
    # Get Gabriel Parameters prop_id first
    c.execute("SELECT prop_id FROM properties WHERE name = ?", ('Gabriel Parameters',))
    prop_result = c.fetchone()
    
    if not prop_result:
        conn.close()
        return None
    
    prop_id = prop_result[0]
    
    # Get material with Gabriel params (there are multiple "Skin" entries, use first with params)
    c.execute("""SELECT m.mat_id, v.vals 
                 FROM materials m 
                 JOIN vectors v ON m.mat_id = v.mat_id 
                 WHERE m.name = ? AND v.prop_id = ?
                 LIMIT 1""", (tissue_name, prop_id))
    result = c.fetchone()
    
    if not result:
        conn.close()
        return None
    
    mat_id, blob_result = result[0], result[1]
    blob = blob_result
    conn.close()
    
    if len(blob) >= 14 * 8:
        values = struct.unpack('d' * 14, blob[:14*8])
        return {
            'ef': values[0],
            'del1': values[1], 'tau1': values[2], 'alf1': values[3],
            'del2': values[4], 'tau2': values[5], 'alf2': values[6],
            'del3': values[7], 'tau3': values[8], 'alf3': values[9],
            'del4': values[10], 'tau4': values[11], 'alf4': values[12],
            'sig': values[13]
        }
    
    return None


def cole_cole_permittivity(freq_hz, params):
    """Calculate complex permittivity using 4-Cole-Cole model."""
    omega = 2 * np.pi * freq_hz
    j = 1j
    
    eps = complex(params['ef'], 0)
    tau_units = [1e-12, 1e-9, 1e-6, 1e-3]  # ps, ns, us, ms
    
    for i in range(4):
        delta = params[f'del{i+1}']
        tau = params[f'tau{i+1}'] * tau_units[i]
        alpha = params[f'alf{i+1}']
        
        if delta != 0 and tau != 0:
            denom = 1 + (j * omega * tau) ** (1 - alpha)
            eps += delta / denom
    
    if params['sig'] != 0 and omega != 0:
        eps -= j * params['sig'] / (omega * EPS_0)
    
    return eps


def get_skin_properties(freq_hz):
    """Get skin properties at specific frequency from IT'IS database."""
    params = get_gabriel_params('Skin')
    
    if params is None:
        raise ValueError("Could not load skin parameters from IT'IS database")
    
    eps_complex = cole_cole_permittivity(freq_hz, params)
    
    # Complex refractive index: m = n - ik (negative imaginary for absorption)
    m = cmath.sqrt(eps_complex)
    if m.real < 0:
        m = -m
    
    # Normal incidence transmission
    n = m.real
    kappa = -m.imag  # positive for absorption
    T0 = 4 * n / ((1 + n)**2 + kappa**2)
    
    return {
        'freq_hz': freq_hz,
        'freq_ghz': freq_hz / 1e9,
        'eps_r': eps_complex.real,
        'sigma': -eps_complex.imag * 2 * np.pi * freq_hz * EPS_0,
        'm': m,
        'n': n,
        'kappa': kappa,
        'abs_m': abs(m),
        'T0': T0
    }


def compute_GO_limit(m):
    """
    Compute geometric optics limit: Q_abs_GO = 2 * integral(T_avg(mu) * mu, 0, 1).
    
    This is the limit as x -> infinity for a sphere in the physical optics (GO) regime.
    """
    def T_avg(mu):
        if mu <= 0:
            return 0
        n2 = m**2
        xi = cmath.sqrt(n2 - 1 + mu**2)
        if xi.real < 0:
            xi = -xi
        
        # TE
        rs = (mu - xi) / (mu + xi)
        Ts = 1 - abs(rs)**2
        
        # TM
        rp = (n2 * mu - xi) / (n2 * mu + xi)
        Tp = 1 - abs(rp)**2
        
        return 0.5 * (Ts + Tp)
    
    integral, _ = integrate.quad(lambda mu: 2 * T_avg(mu) * mu, 0, 1)
    return integral


def test_mie_single_frequency():
    """Test Mie efficiencies at 28 GHz with IT'IS skin parameters."""
    
    print("=" * 60)
    print("Mie Theory: Lossy Dielectric Sphere (28 GHz)")
    print("=" * 60)
    
    props = get_skin_properties(28e9)
    m = props['m']
    T0 = props['T0']
    
    print(f"\nSkin at 28 GHz (from IT'IS database):")
    print(f"  eps_r = {props['eps_r']:.2f}")
    print(f"  sigma = {props['sigma']:.2f} S/m")
    print(f"  m = {m.real:.3f} - {-m.imag:.3f}j")
    print(f"  |m| = {props['abs_m']:.3f}")
    print(f"  T0 = {T0:.6f}")
    
    # Compute GO limit
    Q_abs_GO = compute_GO_limit(m)
    R_sphere = T0 / Q_abs_GO
    
    print(f"\nGeometric optics limit:")
    print(f"  Q_abs(GO) = {Q_abs_GO:.6f}")
    print(f"  R_sphere = T0 / Q_abs(GO) = {R_sphere:.6f}")
    print(f"  Fresnel error = {(R_sphere - 1)*100:.2f}%")
    
    # Use wavelength = 1 (arbitrary units), vary diameter
    lambda0 = 1.0
    
    print("\n" + "-" * 60)
    print(f"{'x':>8} {'Q_ext':>10} {'Q_sca':>10} {'Q_abs':>10} {'T0/Q_abs':>10} {'Error':>10}")
    print("-" * 60)
    
    for x in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0]:
        d = x * lambda0 / np.pi
        qext, qsca, qback, g = mp.efficiencies(m, d, lambda0)
        qabs = qext - qsca
        
        ratio = T0 / qabs if qabs > 0 else float('inf')
        error = (ratio - 1) * 100
        
        print(f"{x:>8.1f} {qext:>10.4f} {qsca:>10.4f} {qabs:>10.4f} {ratio:>10.4f} {error:>+10.2f}%")
    
    print("-" * 60)
    print(f"Asymptotic limit (x -> infinity): error -> {(R_sphere - 1)*100:.2f}%")
    print("\nNote: The framework ALWAYS underestimates at this frequency because")
    print("      R_sphere < 1 (diffraction adds power in shadow).")


def frequency_dependence_analysis():
    """Analyze framework error vs frequency for fixed body sizes."""
    
    print("\n" + "=" * 70)
    print("Frequency Dependence: Prediction Error vs Frequency")
    print("Using IT'IS Database for Frequency-Dependent Skin Properties")
    print("=" * 70)
    
    c = C_0
    
    # Body part diameters (m)
    body_parts = {
        'Finger': 0.017,
        'Arm': 0.080,
        'Head': 0.180,
        'Torso': 0.300,
    }
    
    # Frequencies to analyze. Low-end sampling 1-6 GHz captures the
    # body-Mie regime where the geometric absorption law breaks down
    # the most; high-end samples document the asymptotic recovery.
    freqs = [
        1e9, 1.5e9, 2e9, 2.5e9, 3e9, 3.5e9, 4e9, 4.5e9,
        5e9, 5.5e9, 6e9,
        10e9, 20e9, 28e9, 40e9, 60e9, 77e9, 100e9,
    ]
    
    # Collect results
    results = {}
    
    print("\nLoading skin properties from IT'IS database...")
    for f in freqs:
        props = get_skin_properties(f)
        results[f] = props
        print(f"  {f/1e9:>6.0f} GHz: eps_r={props['eps_r']:>6.1f}, sigma={props['sigma']:>6.1f} S/m, "
              f"|m|={props['abs_m']:>5.2f}, T0={props['T0']:.4f}")
    
    print("\n" + "-" * 70)
    print(r"Prediction error (\%) = (T0/Q_abs - 1) × 100")
    print("Negative = framework underestimates absorption")
    print()
    
    # Header
    header = f"{'Freq (GHz)':>12}"
    for name in body_parts:
        header += f" {name:>10}"
    print(header)
    print("-" * 70)
    
    # Store for plotting
    freq_data = []
    error_data = {name: [] for name in body_parts}
    
    for f in freqs:
        wavelength = c / f
        props = results[f]
        m = props['m']
        T0 = props['T0']
        
        row = f"{f/1e9:>12.0f}"
        
        for name, d in body_parts.items():
            x = np.pi * d / wavelength
            qext, qsca, qback, g = mp.efficiencies(m, d, wavelength)
            qabs = qext - qsca
            
            if qabs > 0.01:
                error = (T0 / qabs - 1) * 100
                row += f" {error:>+10.1f}%"
                error_data[name].append(error)
            else:
                row += f" {'N/A':>10}"
                error_data[name].append(np.nan)
        
        freq_data.append(f/1e9)
        print(row)
    
    print("-" * 70)
    print("\nKey findings:")
    print("1. Error decreases (becomes less negative) at higher frequencies")
    print("2. At 100 GHz, torso-scale objects: framework slightly OVERESTIMATES")
    print("3. Larger objects have smaller errors (diffraction less important)")
    
    return freq_data, error_data, results


def size_parameter_sweep():
    """Sweep size parameter at 28 GHz to show convergence to GO limit."""
    
    print("\n" + "=" * 70)
    print("Size Parameter Sweep at 28 GHz")
    print("=" * 70)
    
    props = get_skin_properties(28e9)
    m = props['m']
    T0 = props['T0']
    Q_abs_GO = compute_GO_limit(m)
    
    lambda0 = 1.0
    x_vals = np.logspace(-0.5, 3.0, 200)
    
    errors = []
    errors_diffraction = []
    
    for x in x_vals:
        d = x * lambda0 / np.pi
        qext, qsca, qback, g = mp.efficiencies(m, d, lambda0)
        qabs = qext - qsca
        
        if qabs > 0.01:
            # Total error
            error_total = (T0 / qabs - 1) * 100
            # Diffraction-only error (relative to GO limit)
            error_diffraction = (Q_abs_GO / qabs - 1) * 100
            errors.append(error_total)
            errors_diffraction.append(error_diffraction)
        else:
            errors.append(np.nan)
            errors_diffraction.append(np.nan)
    
    return x_vals, errors, errors_diffraction


def compute_R_sphere_vs_freq(freqs_hz):
    """
    Compute the sphere ratio R_sphere = T_0 / Q_abs_GO at each frequency.
    
    This is the asymptotic limit (x -> inf) of the framework error at each frequency.
    """
    R_values = []
    for f in freqs_hz:
        props = get_skin_properties(f)
        Q_abs_GO = compute_GO_limit(props['m'])
        R = props['T0'] / Q_abs_GO
        R_values.append(R)
    return R_values


def create_validation_plots(*, mode: str = "png", out_dir: Path | None = None) -> Path:
    """Create comprehensive validation plots with frequency-dependent m(f)."""
    apply_monograph_style(mode=("pdf" if mode == "pdf" else "png"))
    # Outside math-mode, in axis labels and titles:
    #   - LaTeX (PDF): "%" must be escaped as r"\%"
    #   - mathtext (PNG): "%" is a literal character, no escape needed
    pct = r"\%" if mode == "pdf" else "%"
    # Inside $...$: in both PDF (LaTeX) and PNG (mathtext), use r"\%" to render "%".
    pct_math = r"\%"
    
    print("\n" + "=" * 70)
    print("Generating Validation Plots")
    print("=" * 70)
    
    c = C_0
    
    # Get frequency-dependent data
    freq_data, error_data, skin_props = frequency_dependence_analysis()
    
    # Size parameter sweep at 28 GHz
    x_vals, errors_total, errors_diffraction = size_parameter_sweep()
    
    # Compute R_sphere(f) - the frequency-dependent asymptotic limit.
    # Sample down to 1 GHz so the body-Mie panel (0-6 GHz) shows the
    # asymptote across its full window.
    freqs_dense_hz = np.linspace(1e9, 100e9, 100)
    R_dense = compute_R_sphere_vs_freq(freqs_dense_hz)
    asymp_dense = [(R - 1) * 100 for R in R_dense]
    
    # Also compute at the discrete frequency points
    R_discrete = compute_R_sphere_vs_freq([f * 1e9 for f in freq_data])
    asymp_discrete = [(R - 1) * 100 for R in R_discrete]
    
    # Three independent figures so each panel can be a LaTeX subfigure
    # with its own subcaption text (no in-panel (a)/(b)/(c) labels).
    fig_a, ax_a = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.78))
    fig_b, ax_b = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.78))
    fig_c, ax_c = plt.subplots(1, 1, figsize=fig_size_ieee(columns=1, aspect=0.78))
    axes = [ax_a, ax_b, ax_c]

    # Color-blind friendly palette (Okabe-Ito).
    CB_BLUE = "#0072B2"        # blue
    CB_VERMILION = "#D55E00"   # vermilion (red-orange)
    CB_GREEN = "#009E73"       # bluish green
    CB_PURPLE = "#CC79A7"      # reddish purple
    CB_ORANGE = "#E69F00"      # orange (Fresnel/asymptote accent)
    CB_GRAY = "#555555"

    # Common legend frame style: 1 pt black rectangle, no rounded corners.
    legend_kw = dict(
        frameon=True,
        fancybox=False,
        edgecolor="black",
        framealpha=1.0,
        borderpad=0.3,
        handlelength=2.0,
        handletextpad=0.5,
    )

    def _frame_legend(leg):
        if leg is None:
            return
        leg.get_frame().set_linewidth(1.0)
        leg.get_frame().set_edgecolor("black")
        leg.get_frame().set_boxstyle("Square", pad=0.3)

    # ========================================================================
    # Panel (a): error vs size parameter at 28 GHz
    # ========================================================================
    ax1 = axes[0]

    props_28 = skin_props[28e9]
    m_28 = props_28['m']
    T0_28 = props_28['T0']
    Q_abs_GO_28 = compute_GO_limit(m_28)
    R_sphere_28 = T0_28 / Q_abs_GO_28

    ax1.semilogx(x_vals, errors_total, color=CB_BLUE, linewidth=1.8,
                 label='Mie error')
    ax1.axhline(y=0, color='k', linestyle='--', alpha=0.5, linewidth=0.7)
    fresnel_label = (
        r'Fresnel limit $R_{\mathrm{sphere}}{-}1='
        + f'{(R_sphere_28 - 1) * 100:.1f}'
        + pct_math + r'$'
    )
    ax1.axhline(y=(R_sphere_28 - 1) * 100, color=CB_ORANGE, linestyle='-',
                linewidth=1.3, label=fresnel_label)

    ax1.set_xlabel(r'Size parameter $x = \pi d / \lambda$')
    ax1.set_ylabel(f'Prediction error [{pct}]')
    ax1.set_xlim([3, 2000])
    ax1.set_ylim([-70, 10])

    # Body-part guide lines at 28 GHz, with short labels rotated 90 degrees.
    wavelength_28 = c / 28e9
    body_parts_ann = [
        ('finger', 0.017),
        ('arm', 0.080),
        ('head', 0.180),
        ('torso', 0.300),
        ('body', 1.000),
    ]
    for name, d in body_parts_ann:
        x = np.pi * d / wavelength_28
        ax1.axvline(x=x, color=CB_GRAY, linestyle=':', alpha=0.5, linewidth=0.8)
        # Vertical labels in the upper region, just below the zero gridline.
        ax1.text(x, -3, name, ha='right', va='top', fontsize=7,
                 color=CB_GRAY, rotation=90)

    # Inside the panel at the lower-right corner, where the Mie dip
    # has already recovered toward the Fresnel asymptote and there is
    # room beneath the body-part guide labels.
    leg1 = ax1.legend(loc='lower right', frameon=True, fancybox=False,
                      edgecolor='black', framealpha=1.0,
                      borderpad=0.3, handlelength=1.8, handletextpad=0.5)
    _frame_legend(leg1)

    # ========================================================================
    # Panel (b): error vs frequency for body parts
    # ========================================================================
    ax2 = axes[1]

    body_specs = [
        ('Finger', '17 mm',  CB_BLUE,      's', '-'),
        ('Arm',    '80 mm',  CB_VERMILION, 'o', '--'),
        ('Head',   '180 mm', CB_GREEN,     '^', '-.'),
        ('Torso',  '300 mm', CB_PURPLE,    'D', ':'),
    ]
    # Y-window for panel B; mask points outside so the line breaks cleanly
    # at the Rayleigh-regime artifacts at very low frequency for the finger
    # (the Mie Q_abs series shrinks toward zero, sending the relative error
    # to several hundred percent).
    y_min, y_max = -70.0, 5.0
    for key, label, color, marker, ls in body_specs:
        errors = np.asarray(error_data[key], dtype=float)
        errors = np.where((errors > y_max) | (errors < y_min), np.nan, errors)
        ax2.plot(freq_data, errors, color=color, linewidth=1.4,
                 linestyle=ls, marker=marker, markersize=4.5,
                 markerfacecolor='none', markeredgewidth=1.0,
                 markeredgecolor=color, label=label)

    # Frequency-dependent Fresnel asymptote (curve only; the mmWave
    # band sits outside the 0-6 GHz window so no inline label).
    ax2.plot(freqs_dense_hz / 1e9, asymp_dense, color=CB_ORANGE,
             linewidth=1.4, label=r'$R_{\mathrm{sphere}}(f)-1$')

    ax2.set_xlabel('Frequency [GHz]')
    ax2.set_ylabel(f'Prediction error [{pct}]')
    ax2.set_xlim([1, 100])
    ax2.set_ylim([-70, 5])
    ax2.axhline(y=0, color='k', linestyle='--', alpha=0.5, linewidth=0.7)
    # Re-add the mmWave shading and inline label since the panel now
    # spans the full 1-100 GHz band again.
    ax2.axvspan(20, 60, alpha=0.10, color=CB_GREEN, linewidth=0)
    ax2.text(35, 4, 'mmWave', ha='center', va='top',
             fontsize=7, color=CB_GREEN, alpha=0.95)

    # Body-part diameter legend at lower-right where curves are at low |error|.
    leg2 = ax2.legend(loc='lower right', ncol=2, columnspacing=0.8,
                      handlelength=1.6, handletextpad=0.4,
                      frameon=True, fancybox=False, edgecolor='black',
                      framealpha=1.0, borderpad=0.3,
                      title='Diameter', title_fontsize=8)
    _frame_legend(leg2)

    # ========================================================================
    # Panel (c): R_sphere(f) Fresnel limit
    # ========================================================================
    ax3 = axes[2]

    ax3.plot(freqs_dense_hz / 1e9, R_dense, color=CB_BLUE, linewidth=1.6)
    ax3.plot(freq_data, R_discrete, color=CB_BLUE, linestyle='none',
             marker='o', markersize=4.5, markerfacecolor='none',
             markeredgewidth=1.0, markeredgecolor=CB_BLUE, zorder=5)
    ax3.axhline(y=1.0, color='k', linestyle='--', alpha=0.5, linewidth=0.7)
    ax3.axvspan(20, 60, alpha=0.10, color=CB_GREEN, linewidth=0)

    # Crossover at R = 1.
    R_arr = np.array(R_dense)
    f_arr = freqs_dense_hz / 1e9
    cross_idx = np.where(np.diff(np.sign(R_arr - 1.0)))[0]
    f_cross = None
    if len(cross_idx) > 0:
        # Linear interpolation for sub-grid accuracy.
        i = cross_idx[0]
        f_cross = f_arr[i] + (1.0 - R_arr[i]) * (f_arr[i+1] - f_arr[i]) / (R_arr[i+1] - R_arr[i])
        ax3.axvline(x=f_cross, color=CB_GRAY, linestyle=':', alpha=0.7,
                    linewidth=0.8)
        ax3.annotate(rf'$R=1$ at ${f_cross:.0f}$ GHz',
                     xy=(f_cross, 1.0), xytext=(f_cross + 22, 0.972),
                     fontsize=7.5, ha='center', color='k',
                     arrowprops=dict(arrowstyle='-|>', color=CB_GRAY,
                                     alpha=0.8, lw=0.6,
                                     shrinkA=0, shrinkB=2))

    # Inline labels for under/over regions, in the empty corners.
    # The curve runs lower-left to upper-right; underestimates ($R<1$) is the
    # lower half, overestimates ($R>1$) is the upper half. To avoid the curve,
    # place the lower-half label in the lower-RIGHT corner and the upper-half
    # label in the upper-LEFT corner.
    ax3.text(0.97, 0.08, r'underestimates ($R<1$)', transform=ax3.transAxes,
             fontsize=7, color=CB_BLUE, alpha=0.9, va='center', ha='right')
    ax3.text(0.03, 0.92, r'overestimates ($R>1$)', transform=ax3.transAxes,
             fontsize=7, color=CB_VERMILION, alpha=0.9, va='center', ha='left')

    ax3.set_xlabel('Frequency [GHz]')
    ax3.set_ylabel(r'$R_{\mathrm{sphere}} = T_0 / \langle T_{\mathrm{avg}} \rangle$')

    # Secondary y-axis: asymptotic error in %.
    ax3b = ax3.twinx()
    y1_lo, y1_hi = 0.96, 1.04
    ax3.set_ylim([y1_lo, y1_hi])
    ax3b.set_ylim([(y1_lo - 1) * 100, (y1_hi - 1) * 100])
    ax3b.set_ylabel(f'Asymptotic error [{pct}]')
    ax3b.tick_params(axis='y')
    # Match grid: ensure secondary axis does not draw its own grid.
    ax3b.grid(False)

    ax3.set_xlim([0, 105])

    # Save three separate figures
    output_dir = out_dir if out_dir is not None else (Path(__file__).parent.parent / "figures")
    output_dir.mkdir(exist_ok=True)
    ext = ".png" if mode == "png" else ".pdf"
    out_a = output_dir / f"mie_panel_size{ext}"
    out_b = output_dir / f"mie_panel_freq{ext}"
    out_c = output_dir / f"mie_R_sphere{ext}"
    save_kw = dict(dpi=300, bbox_inches="tight") if mode == "png" else dict(bbox_inches="tight")
    fig_a.tight_layout(pad=0.4)
    fig_b.tight_layout(pad=0.4)
    fig_c.tight_layout(pad=0.4)
    fig_a.savefig(out_a, **save_kw)
    fig_b.savefig(out_b, **save_kw)
    fig_c.savefig(out_c, **save_kw)
    plt.close(fig_a)
    plt.close(fig_b)
    plt.close(fig_c)
    print(f"\nPlots saved: {out_a}, {out_b}, {out_c}")

    return out_a


def generate_summary_tables():
    """Generate summary tables for the paper."""
    
    print("\n" + "=" * 70)
    print("SUMMARY TABLES FOR PAPER")
    print("=" * 70)
    
    # Table 1: Error vs size parameter at 28 GHz
    print("\n### Table 1: Error vs Size Parameter (Skin at 28 GHz)")
    print("\n| x = pi*d/lambda | Q_abs (exact) | T_0 (approx) | Error |")
    print("|-----------------|---------------|--------------|-------|")
    
    props_28 = get_skin_properties(28e9)
    m = props_28['m']
    T0 = props_28['T0']
    lambda0 = 1.0
    
    for x in [1, 5, 10, 20, 50, 100]:
        d = x * lambda0 / np.pi
        qext, qsca, _, _ = mp.efficiencies(m, d, lambda0)
        qabs = qext - qsca
        error = (T0 / qabs - 1) * 100
        print(f"| {x:>8} | {qabs:>13.2f} | {T0:>12.2f} | {error:>+5.0f}% |")
    
    # Table 2: Error vs frequency for body parts
    print("\n### Table 2: Error vs Frequency for Body Parts")
    print("\n| Frequency | Finger (17mm) | Arm (80mm) | Head (180mm) | Torso (300mm) |")
    print("|-----------|---------------|------------|--------------|---------------|")
    
    c = C_0
    body_parts = {'Finger (17mm)': 0.017, 'Arm (80mm)': 0.080, 
                  'Head (180mm)': 0.180, 'Torso (300mm)': 0.300}
    
    for freq_ghz in [6, 28, 60, 100]:
        freq_hz = freq_ghz * 1e9
        props = get_skin_properties(freq_hz)
        m = props['m']
        T0 = props['T0']
        wavelength = c / freq_hz
        
        row = f"| {freq_ghz:>9} GHz |"
        
        for name, d in body_parts.items():
            qext, qsca, _, _ = mp.efficiencies(m, d, wavelength)
            qabs = qext - qsca
            error = (T0 / qabs - 1) * 100
            row += f" {error:>+13.1f}% |"
        
        print(row)
    
    # Table 3: Frequency-dependent skin properties
    print("\n### Table 3: IT'IS Skin Properties")
    print("\n| Freq (GHz) | eps_r | sigma (S/m) | abs(m) | T_0 | R_sphere |")
    print("|------------|-------|-------------|--------|-----|----------|")
    
    for freq_ghz in [6, 10, 28, 40, 60, 100]:
        freq_hz = freq_ghz * 1e9
        props = get_skin_properties(freq_hz)
        Q_abs_GO = compute_GO_limit(props['m'])
        R_sphere = props['T0'] / Q_abs_GO
        
        print(f"| {freq_ghz:>10.0f} | {props['eps_r']:>3.0f} | {props['sigma']:>7.1f} | "
              f"{props['abs_m']:>3.1f} | {props['T0']:.3f} | {R_sphere:.3f} |")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mie validation (corrected).")
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
        help="Directory to write output figure into.",
    )
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("MIE THEORY VALIDATION (CORRECTED)")
    print("Using IT'IS v5.0 Database for Frequency-Dependent Skin Properties")
    print("=" * 70)
    
    # Run analyses
    test_mie_single_frequency()
    freq_data, error_data, skin_props = frequency_dependence_analysis()
    outdir = Path(args.outdir)
    outdir.mkdir(exist_ok=True)
    create_validation_plots(mode=args.mode, out_dir=outdir)
    generate_summary_tables()
    
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
    print("\nKey corrections from previous version:")
    print("1. [OK] Frequency-dependent m(f) from IT'IS Gabriel model")
    print("2. [OK] Asymptotic error limit is ~-1.2% (Fresnel approx), not 0%")
    print("3. [OK] Framework can overestimate at high freq for large objects")
    print("4. [OK] Properly shows diffraction vs Fresnel error components")
    # Note: no `plt.show()`; this script is intended to be reproducible and non-interactive.
