"""Does the imaginary part of Gamma matter for absorbed power?

The absorbed power double sum is:
  P_abs ~ Re sum_{n,n'} t_n t_n'^* psi_n psi_n'^* (e_n . e_n'^*) Lambda_nn'

With Approx 2: Lambda_nn' = sqrt(Lambda_nn Lambda_n'n') Gamma_nn'
            ~ sqrt(Lambda_nn Lambda_n'n') (replacing Gamma by 1)

The substitution error in the cross-term magnitude is
  |Lambda_nn' - sqrt(Lambda_nn Lambda_n'n')| = sqrt(Lambda_nn Lambda_n'n') |1 - Gamma|

And the substitution error in P_abs picks up this factor times Re-of-other-terms.

Now if the cross-term ALSO carries the path phase factor exp(-j k_0 (k_n - k_n').r),
the imaginary part of Gamma can be REAL-PROJECTED via the phase, and the *full*
contribution can include a part where Im(Gamma) is upgraded to a real magnitude
contribution.

Actually let me re-think. In the squared-norm form S_ab = ||G x||^2:
  Each term in the double sum is (G column n)^H (G column n') * x_n x_n'^*.
  When we set Gamma = 1, we're saying Lambda_nn' = sqrt(Lambda_nn Lambda_n'n').
  The error in P_abs is sum over n,n' of |Lambda_nn'| |1-Gamma| times other.

The relevant bound is |1 - Gamma| in COMPLEX magnitude, because Gamma multiplies
a complex coefficient that gets summed. The Im part can constructively or
destructively interfere with the real coefficients of the cross-term.

So |1 - Gamma| ~ 2.65% is the worst-case error in cross-term magnitude.
The paper claims 0.44%. So the actual error is 6x larger than claimed.

But! It's still small (2.65% << many other modeling errors). So the qualitative
conclusion is right. The proof is just wrong.

Let me do one more sanity check: |1 - |Gamma||^2 vs |1 - Gamma|^2.
|1 - Gamma|^2 = (1 - Re Gamma)^2 + (Im Gamma)^2
|1 - |Gamma||^2 = (1 - |Gamma|)^2

For Gamma = a - j*b with a ~ 1 - eps, b small:
|Gamma| = sqrt(a^2 + b^2) ~ sqrt((1-eps)^2 + b^2) ~ 1 - eps + b^2/2
1 - |Gamma| ~ eps - b^2/2  (small)
|1 - Gamma|^2 = eps^2 + b^2

So when b dominates (b > eps), |1 - Gamma| ~ b ~ |Im(Gamma)|, but
|1 - |Gamma|| ~ eps which can be much smaller. The supp bound is on the latter.

This is a real error in the proof. Whether it matters for the paper's main
conclusions depends on whether 2.65% (vs 0.44%) is within the calibration
headroom they invoke.

Let me sweep more frequencies to see how this scales.
"""
import numpy as np

def alpha_beta(n_complex, theta_deg, k0):
    th = np.radians(theta_deg)
    mu = np.cos(th)
    xi = np.sqrt(n_complex**2 - 1 + mu**2)
    if np.real(xi) < 0: xi = -xi
    alpha = -k0 * np.imag(xi)
    beta = k0 * np.real(xi)
    return alpha, beta

c = 3e8

def sweep(n_complex, freq, label):
    k0 = 2*np.pi*freq/c
    N = 86
    thetas = np.linspace(0, 85, N)
    err_max = 0
    err_mean = 0
    err_max_abs_form = 0  # |1 - |Gamma||
    for tn in thetas:
        for tnp in thetas:
            a, b = alpha_beta(n_complex, tn, k0)
            ap, bp = alpha_beta(n_complex, tnp, k0)
            G = 2 * np.sqrt(a*ap) / (a + ap - 1j*(bp - b))
            err = abs(1 - G)
            err_abs = abs(1 - abs(G))
            err_max = max(err_max, err)
            err_max_abs_form = max(err_max_abs_form, err_abs)
            err_mean += err
    err_mean /= N**2
    print(f"{label}: |1-Gamma| max={err_max*100:.3f}%, mean={err_mean*100:.3f}%, "
          f"|1-|Gamma|| max={err_max_abs_form*100:.4f}%")

# Skin at various frequencies (rough Cole-Cole-derived ntilde)
sweep(4.49 - 1.79j, 28e9, "Skin 28 GHz, |n|=4.83")
# Skin 60 GHz: per IT'IS, eps_r ~ 8 - 11j, ntilde ~ 3.05 - 1.80j, |n| ~ 3.55
sweep(3.05 - 1.80j, 60e9, "Skin 60 GHz, |n|=3.54")
# Skin 100 GHz: per IT'IS, eps_r ~ 5.6 - 6j, ntilde ~ 2.4 - 1.25j, |n| ~ 2.70
sweep(2.4 - 1.25j, 100e9, "Skin 100 GHz, |n|=2.71")

# What if we use the (smaller) |1-|Gamma|| bound but the cross-term enters via
# the squared norm? The squared norm error involves |Gamma|^2 which is closer
# to 1 (so |1 - |Gamma||).
# But the cross-term in the double-sum picks up Gamma (complex) * other_complex,
# and when summed, the imaginary parts could in principle cancel.
# Let me check by considering a worst-case set of N paths.

# Take N=10 paths with theta uniform in [10, 85]
np.random.seed(42)
N_paths = 10
thetas = np.random.uniform(10, 85, N_paths)
n_complex = 4.49 - 1.79j
k0 = 2*np.pi*28e9/c
alphas = np.array([alpha_beta(n_complex, t, k0)[0] for t in thetas])
betas = np.array([alpha_beta(n_complex, t, k0)[1] for t in thetas])

# True Lambda matrix
Lambda_true = np.zeros((N_paths, N_paths), dtype=complex)
Lambda_approx = np.zeros((N_paths, N_paths), dtype=complex)
for i in range(N_paths):
    for j in range(N_paths):
        Lambda_true[i,j] = 1 / (alphas[i] + alphas[j] - 1j*(betas[j] - betas[i]))
        Lambda_approx[i,j] = np.sqrt(Lambda_true[i,i] * Lambda_true[j,j])

# Random complex coefficients (proxies for t_n psi_n a_n^H x)
coeffs = (np.random.randn(N_paths) + 1j*np.random.randn(N_paths))

# True absorbed power: Re sum_ij coeffs[i] coeffs[j].conj() * Lambda_true[i,j]
P_true = np.real(coeffs @ Lambda_true @ coeffs.conj())
P_approx = np.real(coeffs @ Lambda_approx @ coeffs.conj())
print(f"\nMonte-Carlo (N={N_paths} paths, random coefficients):")
print(f"  P_true = {P_true:.6e}")
print(f"  P_approx = {P_approx:.6e}")
print(f"  Relative error: {abs(P_true - P_approx)/abs(P_true)*100:.4f}%")

# Average over multiple random draws
errs = []
for trial in range(1000):
    np.random.seed(trial)
    thetas = np.random.uniform(0, 85, N_paths)
    alphas = np.array([alpha_beta(n_complex, t, k0)[0] for t in thetas])
    betas = np.array([alpha_beta(n_complex, t, k0)[1] for t in thetas])
    Lambda_true = np.zeros((N_paths, N_paths), dtype=complex)
    Lambda_approx = np.zeros((N_paths, N_paths), dtype=complex)
    for i in range(N_paths):
        for j in range(N_paths):
            Lambda_true[i,j] = 1 / (alphas[i] + alphas[j] - 1j*(betas[j] - betas[i]))
            Lambda_approx[i,j] = np.sqrt(Lambda_true[i,i] * Lambda_true[j,j])
    coeffs = (np.random.randn(N_paths) + 1j*np.random.randn(N_paths))
    P_true = np.real(coeffs @ Lambda_true @ coeffs.conj())
    P_approx = np.real(coeffs @ Lambda_approx @ coeffs.conj())
    errs.append(abs(P_true - P_approx)/abs(P_true))
errs = np.array(errs)
print(f"\nMonte-Carlo over 1000 trials (random angles, random coeffs):")
print(f"  Mean rel error: {np.mean(errs)*100:.3f}%")
print(f"  Max rel error: {np.max(errs)*100:.3f}%")
print(f"  90th percentile: {np.percentile(errs, 90)*100:.3f}%")
