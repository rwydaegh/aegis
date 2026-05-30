"""Verify the expansion of |1 - Gamma|.

Gamma = 2 sqrt(a a') / (a + a' - j(b' - b))
Let u = (a - a')/abar, v = (b - b')/abar where abar = (a+a')/2.
Then a = abar(1 + u/2), a' = abar(1 - u/2).
And b' - b = -v * abar.

Gamma = 2 abar sqrt((1+u/2)(1-u/2)) / (2 abar - j(-v abar))
      = sqrt(1 - u^2/4) / (1 + j v / 2)

So:
  Gamma = sqrt(1 - u^2/4) / (1 + j v/2)
        = sqrt(1 - u^2/4) (1 - j v/2) / (1 + v^2/4)

Expand to second order in u, v:
  sqrt(1 - u^2/4) ~ 1 - u^2/8
  1 / (1 + v^2/4) ~ 1 - v^2/4 + ...

So Re(Gamma) ~ (1 - u^2/8)(1 - v^2/4) ~ 1 - u^2/8 - v^2/4
   Im(Gamma) ~ -(v/2)(1 - u^2/8)(1 - v^2/4) ~ -v/2

|1 - Gamma|^2 = (1 - Re(Gamma))^2 + Im(Gamma)^2
             ~ (u^2/8 + v^2/4)^2 + v^2/4
             ~ v^2/4  [for small u, v]

So |1 - Gamma| ~ |v|/2 to leading order.

The supp bound says:
  |1 - Gamma| <= (1/2)(da/abar)^2 + (1/4)(db/abar)^2 = u^2/2 + v^2/4
  (with sign convention da = a - a', db = b - b' .. wait, supp uses
   dalpha = alpha_n - alpha_n', so u and dalpha/abar are interchangeable.)

The supp bound gives (u^2/2 + v^2/4), but the LEADING TERM in |1 - Gamma| is
|v|/2, NOT v^2/4. The supp bound is missing the O(|v|) term entirely!

This is a major algebraic error. The bound should be |v|/2 = (1/2)|db|/abar,
which for our case is (1/2)*5.29% = 2.65%. That MATCHES the numerical answer.
"""
import numpy as np

n = 4.49 - 1.79j
f = 28e9
c = 3e8
k0 = 2*np.pi*f/c

def alpha_beta(theta_deg):
    th = np.radians(theta_deg)
    mu = np.cos(th)
    xi = np.sqrt(n**2 - 1 + mu**2)
    if np.real(xi) < 0: xi = -xi
    alpha = -k0 * np.imag(xi)
    beta = k0 * np.real(xi)
    return alpha, beta

a, b = alpha_beta(0)
ap, bp = alpha_beta(85)
abar = 0.5 * (a + ap)
u = (a - ap) / abar  # dalpha / abar
v = (b - bp) / abar  # dbeta / abar
print(f"u = dalpha/abar = {u:.4f}")
print(f"v = dbeta/abar = {v:.4f}")
print(f"|v|/2 = {abs(v)/2:.4f} = {abs(v)/2*100:.4f}%  (leading-order |1-Gamma|)")

# Compute Gamma directly
Gamma = 2 * np.sqrt(a*ap) / (a + ap - 1j*(bp - b))
print(f"Direct Gamma = {Gamma}")
print(f"|1 - Gamma| = {abs(1 - Gamma)*100:.4f}%")

# Supp bound
sb = 0.5 * u**2 + 0.25 * v**2
print(f"Supp bound = (1/2)u^2 + (1/4)v^2 = {sb*100:.6f}%  (WRONG, omits O(|v|) term)")

# Correct leading-order bound
print(f"Correct leading-order |1-Gamma| ~ |v|/2 = {abs(v)/2*100:.4f}%")

# The actual second-order expansion: Re(Gamma) ~ 1 - u^2/8 - v^2/4
# Im(Gamma) ~ -v/2
# So |1 - Gamma|^2 = (u^2/8 + v^2/4)^2 + (v/2)^2
# To leading order, |1 - Gamma| ~ |v/2|
# The supp seems to expand only the SQUARED magnitude of the REAL part difference,
# missing the imaginary part entirely.

# Let me check: maybe the supp's expansion is for |1 - |Gamma||, not |1 - Gamma|?
print(f"\n|Gamma| = {abs(Gamma):.6f}, |1 - |Gamma|| = {abs(1 - abs(Gamma)):.6f} = {abs(1-abs(Gamma))*100:.4f}%")
print(f"This matches u^2/8 + v^2/4 = {u**2/8 + v**2/4:.6f}")
print("\nSo the supp bound is for |1 - |Gamma||, not |1 - Gamma|!")
print("That's a different quantity. The cross-term substitution error in")
print("the absorbed-power double sum requires |1 - Gamma|, not |1 - |Gamma||.")
