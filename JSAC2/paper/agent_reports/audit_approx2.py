"""Issue #4: Approximation 2 error budget.

Per supp S1 (eq. Gamma-norm):
  Gamma_nn' = 2 sqrt(alpha_n alpha_n') / [alpha_n + alpha_n' - j(beta_n' - beta_n)]
where alpha_n - j*beta_n = -j k_0 xi_n.

So:
  -j k_0 xi_n = alpha_n - j beta_n
  k_0 xi_n = j*alpha_n + beta_n
  k_0 (Re(xi_n) + j Im(xi_n)) = beta_n + j alpha_n
  Therefore:
    beta_n = k_0 Re(xi_n)
    alpha_n = k_0 Im(xi_n)

For skin n=4.49-1.79j:
  At theta=0, xi = n, so Re(xi)=4.49, Im(xi)=-1.79.
  But Im(xi) should be such that absorption: alpha > 0.
  xi = n means alpha = k_0 Im(n) = k_0 * (-1.79) -- negative!

There's a sign convention issue. The supp says "Re(xi_n) > 0", but Im(xi_n)
matters for alpha. With ntilde = 4.49 - 1.79j, Im(n) = -1.79, so Im(xi) ~ -1.79
at normal incidence. This gives alpha = k_0 * (-1.79), which is NEGATIVE
(amplification, not absorption). That violates "alpha_n > 0".

Looking again: in the supp at line 130-132:
  "alpha_n - j beta_n = -j k_0 xi_n"
So:
  -j k_0 xi = -j k_0 (Re + j Im) = -j k_0 Re + k_0 Im
  Real part of LHS = alpha. So alpha = k_0 Im(xi).
  Imag part of LHS = -beta. So -beta = -k_0 Re(xi), i.e., beta = k_0 Re(xi).

For ntilde = 4.49 - 1.79j (assuming convention exp(-j omega t)):
  xi at theta=0 is n = 4.49 - 1.79j.
  Im(xi) = -1.79. So alpha = k_0 * (-1.79) < 0. BAD.

This implies the convention must be ntilde = 4.49 + 1.79j (with the engineering
exp(j omega t) convention used in the paper, which is also why j=engineering j
per Eq. Etrans line 1448). Let me check.

Going back to the paper: "k_0 xi_n = beta_n - j alpha_n with alpha_n > 0"
(line 1449). So with engineering convention:
  k_0 xi_n = beta_n - j alpha_n
  Re(k_0 xi_n) = beta_n
  Im(k_0 xi_n) = -alpha_n
  So alpha_n = -k_0 Im(xi_n) > 0 means Im(xi_n) < 0.
For ntilde = 4.49 - 1.79j with Im(n) < 0, at theta=0: Im(xi) = Im(n) = -1.79 < 0.
So alpha = -k_0 * (-1.79) = +k_0 * 1.79 > 0.

So the conventions are consistent. Use:
  alpha_n = -k_0 Im(xi_n)
  beta_n = k_0 Re(xi_n)
where xi_n has Im < 0 for absorbing media in this convention.

Now let me sweep theta over [0, 85] for skin at 28 GHz and compute Gamma.
"""
import numpy as np

n = 4.49 - 1.79j
f = 28e9  # Hz
c = 3e8
k0 = 2*np.pi*f/c

def alpha_beta(theta_deg):
    th = np.radians(theta_deg)
    mu = np.cos(th)
    xi = np.sqrt(n**2 - 1 + mu**2)
    if np.real(xi) < 0: xi = -xi
    # ensure Im(xi) < 0 (absorbing convention)
    # if Im(xi) > 0, take complex conjugate? actually sqrt should preserve sign
    alpha = -k0 * np.imag(xi)
    beta = k0 * np.real(xi)
    return alpha, beta, xi

# Verify alpha > 0 across angles
for th in [0, 30, 45, 60, 75, 85]:
    a, b, xi = alpha_beta(th)
    print(f"theta={th:5.1f}: xi={xi}, alpha={a:.2f} m^-1, beta={b:.2f} m^-1")

# Check xi at theta=0
a0, b0, xi0 = alpha_beta(0)
print(f"\nAt theta=0: |xi|={abs(xi0):.4f}, ratio to |n|={abs(xi0)/abs(n):.4f}")

# Lambda_nn' = 1 / (alpha_n + alpha_n' - j(beta_n' - beta_n))
# Gamma_nn' = 2 sqrt(alpha_n alpha_n') / (alpha_n + alpha_n' - j(beta_n' - beta_n))
def Gamma(tn, tnp):
    a, b, _ = alpha_beta(tn)
    ap, bp, _ = alpha_beta(tnp)
    num = 2 * np.sqrt(a * ap)
    den = a + ap - 1j * (bp - b)
    return num / den

# Sweep
N = 86
thetas = np.linspace(0, 85, N)
err_max = 0
err_mean_sum = 0
worst_pair = None
all_errs = []
for tn in thetas:
    for tnp in thetas:
        g = Gamma(tn, tnp)
        err = abs(1 - g)
        all_errs.append(err)
        if err > err_max:
            err_max = err
            worst_pair = (tn, tnp)
        err_mean_sum += err
err_mean = err_mean_sum / N**2

print(f"\n|1 - Gamma_nn'| sweep over [0, 85]^2:")
print(f"  Max: {err_max*100:.4f}% at pair {worst_pair}")
print(f"  Mean: {err_mean*100:.4f}%")
print(f"  Paper claims: <= 0.44% with mean 0.17%")

# What about the Re part vs Im part?
print(f"\nDetailed at the worst pair:")
tn, tnp = worst_pair
a, b, _ = alpha_beta(tn)
ap, bp, _ = alpha_beta(tnp)
g = Gamma(tn, tnp)
print(f"  alpha_n={a:.4f}, alpha_n'={ap:.4f}, dalpha={a-ap:.4f}")
print(f"  beta_n={b:.4f}, beta_n'={bp:.4f}, dbeta={b-bp:.4f}")
print(f"  Gamma = {g}, |1-G| = {abs(1-g):.6f}")

# Compute the bound estimate from supp:
# |1 - Gamma| <= (1/2)(dalpha/alpha_bar)^2 + (1/4)(dbeta/alpha_bar)^2
abar = 0.5 * (a + ap)
da_rel2 = ((a - ap) / abar)**2
db_rel2 = ((b - bp) / abar)**2
bound = 0.5 * da_rel2 + 0.25 * db_rel2
print(f"  Supp bound = (1/2)(dalpha/abar)^2 + (1/4)(dbeta/abar)^2")
print(f"            = (1/2)*{da_rel2:.4f} + (1/4)*{db_rel2:.4f}")
print(f"            = {bound:.6f} = {bound*100:.4f}%")
print(f"  Actual |1-G|: {abs(1-g)*100:.4f}%")
print(f"  Bound is {'TIGHT' if bound > abs(1-g) else 'LOOSE/WRONG'}")

# Also compute the DOMINANT term: dbeta/abar
print(f"\nKey ratio analysis:")
print(f"  alpha_bar = {abar:.2f} m^-1")
print(f"  |dalpha|/abar = {abs(a-ap)/abar*100:.2f}%")
print(f"  |dbeta|/abar = {abs(b-bp)/abar*100:.2f}%")
print(f"  Note: dbeta/abar can be much larger than dalpha/abar because")
print(f"  beta = k0 Re(xi) ~ 4.5 k0 vs alpha = -k0 Im(xi) ~ 1.8 k0")
print(f"  So Re(xi) varies by ~ 2% (per supp), but |dbeta|/abar = ")
print(f"   |k0 d(Re xi)| / (k0 |Im xi|) = |d(Re xi)| / |Im xi|")
print(f"   ~ 2% * Re(xi)/|Im(xi)| = 2% * 4.49/1.79 ~ 5%")

# Verify: Im(xi) at theta_n vs theta_n' = 85 deg
for th in [0, 50, 85]:
    a, b, xi = alpha_beta(th)
    print(f"   theta={th}: Re(xi)={np.real(xi):.4f}, Im(xi)={np.imag(xi):.4f}")
