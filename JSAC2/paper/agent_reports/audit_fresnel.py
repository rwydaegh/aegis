"""Verify pseudo-Brewster collapse claim.

JSAC paper claim (Sec III.B, line 460):
  For materials with |n| >= 2 + sqrt(3) ~ 3.73, TE and TM transmittances pinch
  together at all incidence angles below the critical angle.
  At 28 GHz both T_s, T_p lie within 5% of T0~0.54 across [0, 80] degrees.

Definitions (paper eq. Sab-single, line 449 and supp eq. S-fresnel-t):
  T_{s,n} = |t_{s,n}|^2 * Re(xi_n) / mu_n
  t_{s,n} = 2*mu_n / (mu_n + xi_n)
  t_{p,n} = 2*ntilde*mu_n / (ntilde^2 * mu_n + xi_n)
  xi_n = sqrt(ntilde^2 - 1 + mu_n^2)
  Re(xi_n) > 0
"""
import numpy as np

def fresnel_T(ntilde, theta_deg):
    theta = np.radians(theta_deg)
    mu = np.cos(theta)  # incidence cosine
    xi = np.sqrt(ntilde**2 - 1 + mu**2)
    # ensure Re(xi) > 0
    if np.any(np.real(xi) < 0):
        xi = -xi
    t_s = 2*mu / (mu + xi)
    t_p = 2*ntilde*mu / (ntilde**2 * mu + xi)
    # power transmittance: T = |t|^2 * Re(xi) / mu  (per paper)
    Ts = np.abs(t_s)**2 * np.real(xi) / mu
    Tp = np.abs(t_p)**2 * np.real(xi) / mu
    return Ts, Tp, t_s, t_p, xi

def report_band(ntilde, label, theta_max=80):
    thetas = np.linspace(0, theta_max, 1601)
    Ts, Tp, t_s, t_p, xi = fresnel_T(ntilde, thetas)
    # T0 at normal incidence from |n|? The paper claims T0~0.54
    Ts0, Tp0, *_ = fresnel_T(ntilde, 0.0)
    print(f"\n=== {label}: ntilde={ntilde}, |ntilde|={abs(ntilde):.3f} ===")
    print(f"  Normal incidence: Ts={Ts0:.4f}, Tp={Tp0:.4f}")
    # Pseudo-Brewster: find min of Tp
    idx = np.argmin(Tp)
    print(f"  Tp min = {Tp[idx]:.4f} at theta={thetas[idx]:.2f} deg "
          f"(Ts there = {Ts[idx]:.4f})")
    # Also find max of Ts
    idx_s = np.argmax(Ts)
    print(f"  Ts max = {Ts[idx_s]:.4f} at theta={thetas[idx_s]:.2f} deg")
    # Check the 5% claim: relative spread around mean
    # Define T0 = mean (Ts(0)+Tp(0))/2
    T0 = 0.5 * (Ts0 + Tp0)
    print(f"  T0 (mean at 0 deg) = {T0:.4f}")
    # Maximum relative deviation of Ts and Tp from T0
    dev_s = np.max(np.abs(Ts - T0)/T0)
    dev_p = np.max(np.abs(Tp - T0)/T0)
    print(f"  Max |Ts-T0|/T0 over [0,{theta_max}] = {100*dev_s:.2f}%")
    print(f"  Max |Tp-T0|/T0 over [0,{theta_max}] = {100*dev_p:.2f}%")
    # Also check a single scalar Tepskin = 0.54 (paper claim)
    Tepskin = 0.54
    dev_s_p = np.max(np.abs(Ts - Tepskin)/Tepskin)
    dev_p_p = np.max(np.abs(Tp - Tepskin)/Tepskin)
    print(f"  Max |Ts-0.54|/0.54 over [0,{theta_max}] = {100*dev_s_p:.2f}%")
    print(f"  Max |Tp-0.54|/0.54 over [0,{theta_max}] = {100*dev_p_p:.2f}%")
    # Also check the |T_s-T_p| (the actual pinching claim)
    pinch = np.max(np.abs(Ts - Tp))
    print(f"  Max |Ts - Tp| over [0,{theta_max}] = {pinch:.4f}")
    print(f"  Max |Ts - Tp|/T0 = {100*pinch/T0:.2f}%")
    # Print at a few specific angles
    for th in [0, 30, 45, 60, 70, 75, 80]:
        Tsi, Tpi, *_ = fresnel_T(ntilde, th)
        print(f"  theta={th:5.1f}: Ts={Tsi:.4f}, Tp={Tpi:.4f}, "
              f"diff%={100*(Tsi-Tpi)/T0:+.2f}")

# Skin at 28 GHz
n_28 = 4.49 - 1.79j
report_band(n_28, "Skin 28 GHz", theta_max=80)
report_band(n_28, "Skin 28 GHz [0,85]", theta_max=85)

# Skin at 60 GHz: |ntilde| ~ 3.68 per paper Table III
# IT'IS database typical: skin 60 GHz: eps_r ~ 7.98 - j*10.9 (4-cole-cole)
# ntilde = sqrt(eps_r) ~ 3.04 - j*1.79; |n|~3.53. Paper says 3.68 in Table.
# Use the paper's |n| ~ 3.68 by tweaking
# For numerical: simple model from monograph: ntilde at 60 GHz skin
# Actually let's just take |n| = 3.68 with similar Re/Im ratio
# The paper Table III says |n|=3.68 at 60 GHz, |n|=3.01 at 100 GHz
n_60 = 3.05 - 2.05j   # approx, |n|~3.67
n_100 = 2.5 - 1.7j    # approx, |n|~3.02
report_band(n_60, "Skin 60 GHz (approx)", theta_max=80)
report_band(n_100, "Skin 100 GHz (approx)", theta_max=80)

# Verify the |n| >= 2 + sqrt(3) condition
print(f"\n2 + sqrt(3) = {2 + np.sqrt(3):.6f}")
# Find at what |n| TE/TM differ less than X percent everywhere

# Specific check: Brewster minimum location
# For lossless n (real), Brewster angle: tan(theta_B) = n
# For |n|=3.73, theta_B = atan(3.73) ~ 75 deg
print(f"\nLossless Brewster angle for n=3.73: {np.degrees(np.arctan(3.73)):.2f} deg")
print(f"Lossless Brewster angle for |n|=4.83: {np.degrees(np.arctan(4.83)):.2f} deg")

# For lossy materials, pseudo-Brewster (min |t_p|^2): no clean formula
# but T_p hits a minimum. For n=4.83 nominally we can find numerically
