"""How tight does the angle range need to be for the 5% claim?

The pseudo-Brewster collapse claim is DRAMATICALLY false at 80 degrees.
Let me find the angle range where the pinching is within 5%.
"""
import numpy as np

n = 4.49 - 1.79j

def T_at(th_deg):
    th = np.radians(th_deg)
    mu = np.cos(th)
    xi = np.sqrt(n**2 - 1 + mu**2)
    if np.real(xi) < 0: xi = -xi
    t_s = 2*mu / (mu + xi)
    t_p = 2*n*mu / (n**2 * mu + xi)
    T_s = abs(t_s)**2 * np.real(xi)/mu
    T_p = abs(t_p)**2 * np.real(xi)/mu
    return T_s, T_p

# Finest sweep
thetas = np.linspace(0, 80, 8001)
T_s_arr = []
T_p_arr = []
for t in thetas:
    Ts, Tp = T_at(t)
    T_s_arr.append(Ts)
    T_p_arr.append(Tp)
T_s_arr = np.array(T_s_arr)
T_p_arr = np.array(T_p_arr)
T0 = 0.54

# At what angle does |T_s - T0|/T0 first exceed 5%?
err_s = np.abs(T_s_arr - T0)/T0
err_p = np.abs(T_p_arr - T0)/T0
err_diff = np.abs(T_s_arr - T_p_arr)/T0
ix5_s = np.argmax(err_s > 0.05)
ix5_p = np.argmax(err_p > 0.05)
ix5_diff = np.argmax(err_diff > 0.05)
print(f"|Ts - 0.54|/0.54 first exceeds 5% at theta={thetas[ix5_s]:.2f}")
print(f"|Tp - 0.54|/0.54 first exceeds 5% at theta={thetas[ix5_p]:.2f}")
print(f"|Ts - Tp|/0.54 first exceeds 5% at theta={thetas[ix5_diff]:.2f}")

# At what angles do the absolute T_s-T_p stay within 5%?
ix5_diff_abs = np.argmax(err_diff > 0.05)
print(f"\nMax angle where ALL three (Ts, Tp, |Ts-Tp|) within 5% of T0: "
      f"min({thetas[ix5_s]:.2f}, {thetas[ix5_p]:.2f}, {thetas[ix5_diff]:.2f}) = "
      f"{min(thetas[ix5_s], thetas[ix5_p], thetas[ix5_diff]):.2f} deg")

# What if we consider only T_p (which goes UP, so a different reference)
# Or what about a weighted body-average over Lambertian distribution?
# Lambertian weighting: integrate cos(theta) sin(theta) dtheta dphi
# For a flat body surface seen from random hemisphere directions,
# the angular weight is cos(theta)*sin(theta) (incidence-cosine times solid angle)
weights_lambertian = np.cos(np.radians(thetas)) * np.sin(np.radians(thetas))
mean_Ts = np.trapezoid(T_s_arr * weights_lambertian, thetas) / np.trapezoid(weights_lambertian, thetas)
mean_Tp = np.trapezoid(T_p_arr * weights_lambertian, thetas) / np.trapezoid(weights_lambertian, thetas)
print(f"\nLambertian-weighted means (over incidence cosine): "
      f"<Ts>={mean_Ts:.4f}, <Tp>={mean_Tp:.4f}")

# Plain angular average (uniform)
mean_Ts_unif = np.mean(T_s_arr)
mean_Tp_unif = np.mean(T_p_arr)
print(f"Uniform angular means: <Ts>={mean_Ts_unif:.4f}, <Tp>={mean_Tp_unif:.4f}")

# Just (Ts + Tp)/2 at each angle
T_avg = 0.5 * (T_s_arr + T_p_arr)
print(f"\nMid (Ts+Tp)/2 at various angles:")
for th in [0, 30, 45, 60, 70, 75, 80]:
    Ts, Tp = T_at(th)
    print(f"  theta={th}: Ts={Ts:.4f}, Tp={Tp:.4f}, "
          f"avg={(Ts+Tp)/2:.4f}, diff={abs(Ts-Tp):.4f}")

# At what angle is the average closest to constant?
ix_min = np.argmin(np.abs(T_avg - T_avg[0]))  # always 0
# Actually let me see how T_avg deviates from T0=0.54
err_avg = np.abs(T_avg - 0.54)/0.54
print(f"\n(Ts+Tp)/2 average deviation from 0.54:")
print(f"  at 0 deg: {100*err_avg[0]:.2f}%")
print(f"  at 30: {100*err_avg[3000]:.2f}%")
print(f"  at 45: {100*err_avg[4500]:.2f}%")
print(f"  at 60: {100*err_avg[6000]:.2f}%")
print(f"  at 75: {100*err_avg[7500]:.2f}%")
print(f"  at 80: {100*err_avg[8000]:.2f}%")
ix5_avg = np.argmax(err_avg > 0.05)
print(f"  first exceeds 5% at: theta={thetas[ix5_avg]:.2f}")
