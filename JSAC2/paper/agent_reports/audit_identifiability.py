"""Issue #7: Identifiability proof in Appendix C.

Paper claim (line 727): 'The fit is non-trivial as long as K <= M and the
pilot SNR exceeds K sigma_K^{-2}.'

Supp/App C (line 1601-1607): 'The fit is non-trivial when SNR_ul >= K sigma_K^{-2}.'

Now sigma_K is the K-th singular value of Lambda_KH (M x T_vis matrix).

Lambda_KH entry: [a_n]_m * beta_n * S_t * K * g_UE^H psi * G(c_t, r_p) * exp(-j k_0 khat_n . c_t).

Units: [a_n]_m is dimensionless (steering element), beta_n carries amplitude (per-path),
S_t in m^2, K = jk_0 r_0 in 1/m (k_0 has units 1/m, r_0 dimensionless), g_UE^H psi
dimensionless (UE pattern * polarization), G in 1/m (Green's function 1/(4 pi R)
where R has units m, so 1/(4pi R) has units 1/m).

So Lambda_KH[m,t] units: (dimensionless) * (whatever beta) * (m^2) * (1/m) * (1/m) * (dimensionless)
                       = (m^2 / m^2) * beta = beta

If beta_n is unitless (a multiplicative path gain), then Lambda_KH is unitless.
If beta_n has units (e.g., V or sqrt(W)), then Lambda_KH has those units.

Per the paper: beta_n is calibrated against UL pilots, so it absorbs whatever
gives the channel its dimensional unit. The channel h has units of V/A or
similar (H = E/I). Probably treated as unitless complex gain in this paper.

Assume Lambda_KH is unitless. Then sigma_K is unitless. So sigma_K^{-2} is unitless.
SNR_ul is unitless. The bound SNR_ul >= K sigma_K^{-2} is dimensionally consistent.

But!! The proof says (line 1583-1589):
  Var(gamma_k_hat) = sigma_p^2 / (sigma_k^2 + lambda)
where sigma_p^2 is noise variance.

So Var(gamma_k) has units sigma_p^2/sigma_k^2 -- if sigma_p is noise amplitude and
sigma_k is from Lambda_KH amplitude, fine.

The 'per-mode SNR' is sigma_k^2 / sigma_p^2 (SNR for that mode). Threshold of unity
gives sigma_k^2 >= sigma_p^2. The paper writes:
'The fit is non-trivial when SNR_ul >= K sigma_K^{-2}'
Where SNR_ul = (signal power)/(noise power). If signal power = ||r||^2 and noise
power = M * sigma_p^2 (total noise across M antennas), then SNR_ul = ||r||^2/(M sigma_p^2).

The condition sigma_K^2 SNR_ul >> 1 (eq line 1589) means sigma_K^2 ||r||^2/(M sigma_p^2) >> 1,
which gives sigma_K^2 ||r||^2 >> M sigma_p^2. Hmm. The 'K' in the lower bound seems
ad hoc.

Actually I think the SNR_ul >= K sigma_K^{-2} is a heuristic combining (a) the per-mode
SNR threshold sigma_K^2 >= sigma_p^2 (i.e., per-mode SNR >= 1) and (b) a multi-mode
penalty K (multiple-comparison correction or trace-norm style).

It IS dimensionally consistent under the assumption that SNR_ul and sigma_K are
both dimensionless (relative amplitudes). The 'K' factor is heuristic.

The bigger issue Robin raised: 'sigma_K > 0 just means K <= rank(Lambda); it does
NOT mean the residual r lies in span(U_K)'.

Looking at line 1571-1574:
'unique whenever sigma_K > 0, i.e. whenever the truncated basis sits in the column
space of Lambda_KH. If the residual r lies entirely in span(U_K), the recovery is
exact. Otherwise, the orthogonal complement (I - U_K U_K^H) r is by construction
outside the body-side estimable subspace and is absorbed into the LOS / antenna
calibration beta in Section V.'

So the paper IS distinguishing 'identifiability of gamma_hat from r' (which only
needs sigma_K > 0) vs 'exact recovery of true gamma' (which needs r in span(U_K)).
The proposition claim 'exactly identifiable when r lies in span(U_K)' is technically
correct but maybe stated awkwardly. Identifiability of the LS solution is just
sigma_K > 0. Whether that LS solution recovers the TRUE gamma depends on whether
r is in span(U_K).

Actually reading more carefully: 'exactly identifiable when the residual lies in
span(U_K)'. The phrase 'exactly identifiable' is a non-standard usage. Identifiability
is usually about uniqueness of the parameter, which is given by sigma_K > 0. Exact
RECOVERY is different.

So the proof is loose but not wrong. The dimensional/algebraic content is OK.
"""
print("Issue #7: Identifiability bound dimensions")
print()
print("SNR_ul dimensionless, sigma_K dimensionless => SNR_ul >= K sigma_K^{-2} OK.")
print("The 'K' factor is heuristic (not a strict bound), but dimensionally OK.")
print()
print("Per-mode interpretation: Var(gamma_k) = sigma_p^2 / sigma_k^2 means")
print("per-mode SNR sigma_k^2 / sigma_p^2 >= 1 requires sigma_k^2 >= sigma_p^2.")
print()
print("The 'identifiability when r in span(U_K)' claim is technically about")
print("EXACT RECOVERY, not identifiability per se. Standard LS uniqueness needs")
print("only sigma_K > 0. The proposition phrasing is loose/non-standard.")
