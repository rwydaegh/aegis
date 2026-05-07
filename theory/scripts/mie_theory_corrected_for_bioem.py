"""
Mie Theory Validation – BioEM 2026 figure (two-panel version)
=============================================================

Produces a two-panel figure:
  Top:    Framework error vs size parameter at 28 GHz
  Bottom: Framework error vs frequency for four body-part sizes

The third panel (R_sphere vs frequency) from the full monograph figure is
omitted; that information is stated in the text and visible as the Fresnel
limit line in the first two panels.

Based on: mie_theory_corrected.py
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

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from _plot_style import apply_monograph_style, fig_size_textwidth

import argparse

# Physical constants
EPS_0 = 8.854187817e-12  # F/m
C_0 = 299792458.0         # m/s

# Database paths
DB_PATHS = [
    Path(__file__).parent.parent / "data" / "itis_v5.db",
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
    c.execute("SELECT prop_id FROM properties WHERE name = ?", ('Gabriel Parameters',))
    prop_result = c.fetchone()
    if not prop_result:
        conn.close()
        return None
    prop_id = prop_result[0]
    c.execute("""SELECT m.mat_id, v.vals
                 FROM materials m
                 JOIN vectors v ON m.mat_id = v.mat_id
                 WHERE m.name = ? AND v.prop_id = ?
                 LIMIT 1""", (tissue_name, prop_id))
    result = c.fetchone()
    if not result:
        conn.close()
        return None
    blob = result[1]
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
    tau_units = [1e-12, 1e-9, 1e-6, 1e-3]
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
    m = cmath.sqrt(eps_complex)
    if m.real < 0:
        m = -m
    n = m.real
    kappa = -m.imag
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
    """Compute geometric optics limit: Q_abs_GO = 2 * integral(T_avg(mu)*mu, 0, 1)."""
    def T_avg(mu):
        if mu <= 0:
            return 0
        n2 = m**2
        xi = cmath.sqrt(n2 - 1 + mu**2)
        if xi.real < 0:
            xi = -xi
        rs = (mu - xi) / (mu + xi)
        Ts = 1 - abs(rs)**2
        rp = (n2 * mu - xi) / (n2 * mu + xi)
        Tp = 1 - abs(rp)**2
        return 0.5 * (Ts + Tp)
    integral, _ = integrate.quad(lambda mu: 2 * T_avg(mu) * mu, 0, 1)
    return integral


def frequency_dependence_analysis():
    """Analyze framework error vs frequency for fixed body sizes."""
    body_parts = {
        'Finger': 0.017,
        'Arm': 0.080,
        'Head': 0.180,
        'Torso': 0.300,
    }
    freqs = [6e9, 10e9, 20e9, 28e9, 40e9, 60e9, 77e9, 100e9]
    results = {}
    for f in freqs:
        results[f] = get_skin_properties(f)
    freq_data = []
    error_data = {name: [] for name in body_parts}
    for f in freqs:
        wavelength = C_0 / f
        props = results[f]
        m = props['m']
        T0 = props['T0']
        for name, d in body_parts.items():
            x = np.pi * d / wavelength
            qext, qsca, qback, g = mp.efficiencies(m, d, wavelength)
            qabs = qext - qsca
            if qabs > 0.01:
                error_data[name].append((T0 / qabs - 1) * 100)
            else:
                error_data[name].append(np.nan)
        freq_data.append(f / 1e9)
    return freq_data, error_data, results


def size_parameter_sweep():
    """Sweep size parameter at 28 GHz to show convergence to GO limit."""
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
            errors.append((T0 / qabs - 1) * 100)
            errors_diffraction.append((Q_abs_GO / qabs - 1) * 100)
        else:
            errors.append(np.nan)
            errors_diffraction.append(np.nan)
    return x_vals, errors, errors_diffraction


def create_validation_plots(*, mode: str = "png", out_dir: Path | None = None) -> Path:
    """Create two-panel validation figure for BioEM 2026."""
    apply_monograph_style(mode=("pdf" if mode == "pdf" else "png"))
    pct = r"\%" if mode == "pdf" else "%"

    c = C_0

    # Data
    freq_data, error_data, skin_props = frequency_dependence_analysis()
    x_vals, errors_total, errors_diffraction = size_parameter_sweep()

    # Fresnel limit line for the middle panel (frequency-dependent)
    freqs_dense_hz = np.linspace(6e9, 100e9, 50)
    asymp_dense = []
    for f in freqs_dense_hz:
        props = get_skin_properties(f)
        Q_abs_GO = compute_GO_limit(props['m'])
        asymp_dense.append((props['T0'] / Q_abs_GO - 1) * 100)

    # Two-panel figure
    fig, axes = plt.subplots(2, 1, figsize=fig_size_textwidth(aspect=1.20))

    # === Top panel: Error vs size parameter (28 GHz) ===
    ax1 = axes[0]

    props_28 = skin_props[28e9]
    m_28 = props_28['m']
    T0_28 = props_28['T0']
    Q_abs_GO_28 = compute_GO_limit(m_28)
    R_sphere_28 = T0_28 / Q_abs_GO_28

    ax1.semilogx(x_vals, errors_total, 'b-', linewidth=2, label='Total framework error')
    ax1.semilogx(x_vals, errors_diffraction, color='steelblue', linestyle='--',
                 linewidth=1.5, alpha=0.7, label='Diffraction error only')
    ax1.axhline(y=0, color='k', linestyle='--', alpha=0.4)
    ax1.axhline(y=-10, color='r', linestyle=':', alpha=0.4)
    ax1.axhline(y=10, color='r', linestyle=':', alpha=0.4, label=rf'$\pm$10{pct} error')
    ax1.axhline(y=(R_sphere_28 - 1)*100, color='darkorange', linestyle='-', alpha=0.8,
                linewidth=1.5, label=f'Fresnel limit (R={R_sphere_28:.3f})')

    ax1.set_xlabel(r'Size parameter $x = \pi d/\lambda$')
    ax1.set_ylabel(f'Framework error ({pct})')
    ax1.set_title('Error vs size parameter (Skin at 28 GHz)')
    ax1.set_xlim([0.3, 2000])
    ax1.set_ylim([-70, 20])
    ax1.grid(True, alpha=0.25)
    ax1.legend(loc='upper left', frameon=True, fontsize=6,
               fancybox=False, edgecolor='black', borderpad=0.4).get_frame().set_linewidth(1.0)

    # Body-part annotations
    wavelength_28 = c / 28e9
    body_parts_ann = [
        ("Finger\n(17mm)", 0.017, -60),
        ("Arm\n(80mm)",    0.08,  -60),
        ("Head\n(180mm)",  0.18,  -50),
        ("Torso\n(300mm)", 0.3,   -35),
    ]
    for name, d, y_pos in body_parts_ann:
        x = np.pi * d / wavelength_28
        ax1.axvline(x=x, color='gray', linestyle='--', alpha=0.3, linewidth=0.8)
        ax1.text(x, y_pos, name, ha='center', fontsize=7, color='gray')

    # === Bottom panel: Error vs frequency ===
    ax2 = axes[1]

    colors = ['red', 'orange', 'green', 'blue']
    labels = ['Finger (17mm)', 'Arm (80mm)', 'Head (180mm)', 'Torso (300mm)']

    for label, color in zip(labels, colors):
        errors = error_data[label.split()[0]]
        ax2.plot(freq_data, errors, color=color, linewidth=2, marker='o',
                 markersize=4, label=label)

    ax2.plot(freqs_dense_hz / 1e9, asymp_dense, 'k-', linewidth=2.5, alpha=0.8,
             label=r'Fresnel limit $(R_{\mathrm{sphere}}(f)-1)$')

    ax2.axhline(y=0, color='k', linestyle='--', alpha=0.4)
    ax2.axhline(y=-10, color='gray', linestyle=':', alpha=0.4)
    ax2.axvspan(20, 60, alpha=0.08, color='green', label='mmWave (20-60 GHz)')
    ax2.set_xlabel('Frequency (GHz)')
    ax2.set_ylabel(f'Framework error ({pct})')
    ax2.set_title("Error vs frequency (IT'IS skin properties)")
    ax2.set_xlim([0, 105])
    ax2.set_ylim([-70, 10])
    ax2.grid(True, alpha=0.25)
    ax2.legend(loc='lower right', ncol=1, frameon=True, fontsize=6,
               fancybox=False, edgecolor='black', borderpad=0.4).get_frame().set_linewidth(1.0)

    plt.tight_layout()

    # Save
    output_dir = out_dir if out_dir is not None else (Path(__file__).parent.parent / "bioem2026" / "figures")
    output_dir.mkdir(exist_ok=True)
    ext = ".png" if mode == "png" else ".pdf"
    output_path = output_dir / f"mie_validation_corrected_for_bioem{ext}"
    if mode == "png":
        fig.savefig(output_path, dpi=250, bbox_inches="tight")
    else:
        fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Plot saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mie validation (BioEM 2-panel).")
    parser.add_argument("--mode", type=str, choices=["png", "pdf"], default="png")
    parser.add_argument("--outdir", type=str, default=None,
                        help="Output directory (default: bioem2026/figures/)")
    args = parser.parse_args()

    out = Path(args.outdir) if args.outdir else None
    create_validation_plots(mode=args.mode, out_dir=out)
