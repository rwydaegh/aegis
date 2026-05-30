"""Issue #5: Q_abs(theta) = J^H M(theta) J factorization.

Per line 555-559:
  Q_abs(theta) = integral_Sigma G_tilde^H G_tilde dA = J^H M(theta) J

Per line 488: J in C^{M x N} is the BS path dictionary, where each path
n carries [a_n]_m steering, khat_n direction, psi_n polarization,
beta_n amplitude. J entries are independent of body pose theta.

But! The set of paths N traced from BS to 'body region' depends on the body
LOCATION. If the body moves (translates), the BS-to-body region paths change.
In particular, even for fixed location, the paths INCIDENT on the body depend
on the body shape, hence pose, in non-trivial ways.

Reading the construction more carefully:
- Sionna RT traces 'paths from BS to body region', not to specific triangles.
- These paths are then projected onto triangles via incidence-cosine and
  visibility filtering.
- The PATH DICTIONARY J is the set of paths to a fixed 'body region', presumably
  a small box around the body centroid. So pose changes don't change J.
- M(theta) encodes which paths land on which triangles, the polarization-Fresnel
  coupling, the cross-path visibility, etc.

Decomposition:
  Q_abs[i,j] = sum_n sum_n' [J]_{ni}^* [J]_{n'j} M[n,n']
  where M[n,n'] = sum_t S_t F_n^H F_n' Lambda_nn' (e_p,n . e_p,n') etc.,
  with the t-sum over visible triangles.

So M(theta) is body-pose-dependent (through triangles, normals, visibility).
J is body-LOCATION-dependent (through traced paths) but NOT joint-angle dependent.

Crucially:
- For closed-loop BS-side ascent on x at fixed pose, M is fixed and J^H J
  is fixed, so the structure is exploited.
- For pose change Delta theta (joint rotations), M changes but J stays the same.
- For body TRANSLATION (e.g., walking step), the BS-traced paths change too,
  so J changes.

The factorization separation is VALID for pose changes that don't move the body
centroid (the use case for closed-loop ascent on z, the latent pose).

But the paper text says line 562-563: 'The factorisation separates the per-slot
precoder cost from the per-pose body refresh.' This is correct only for
joint-angle changes that don't shift the body centroid significantly. For larger
moves (a walking step), J needs to be re-traced.

Robin's question: 'is this an issue for the closed-loop ascent, where pose moves
are small joint rotations not body translations?' Answer: NO, the factorization
is valid for the closed-loop optimization. The control variable is z (latent pose),
which only changes joint angles, not the body centroid. The body centroid is held
fixed by the per-Rx geometry. So J is fixed across the latent ascent.

Verdict: the factorization claim is OK for the use case, though the text could
be more precise about what 'per-pose' means (joint angles, not centroid).

#6 was already addressed.
"""
print("Issue #5: Q_abs(theta) = J^H M(theta) J factorization")
print()
print("Setup:")
print("- J encodes BS-to-body-REGION paths (function of body LOCATION).")
print("- M(theta) encodes triangle-pose details (function of joint angles).")
print()
print("For the closed-loop ascent on z (latent pose), only joint angles change,")
print("not body centroid. So J is fixed and the factorization is valid.")
print()
print("For a walking step (centroid translation), J needs to be re-traced.")
print("Paper's 'per-pose body refresh' text is correct for joint changes only,")
print("but could be more precise.")
print()
print("Verdict: factorization claim OK for the precoding use case.")
