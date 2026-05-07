"""
Christ et al. 2025 Skin Model Implementation
============================================

Implements the two-layer Debye model from:
Christ, A., et al. (2025). "Human Skin Model From 15 GHz to 110 GHz"
Bioelectromagnetics, 46(7), e70025.

Table 6 parameters for Layer D (dermis) and Layer SC (stratum corneum).

Author: PRL EMT Project
Date: 2026-02-06
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Physical constants
EPS_0 = 8.854187817e-12  # F/m (permittivity of free space)

# Table 6 Parameters from Christ et al. 2025
# Layer D (Dermis) - Debye model parameters
LAYER_D_PARAMS = {
    'mean': {
        'd_um': np.inf,  # Infinite (bulk)
        'eps_inf': 7.88,
        'eps_static': 47.0,
        'sigma': 5.19,  # S/m
        'tau_ps': 8.35
    },
    '68pct': {
        'd_um': np.inf,
        'eps_inf': 5.06,
        'eps_static': 37.0,
        'sigma': 7.62,
        'tau_ps': 8.19
    },
    '95pct': {
        'd_um': np.inf,
        'eps_inf': 2.98,
        'eps_static': 32.8,
        'sigma': 6.94,
        'tau_ps': 8.76
    }
}

# Layer SC (Stratum Corneum) - Debye model parameters
LAYER_SC_PARAMS = {
    'thin': {
        'd_um': 20.0,
        'eps_inf': 2.96,
        'eps_static': 4.46,
        'sigma': 0.0,  # Lossless
        'tau_ps': 6.9
    },
    'thick1': {
        'd_um': 227.0,
        'eps_inf': 4.01,
        'eps_static': 9.11,
        'sigma': 0.0,  # Lossless
        'tau_ps': 1.63
    },
    'thick2': {
        'd_um': 262.0,
        'eps_inf': 3.27,
        'eps_static': 8.22,
        'sigma': 0.0,
        'tau_ps': 2.04
    },
    'thick3': {
        'd_um': 295.0,
        'eps_inf': 2.49,
        'eps_static': 7.29,
        'sigma': 0.0,
        'tau_ps': 2.22
    }
}


def debye_permittivity(freq_hz, eps_inf, eps_static, sigma, tau_ps):
    """
    Calculate complex permittivity using Debye model (α=0).
    
    Equation (1) from Christ et al. 2025 with α=0:
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
    debey_term = (eps_static - eps_inf) / (1 + 1j * omega * tau)
    
    # Conductivity term: -jσ/(ωε₀)
    if sigma > 0 and np.any(omega > 0):
        cond_term = -1j * sigma / (omega * EPS_0)
    else:
        cond_term = 0
    
    eps_complex = eps_inf + debey_term + cond_term
    
    return eps_complex


def get_skin_properties(freq_hz, layer_d_type='mean', layer_sc_type='thin'):
    """
    Get frequency-dependent dielectric properties for two-layer skin model.
    
    Parameters:
    -----------
    freq_hz : float or array
        Frequency in Hz
    layer_d_type : str
        'mean', '68pct', or '95pct' for Layer D coverage
    layer_sc_type : str
        'thin', 'thick1', 'thick2', or 'thick3' for Layer SC thickness
    
    Returns:
    --------
    dict with keys:
        'freq_hz': frequency array
        'layer_d': dict with 'eps_r', 'sigma', 'eps_complex' for dermis
        'layer_sc': dict with 'eps_r', 'sigma', 'eps_complex' for SC
        'd_sc_um': SC layer thickness in micrometers
    """
    # Get parameters
    d_params = LAYER_D_PARAMS[layer_d_type]
    sc_params = LAYER_SC_PARAMS[layer_sc_type]
    
    # Calculate complex permittivity for each layer
    eps_d = debye_permittivity(
        freq_hz, 
        d_params['eps_inf'], 
        d_params['eps_static'], 
        d_params['sigma'], 
        d_params['tau_ps']
    )
    
    eps_sc = debye_permittivity(
        freq_hz,
        sc_params['eps_inf'],
        sc_params['eps_static'],
        sc_params['sigma'],
        sc_params['tau_ps']
    )
    
    # Extract real permittivity and conductivity
    eps_r_d = eps_d.real
    eps_r_sc = eps_sc.real
    
    # Conductivity from imaginary part: σ = -ωε₀·ε''
    omega = 2 * np.pi * freq_hz
    sigma_d = -eps_d.imag * omega * EPS_0
    sigma_sc = -eps_sc.imag * omega * EPS_0
    
    return {
        'freq_hz': freq_hz,
        'layer_d': {
            'eps_r': eps_r_d,
            'sigma': sigma_d,
            'eps_complex': eps_d
        },
        'layer_sc': {
            'eps_r': eps_r_sc,
            'sigma': sigma_sc,
            'eps_complex': eps_sc
        },
        'd_sc_um': sc_params['d_um']
    }


def plot_christ_model(freq_ghz_min=0.01, freq_ghz_max=110, save_path=None):
    """
    Plot Christ et al. skin model properties vs frequency.
    
    Parameters:
    -----------
    freq_ghz_min : float
        Minimum frequency in GHz
    freq_ghz_max : float
        Maximum frequency in GHz
    save_path : str or Path, optional
        Path to save figure
    """
    freq_hz = np.logspace(np.log10(freq_ghz_min * 1e9), 
                         np.log10(freq_ghz_max * 1e9), 
                         1000)
    freq_ghz = freq_hz / 1e9
    
    # Get properties for different coverage levels
    results_mean = get_skin_properties(freq_hz, 'mean', 'thin')
    results_95pct = get_skin_properties(freq_hz, '95pct', 'thin')
    
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Plot 1: Layer D permittivity
    ax1 = axes[0, 0]
    ax1.loglog(freq_ghz, results_mean['layer_d']['eps_r'], 
               'b-', linewidth=2, label='Layer D (mean)', alpha=0.8)
    ax1.loglog(freq_ghz, results_95pct['layer_d']['eps_r'], 
               'b--', linewidth=2, label='Layer D (95% coverage)', alpha=0.8)
    ax1.set_xlabel('Frequency (GHz)', fontsize=12)
    ax1.set_ylabel('Relative Permittivity ε\'', fontsize=12)
    ax1.set_title('Layer D (Dermis) - Permittivity', fontsize=14)
    ax1.legend(fontsize=10)
    ax1.grid(True, which='both', alpha=0.3)
    ax1.set_xlim([freq_ghz_min, freq_ghz_max])
    
    # Plot 2: Layer D conductivity
    ax2 = axes[0, 1]
    ax2.loglog(freq_ghz, results_mean['layer_d']['sigma'], 
               'r-', linewidth=2, label='Layer D (mean)', alpha=0.8)
    ax2.loglog(freq_ghz, results_95pct['layer_d']['sigma'], 
               'r--', linewidth=2, label='Layer D (95% coverage)', alpha=0.8)
    ax2.set_xlabel('Frequency (GHz)', fontsize=12)
    ax2.set_ylabel('Conductivity σ (S/m)', fontsize=12)
    ax2.set_title('Layer D (Dermis) - Conductivity', fontsize=14)
    ax2.legend(fontsize=10)
    ax2.grid(True, which='both', alpha=0.3)
    ax2.set_xlim([freq_ghz_min, freq_ghz_max])
    
    # Plot 3: Layer SC permittivity
    ax3 = axes[1, 0]
    results_thin = get_skin_properties(freq_hz, 'mean', 'thin')
    results_thick1 = get_skin_properties(freq_hz, 'mean', 'thick1')
    ax3.loglog(freq_ghz, results_thin['layer_sc']['eps_r'], 
               'g-', linewidth=2, label='SC thin (20 μm)', alpha=0.8)
    ax3.loglog(freq_ghz, results_thick1['layer_sc']['eps_r'], 
               'g--', linewidth=2, label='SC thick1 (227 μm)', alpha=0.8)
    ax3.set_xlabel('Frequency (GHz)', fontsize=12)
    ax3.set_ylabel('Relative Permittivity ε\'', fontsize=12)
    ax3.set_title('Layer SC (Stratum Corneum) - Permittivity', fontsize=14)
    ax3.legend(fontsize=10)
    ax3.grid(True, which='both', alpha=0.3)
    ax3.set_xlim([freq_ghz_min, freq_ghz_max])
    
    # Plot 4: Layer SC conductivity (should be ~0)
    ax4 = axes[1, 1]
    ax4.loglog(freq_ghz, results_thin['layer_sc']['sigma'], 
               'm-', linewidth=2, label='SC thin (20 μm)', alpha=0.8)
    ax4.loglog(freq_ghz, results_thick1['layer_sc']['sigma'], 
               'm--', linewidth=2, label='SC thick1 (227 μm)', alpha=0.8)
    ax4.set_xlabel('Frequency (GHz)', fontsize=12)
    ax4.set_ylabel('Conductivity σ (S/m)', fontsize=12)
    ax4.set_title('Layer SC (Stratum Corneum) - Conductivity', fontsize=14)
    ax4.legend(fontsize=10)
    ax4.grid(True, which='both', alpha=0.3)
    ax4.set_xlim([freq_ghz_min, freq_ghz_max])
    ax4.set_ylim([1e-6, 1e-2])  # SC is lossless, so very small
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Plot saved to: {save_path}")
    
    plt.show()


def compare_with_nict(freq_ghz_min=0.01, freq_ghz_max=100):
    """
    Compare Christ model with NICT measurements.
    
    Note: This requires measurements-Skin.csv to be present.
    """
    try:
        import pandas as pd
        import re
        
        # Load NICT data
        csv_path = Path(__file__).parent.parent / "data" / "measurements-Skin.csv"
        df = pd.read_csv(csv_path)
        
        # Parse NICT frequency format
        def parse_val(s):
            return float(re.sub(r'\.E', 'E', str(s).strip()))
        
        nict_freq_hz = df['Frequency'].apply(parse_val).values
        nict_eps_r = df['Relative Permittivity'].apply(parse_val).values
        nict_sigma = df['Electric Conductivity'].apply(parse_val).values
        
        # Calculate Christ model at NICT frequencies
        christ_results = get_skin_properties(nict_freq_hz, 'mean', 'thin')
        
        # Plot comparison
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        freq_ghz = nict_freq_hz / 1e9
        
        # Permittivity comparison
        ax1 = axes[0]
        ax1.loglog(freq_ghz, nict_eps_r, 'b-', linewidth=2, 
                  label='NICT Measurements', alpha=0.8)
        ax1.loglog(freq_ghz, christ_results['layer_d']['eps_r'], 
                  'r--', linewidth=2, label='Christ Layer D (mean)', alpha=0.8)
        ax1.set_xlabel('Frequency (GHz)', fontsize=12)
        ax1.set_ylabel('Relative Permittivity ε\'', fontsize=12)
        ax1.set_title('Permittivity: NICT vs Christ Model', fontsize=14)
        ax1.legend(fontsize=11)
        ax1.grid(True, which='both', alpha=0.3)
        
        # Conductivity comparison
        ax2 = axes[1]
        ax2.loglog(freq_ghz, nict_sigma, 'b-', linewidth=2, 
                  label='NICT Measurements', alpha=0.8)
        ax2.loglog(freq_ghz, christ_results['layer_d']['sigma'], 
                  'r--', linewidth=2, label='Christ Layer D (mean)', alpha=0.8)
        ax2.set_xlabel('Frequency (GHz)', fontsize=12)
        ax2.set_ylabel('Conductivity σ (S/m)', fontsize=12)
        ax2.set_title('Conductivity: NICT vs Christ Model', fontsize=14)
        ax2.legend(fontsize=11)
        ax2.grid(True, which='both', alpha=0.3)
        
        plt.tight_layout()
        output_dir = Path(__file__).parent.parent / 'figures'
        output_dir.mkdir(exist_ok=True)
        plt.savefig(output_dir / 'christ_nict_comparison.png', dpi=150, bbox_inches='tight')
        print(f"Comparison plot saved to: {output_dir / 'christ_nict_comparison.png'}")
        plt.show()
        
    except ImportError:
        print("pandas required for NICT comparison")
    except FileNotFoundError:
        print("measurements-Skin.csv not found")


if __name__ == "__main__":
    # Example usage
    print("Christ et al. 2025 Skin Model Implementation")
    print("=" * 60)
    
    # Get properties at specific frequencies
    test_freqs = np.array([1e9, 10e9, 28e9, 60e9, 100e9])  # 1, 10, 28, 60, 100 GHz
    
    print("\nLayer D (Dermis) - Mean Coverage:")
    results = get_skin_properties(test_freqs, 'mean', 'thin')
    for i, f in enumerate(test_freqs):
        print(f"  {f/1e9:.1f} GHz: ε' = {results['layer_d']['eps_r'][i]:.2f}, "
              f"σ = {results['layer_d']['sigma'][i]:.2f} S/m")
    
    print("\nLayer D (Dermis) - 95% Coverage (conservative):")
    results_95 = get_skin_properties(test_freqs, '95pct', 'thin')
    for i, f in enumerate(test_freqs):
        print(f"  {f/1e9:.1f} GHz: ε' = {results_95['layer_d']['eps_r'][i]:.2f}, "
              f"σ = {results_95['layer_d']['sigma'][i]:.2f} S/m")
    
    # Plot model
    print("\nGenerating plots...")
    output_dir = Path(__file__).parent.parent / 'figures'
    output_dir.mkdir(exist_ok=True)
    plot_christ_model(save_path=str(output_dir / 'christ_skin_model.png'))
    
    # Compare with NICT if available
    print("\nComparing with NICT data...")
    compare_with_nict()
