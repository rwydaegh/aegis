"""
Comprehensive Skin Model Comparison
====================================

This script loads skin dielectric properties from:
1. NICT measurements-Skin.csv (direct measurements - ground truth)
2. IT'IS v5.0 database (Gabriel 1996 4-Cole-Cole model)
3. Gabriel × 1.2 (Christ 2021 actual skin model - fitted to measurements)
4. Christ 2025 Dermis (Layer D, mean - newest Debye model)

And plots them together for comparison.

Author: PRL EMT Project
Date: 2026-02-06
"""

import numpy as np
import matplotlib.pyplot as plt
import sqlite3
import struct
import cmath
from pathlib import Path
import csv
import re

# Physical constants
EPS_0 = 8.854187817e-12  # F/m

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


def debye_permittivity(freq_hz, eps_inf, eps_static, sigma, tau_ps):
    """
    Calculate complex permittivity using Debye model (α=0 Cole-Cole).
    
    From Christ et al. 2025, Table 6 (Layer D dermis):
    ε_r(ω) = ε_∞ + (ε_s - ε_∞)/(1 + jωτ) - jσ/(ωε₀)
    
    Parameters:
    -----------
    freq_hz : float or array
        Frequency in Hz
    eps_inf : float
        High-frequency permittivity limit (ε_∞)
    eps_static : float
        Static permittivity (ε_s)
    sigma : float
        Static conductivity in S/m
    tau_ps : float
        Relaxation time in picoseconds
    
    Returns:
    --------
    eps_complex : complex or array of complex
        Complex relative permittivity ε_r = ε' - jε''
    """
    omega = 2 * np.pi * freq_hz
    tau = tau_ps * 1e-12  # Convert ps to seconds
    
    # Debye term: (ε_s - ε_∞)/(1 + jωτ)
    debye_term = (eps_static - eps_inf) / (1 + 1j * omega * tau)
    
    # Conductivity term: -jσ/(ωε₀)
    if sigma > 0 and np.any(omega > 0):
        cond_term = -1j * sigma / (omega * EPS_0)
    else:
        cond_term = 0
    
    eps_complex = eps_inf + debye_term + cond_term
    
    return eps_complex


def load_nict_data():
    """Load NICT measurements from CSV file."""
    csv_path = Path(__file__).parent.parent / "data" / "measurements-Skin.csv"
    
    freq_hz = []
    eps_r = []
    loss_factor = []
    sigma = []
    
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header
        
        for row in reader:
            if len(row) >= 4 and row[0].strip():
                try:
                    # Parse NICT's weird format like '1.000000.E+06'
                    def parse_val(s):
                        return float(re.sub(r'\.E', 'E', s.strip()))
                    freq_hz.append(parse_val(row[0]))
                    eps_r.append(parse_val(row[1]))
                    loss_factor.append(parse_val(row[2]))
                    sigma.append(parse_val(row[3]))
                except ValueError:
                    continue
    
    return {
        'freq_hz': np.array(freq_hz),
        'eps_r': np.array(eps_r),
        'loss_factor': np.array(loss_factor),
        'sigma': np.array(sigma)
    }


def main():
    """Main function to compare IT'IS and NICT data."""
    
    # Load NICT measurements
    print("Loading NICT measurements...")
    nict_data = load_nict_data()
    
    nict_freq_hz = nict_data['freq_hz']
    nict_eps_r = nict_data['eps_r']
    nict_sigma = nict_data['sigma']
    
    print(f"  NICT frequency range: {nict_freq_hz.min():.2e} Hz to {nict_freq_hz.max():.2e} Hz")
    print(f"  NICT frequency range: {nict_freq_hz.min()/1e6:.2f} MHz to {nict_freq_hz.max()/1e9:.2f} GHz")
    print(f"  Number of NICT data points: {len(nict_freq_hz)}")
    
    # Load IT'IS Gabriel parameters
    print("\nLoading IT'IS Gabriel parameters...")
    params = get_gabriel_params('Skin')
    
    if params is None:
        raise ValueError("Could not load skin parameters from IT'IS database")
    
    print(f"  Gabriel parameters loaded:")
    print(f"    ef = {params['ef']}")
    print(f"    del1 = {params['del1']}, tau1 = {params['tau1']} ps, alf1 = {params['alf1']}")
    print(f"    del2 = {params['del2']}, tau2 = {params['tau2']} ns, alf2 = {params['alf2']}")
    print(f"    del3 = {params['del3']}, tau3 = {params['tau3']} us, alf3 = {params['alf3']}")
    print(f"    del4 = {params['del4']}, tau4 = {params['tau4']} ms, alf4 = {params['alf4']}")
    print(f"    sig = {params['sig']} S/m")
    
    # Calculate IT'IS model values at NICT frequencies
    print("\nCalculating IT'IS Gabriel model values...")
    itis_eps_r = np.zeros(len(nict_freq_hz))
    itis_sigma = np.zeros(len(nict_freq_hz))
    
    for i, freq in enumerate(nict_freq_hz):
        eps_complex = cole_cole_permittivity(freq, params)
        itis_eps_r[i] = eps_complex.real
        itis_sigma[i] = -eps_complex.imag * 2 * np.pi * freq * EPS_0
    
    # Calculate Gabriel × 1.2 (Christ 2021 actual skin model)
    print("\nCalculating Gabriel × 1.2 (Christ 2021 skin model)...")
    print("  (20% increase in both permittivity and conductivity)")
    gabriel_scaled_eps_r = itis_eps_r * 1.2
    gabriel_scaled_sigma = itis_sigma * 1.2
    
    # Calculate Christ 2025 Dermis (Layer D, mean)
    print("\nCalculating Christ 2025 Dermis (Layer D, mean)...")
    # Table 6 parameters from Christ et al. 2025
    christ2025_eps_inf = 7.88
    christ2025_eps_static = 47.0
    christ2025_sigma_static = 5.19  # S/m
    christ2025_tau_ps = 8.35  # ps
    
    christ2025_eps_r = np.zeros(len(nict_freq_hz))
    christ2025_sigma_eff = np.zeros(len(nict_freq_hz))
    
    for i, freq in enumerate(nict_freq_hz):
        eps_complex = debye_permittivity(
            freq, christ2025_eps_inf, christ2025_eps_static,
            christ2025_sigma_static, christ2025_tau_ps
        )
        christ2025_eps_r[i] = eps_complex.real
        christ2025_sigma_eff[i] = -eps_complex.imag * 2 * np.pi * freq * EPS_0
    
    print(f"  Christ 2025 Debye parameters:")
    print(f"    eps_inf = {christ2025_eps_inf}")
    print(f"    eps_static = {christ2025_eps_static}")
    print(f"    sigma_0 = {christ2025_sigma_static} S/m")
    print(f"    tau = {christ2025_tau_ps} ps")
    
    # Create figure with two subplots
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Convert frequency to GHz for plotting
    freq_ghz = nict_freq_hz / 1e9
    
    # Plot 1: Relative Permittivity
    ax1 = axes[0]
    ax1.loglog(freq_ghz, nict_eps_r, 'b-', linewidth=2.5, label='NICT Measurements', alpha=0.9)
    ax1.loglog(freq_ghz, itis_eps_r, 'r--', linewidth=2, label="IT'IS Gabriel 1996", alpha=0.7)
    ax1.loglog(freq_ghz, gabriel_scaled_eps_r, 'orange', linestyle='-.', linewidth=2, 
               label='Gabriel × 1.2 (Christ 2021)', alpha=0.7)
    ax1.loglog(freq_ghz, christ2025_eps_r, 'g:', linewidth=2.5, label='Christ 2025 Dermis', alpha=0.8)
    ax1.set_xlabel('Frequency (GHz)', fontsize=12)
    ax1.set_ylabel('Relative Permittivity (ε\')', fontsize=12)
    ax1.set_title('Skin Relative Permittivity: Model Comparison', fontsize=14)
    ax1.legend(fontsize=10, loc='best')
    ax1.grid(True, which='both', alpha=0.3)
    ax1.set_xlim([freq_ghz.min(), freq_ghz.max()])
    
    # Add vertical lines for key frequencies
    for f_marker, label in [(0.001, '1 MHz'), (1, '1 GHz'), (10, '10 GHz'), (100, '100 GHz')]:
        if freq_ghz.min() <= f_marker <= freq_ghz.max():
            ax1.axvline(f_marker, color='gray', linestyle=':', alpha=0.5)
    
    # Plot 2: Electrical Conductivity
    ax2 = axes[1]
    ax2.loglog(freq_ghz, nict_sigma, 'b-', linewidth=2.5, label='NICT Measurements', alpha=0.9)
    ax2.loglog(freq_ghz, itis_sigma, 'r--', linewidth=2, label="IT'IS Gabriel 1996", alpha=0.7)
    ax2.loglog(freq_ghz, gabriel_scaled_sigma, 'orange', linestyle='-.', linewidth=2,
               label='Gabriel × 1.2 (Christ 2021)', alpha=0.7)
    ax2.loglog(freq_ghz, christ2025_sigma_eff, 'g:', linewidth=2.5, label='Christ 2025 Dermis', alpha=0.8)
    ax2.set_xlabel('Frequency (GHz)', fontsize=12)
    ax2.set_ylabel('Electrical Conductivity σ (S/m)', fontsize=12)
    ax2.set_title('Skin Conductivity: Model Comparison', fontsize=14)
    ax2.legend(fontsize=10, loc='best')
    ax2.grid(True, which='both', alpha=0.3)
    ax2.set_xlim([freq_ghz.min(), freq_ghz.max()])
    
    # Add vertical lines for key frequencies
    for f_marker, label in [(0.001, '1 MHz'), (1, '1 GHz'), (10, '10 GHz'), (100, '100 GHz')]:
        if freq_ghz.min() <= f_marker <= freq_ghz.max():
            ax2.axvline(f_marker, color='gray', linestyle=':', alpha=0.5)
    
    plt.tight_layout()
    output_dir = Path(__file__).parent.parent / 'figures'
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'skin_itis_vs_nict_comparison.png', dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {output_dir / 'skin_itis_vs_nict_comparison.png'}")
    
    # Create second figure: Linear scale 20-100 GHz
    fig2, axes2 = plt.subplots(1, 2, figsize=(14, 6))
    mask_hf = (freq_ghz >= 20) & (freq_ghz <= 100)
    freq_hf = freq_ghz[mask_hf]
    nict_eps_hf = nict_eps_r[mask_hf]
    nict_sigma_hf = nict_sigma[mask_hf]
    itis_eps_hf = itis_eps_r[mask_hf]
    itis_sigma_hf = itis_sigma[mask_hf]
    gabriel_scaled_eps_hf = gabriel_scaled_eps_r[mask_hf]
    gabriel_scaled_sigma_hf = gabriel_scaled_sigma[mask_hf]
    christ2025_eps_hf = christ2025_eps_r[mask_hf]
    christ2025_sigma_hf = christ2025_sigma_eff[mask_hf]
    
    ax3 = axes2[0]
    ax3.plot(freq_hf, nict_eps_hf, 'b-', linewidth=2.5, label='NICT Measurements', alpha=0.9)
    ax3.plot(freq_hf, itis_eps_hf, 'r--', linewidth=2, label="IT'IS Gabriel 1996", alpha=0.7)
    ax3.plot(freq_hf, gabriel_scaled_eps_hf, 'orange', linestyle='-.', linewidth=2,
             label='Gabriel × 1.2 (Christ 2021)', alpha=0.7)
    ax3.plot(freq_hf, christ2025_eps_hf, 'g:', linewidth=2.5, label='Christ 2025 Dermis', alpha=0.8)
    ax3.set_xlabel('Frequency (GHz)', fontsize=12)
    ax3.set_ylabel("Relative Permittivity", fontsize=12)
    ax3.set_title('Skin Permittivity 20-100 GHz (Linear Scale)', fontsize=14)
    ax3.legend(fontsize=10, loc='best')
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim([20, 100])
    
    ax4 = axes2[1]
    ax4.plot(freq_hf, nict_sigma_hf, 'b-', linewidth=2.5, label='NICT Measurements', alpha=0.9)
    ax4.plot(freq_hf, itis_sigma_hf, 'r--', linewidth=2, label="IT'IS Gabriel 1996", alpha=0.7)
    ax4.plot(freq_hf, gabriel_scaled_sigma_hf, 'orange', linestyle='-.', linewidth=2,
             label='Gabriel × 1.2 (Christ 2021)', alpha=0.7)
    ax4.plot(freq_hf, christ2025_sigma_hf, 'g:', linewidth=2.5, label='Christ 2025 Dermis', alpha=0.8)
    ax4.set_xlabel('Frequency (GHz)', fontsize=12)
    ax4.set_ylabel('Electrical Conductivity (S/m)', fontsize=12)
    ax4.set_title('Skin Conductivity 20-100 GHz (Linear Scale)', fontsize=14)
    ax4.legend(fontsize=10, loc='best')
    ax4.grid(True, alpha=0.3)
    ax4.set_xlim([20, 100])
    plt.tight_layout()
    output_dir = Path(__file__).parent.parent / 'figures'
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / 'skin_itis_vs_nict_20_100GHz_linear.png', dpi=150, bbox_inches='tight')
    print(f"Plot saved to: {output_dir / 'skin_itis_vs_nict_20_100GHz_linear.png'}")
    
    # Calculate and print statistics
    print("\n" + "="*70)
    print("COMPARISON STATISTICS (All Models vs. NICT Measurements)")
    print("="*70)
    
    # Relative differences
    eps_rel_diff_itis = (itis_eps_r - nict_eps_r) / nict_eps_r * 100
    sigma_rel_diff_itis = (itis_sigma - nict_sigma) / nict_sigma * 100
    eps_rel_diff_gabriel_scaled = (gabriel_scaled_eps_r - nict_eps_r) / nict_eps_r * 100
    sigma_rel_diff_gabriel_scaled = (gabriel_scaled_sigma - nict_sigma) / nict_sigma * 100
    eps_rel_diff_christ2025 = (christ2025_eps_r - nict_eps_r) / nict_eps_r * 100
    sigma_rel_diff_christ2025 = (christ2025_sigma_eff - nict_sigma) / nict_sigma * 100
    
    print(f"\n1. IT'IS Gabriel 1996:")
    print(f"   Permittivity:  Mean={np.mean(eps_rel_diff_itis):+.2f}%, Std={np.std(eps_rel_diff_itis):.2f}%")
    print(f"   Conductivity:  Mean={np.mean(sigma_rel_diff_itis):+.2f}%, Std={np.std(sigma_rel_diff_itis):.2f}%")
    
    print(f"\n2. Gabriel × 1.2 (Christ 2021 fitted):")
    print(f"   Permittivity:  Mean={np.mean(eps_rel_diff_gabriel_scaled):+.2f}%, Std={np.std(eps_rel_diff_gabriel_scaled):.2f}%")
    print(f"   Conductivity:  Mean={np.mean(sigma_rel_diff_gabriel_scaled):+.2f}%, Std={np.std(sigma_rel_diff_gabriel_scaled):.2f}%")
    
    print(f"\n3. Christ 2025 Dermis (Layer D, mean):")
    print(f"   Permittivity:  Mean={np.mean(eps_rel_diff_christ2025):+.2f}%, Std={np.std(eps_rel_diff_christ2025):.2f}%")
    print(f"   Conductivity:  Mean={np.mean(sigma_rel_diff_christ2025):+.2f}%, Std={np.std(sigma_rel_diff_christ2025):.2f}%")
    
    # Frequency band analysis
    print("\n" + "-"*70)
    print("FREQUENCY BAND ANALYSIS (% Difference from NICT)")
    print("-"*70)
    
    bands = [
        ('10-100 GHz (mmWave)', 10e9, 100e9),
        ('1-10 GHz', 1e9, 10e9),
        ('100 MHz - 1 GHz', 100e6, 1e9),
    ]
    
    for band_name, f_min, f_max in bands:
        mask = (nict_freq_hz >= f_min) & (nict_freq_hz <= f_max)
        if np.any(mask):
            print(f"\n{band_name}:")
            
            eps_diff_band_itis = eps_rel_diff_itis[mask]
            sigma_diff_band_itis = sigma_rel_diff_itis[mask]
            print(f"  Gabriel 1996:      eps'={np.mean(eps_diff_band_itis):+5.1f}+/-{np.std(eps_diff_band_itis):4.1f}%  "
                  f"sigma={np.mean(sigma_diff_band_itis):+5.1f}+/-{np.std(sigma_diff_band_itis):4.1f}%")
            
            eps_diff_band_scaled = eps_rel_diff_gabriel_scaled[mask]
            sigma_diff_band_scaled = sigma_rel_diff_gabriel_scaled[mask]
            print(f"  Gabriel x 1.2:     eps'={np.mean(eps_diff_band_scaled):+5.1f}+/-{np.std(eps_diff_band_scaled):4.1f}%  "
                  f"sigma={np.mean(sigma_diff_band_scaled):+5.1f}+/-{np.std(sigma_diff_band_scaled):4.1f}%")
            
            eps_diff_band_2025 = eps_rel_diff_christ2025[mask]
            sigma_diff_band_2025 = sigma_rel_diff_christ2025[mask]
            print(f"  Christ 2025:       eps'={np.mean(eps_diff_band_2025):+5.1f}+/-{np.std(eps_diff_band_2025):4.1f}%  "
                  f"sigma={np.mean(sigma_diff_band_2025):+5.1f}+/-{np.std(sigma_diff_band_2025):4.1f}%")
    
    plt.show()


if __name__ == "__main__":
    main()
