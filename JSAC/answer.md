  1. The SAR matrix, precisely

  All five published papers share one object. For an N-antenna transmitter emitting signal vector x ∈ ℂ^N, the SAR at a tissue
  point p (or averaged over a volume V around p) is a quadratic form:

  $$\text{SAR}(\mathbf{x}) = \mathbf{x}^H \mathbf{R}(\mathbf{p}) ,\mathbf{x}$$

  where R(p) is an N×N Hermitian PSD matrix. Concretely (Castellanos eq. 1-3, Ying 2015 eq. 8):

  $$[\mathbf{R}(\mathbf{p})]_{ij} ;=;
  \frac{\sigma(\mathbf{p})}{2\rho(\mathbf{p})};\mathbf{E}_i^*(\mathbf{p})\cdot\mathbf{E}_j(\mathbf{p})$$

  — σ and ρ are tissue conductivity and density at p, and E_i(p) is the E-field at p when only antenna i is excited with unit
  input and the rest are terminated. So R just bookkeeps "if I drive antenna i and antenna j with unit amplitudes, how much
  their fields constructively deposit heat at p." Integrate it over a volume → volume-averaged R_V. AEGIS's exposure operator Q
  is the body-surface analog of this matrix — same object, same physics, derived in closed form instead of CST-fitted.

  What R depends on: antenna geometry (fixed by the device), tissue properties (effectively fixed), and the body position/pose
  (varies second-to-second).

  That last bit is the whole game. Every previous paper freezes R offline. You have the tools to update it online.

  2. What the prior art actually does, in math

  Hochwald 2014 — pick L canonical gestures (head-right, head-left, pocket, table, hand, etc.), compute R_l for each with CST,
  then use the worst:

  $$\mathbf{S} ;=; \arg\max_{l=1,\dots,L}; \text{tr}(\mathbf{R}_l,\mathbf{Q}), \quad
  \mathbf{Q}=\mathbb{E}[\mathbf{x}\mathbf{x}^H]$$

  Everything downstream uses this single S. Very conservative.

  Ying 2015 — solve, with that worst-case S fixed:

  $$\max_\mathbf{F};\log!\bigl|\mathbf{I}+\tfrac{1}{\sigma^2}\mathbf{H}\mathbf{F}\mathbf{F}^H\mathbf{H}^H\bigr|;\text{s.t.};\tex
  t{tr}(\mathbf{F}^H\mathbf{S}\mathbf{F})\le Q_0,;\text{tr}(\mathbf{F}^H\mathbf{F})\le P$$

  Solution: modified water-filling over the "effective channel" H(λS+νI)^(-1/2). Both constraints active → Lagrangian (λ, ν).
  This is their headline result.

  Ying 2017 — K users, each with its own {R_k,i} and power Q_k,i. Iterative per-user water-filling. ~3 dB over power-backoff.

  Castellanos 2020 — provides closed-form-ish R(p) at any surface point at 28 GHz for a ULA above a sphere, so you don't need a
  new CST run per p. Same worst-case philosophy downstream.

  Zhou 2026 — instead of the instantaneous constraint, integrates Pennes' bioheat equation over 6-minute windows to get a
  thermal-temperature constraint; uses Lyapunov / virtual-queue to let per-slot SAR exceed the ICNIRP peak as long as the
  time-averaged thermal rise stays safe. Single head-on-sphere, no DT.

  The universal assumption: the body state (and hence R) is either frozen at one worst configuration or known exactly. Nobody
  treats it as a random variable whose distribution is narrowed by sensors. That is the hole.

  3. Bayesian-risk / CVaR, without handwaving

  You have a library of L gesture configurations, each with a precomputed R_l. Call the true (unknown) gesture θ ∈ {1, ..., L}.
  The classifier produces a posterior p = (p_1, ..., p_L), where p_l = Pr(θ=l | sensor readings).

  Define the random variable V = tr(R(θ) Q) — this is "what SAR you'll actually cause."

  Four ways to constrain V ≤ limit. All are real; they differ in how conservative/risk-tolerant:

  ┌────────────────────┬─────────────────────────┬─────────────────────────────────────────────────────────────────────────┐
  │     Constraint     │         Formula         │                               In English                                │
  ├────────────────────┼─────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Worst-case         │ max_l tr(R_l Q) ≤ limit │ "Assume the user is in whichever gesture is worst for me right now." No │
  │ (Hochwald)         │                         │  posterior used.                                                        │
  ├────────────────────┼─────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Expected value     │ Σ_l p_l · tr(R_l Q) ≤   │ "On average it's fine." Can violate on bad realizations. Unsafe.        │
  │                    │ limit                   │                                                                         │
  ├────────────────────┼─────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ Chance constraint  │ Pr(V ≤ limit) ≥ 1-α     │ "Violate no more than fraction α of the time." Intuitive but non-convex │
  │                    │                         │  in Q.                                                                  │
  ├────────────────────┼─────────────────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ CVaR at level α    │ CVaR_α(V) ≤ limit       │ "The average of the worst α fraction of outcomes stays under the        │
  │                    │                         │ limit." Convex in Q.                                                    │
  └────────────────────┴─────────────────────────┴─────────────────────────────────────────────────────────────────────────┘

  CVaR_α — "Conditional Value-at-Risk," aka "Expected Shortfall." Definition:

  $$\text{CVaR}\alpha(V) ;=; \mathbb{E}[,V ,\big|, V \ge \text{VaR}\alpha(V),]$$

  where VaR_α is the α-quantile (the value such that V exceeds it with probability α).

  Concretely, when the posterior is discrete over L gestures: sort the values v_l = tr(R_l Q) from largest to smallest, take the
   top α fraction (weighted by p_l), average them. That's CVaR_α(V).

  Why CVaR is the right tool here:

  1. It's convex in Q, so you keep the QCQP structure of your ECBF. Solvable in the same framework you already have.
  2. It dominates the chance constraint: CVaR_α(V) ≤ limit ⇒ Pr(V > limit) ≤ α. So it's a safe convex surrogate for "be
  compliant with prob ≥ 1-α."
  3. It interpolates cleanly: α → 0 recovers Hochwald's worst-case; α → 1 recovers the expected-value constraint; α ~ 0.05 is
  the sweet spot used in financial risk management.
  4. Rockafellar-Uryasev trick: CVaR_α(V) = min_t { t + (1/α) E[(V-t)_+] }. This turns it into an easy jointly-convex problem in
   (Q, t).

  What changes in the optimization. The Ying 2015 problem becomes:

  $$\max_\mathbf{F};\log|\mathbf{I}+\tfrac{1}{\sigma^2}\mathbf{H}\mathbf{F}\mathbf{F}^H\mathbf{H}^H|;;\text{s.t.};;\text{CVaR}_\
  alpha^{\mathbf{p}}!\bigl[\text{tr}(\mathbf{R}(\theta)\mathbf{F}\mathbf{F}^H)\bigr]\le
  Q_0,;;\text{tr}(\mathbf{F}^H\mathbf{F})\le P$$

  In discrete form this unpacks into (L+1) linear-quadratic constraints. Still tractable, still has closed-form dual structure à
   la Ying, with the extra twist that the active constraints depend on which gestures are "tail" gestures under the current
  posterior.

  The payoff: when the posterior is peaked (the sensors are confident the user is in one gesture), CVaR is close to tr(R of that
   gesture · Q), so you get nearly the full capacity of "oracle knows the gesture." When the posterior is flat, CVaR approaches
  Hochwald's worst-case. You degrade gracefully to the old paper when sensing tells you nothing.

  4. Sensors, simulated concretely

  Your instinct — "do I simulate an accelerometer?" — is exactly where most robustness papers go wrong. The answer is no, you
  don't simulate sensor physics. You simulate the output of the classifier.

  Here's the pipeline:

  1. Ground truth: at simulation time t, the true gesture is θ_t* ∈ {1, ..., L}. You drive this from your animation / pose
  sequence (e.g., user walks for 10 s, puts phone to right ear for 5 s, slips it in pocket for 30 s).
  2. Classifier posterior model: you assume a classifier exists (Apple ships one; there's a pile of prior work on IMU+prox+grip
  → hand-state classification). You don't implement it. You model its output distribution with a confusion model:
    - A confusion matrix C where C[l̂, l*] = Pr(classifier peaks on l̂ | truth is l*).
    - Or, more realistically, a Dirichlet-output model: given truth l*, draw pt ~ Dir(κ · c{l*}) where c_{l*} is a prior profile
   (mass concentrated on l*, spread on confusable classes — e.g., "hand" and "pocket" often confuse).
  3. Calibration knob: vary κ / the off-diagonal mass of C to sweep sensor quality. Run the whole evaluation at e.g. κ ∈ {10,
  100, ∞} to show sensitivity. κ=∞ = oracle (perfect gesture knowledge); Hochwald is effectively κ=0 (no sensor, uniform prior).
  4. Feed p_t to CVaR-ECBF at each time step, solve, apply, next step.

  The entire sensing component is ~30 lines of numpy: draw l* from your pose sequence, draw p_t from a Dirichlet conditioned on
  l*, hand p_t to the solver. No accelerometer model, no Kalman filter, no perception network. If a reviewer asks "where does
  the classifier come from?" you cite one of ~50 papers on IMU/grip/prox hand-state classification and point to the Apple
  off-body detector as the deployed version.

  If you want one figure of flavor: pick a real IMU-trace dataset (there are public ones for phone usage), train a tiny
  classifier, show that the confusion matrix you assume in the Dirichlet model is consistent with the real one. That's maybe one
   afternoon of PyTorch and one figure. Optional.

  5. The paper in one paragraph

  Every exposure-constrained beamforming paper so far precomputes a library of SAR matrices {R_l} for canonical body
  configurations and enforces a static worst-case max_l tr(R_l FF^H) ≤ limit. This is conservative because the user is in one
  gesture at any moment, and cheap on-device sensors already present on every smartphone (proximity, grip, IMU) produce a
  posterior over that gesture. We propose twin-in-the-loop beamforming: a body digital twin maintained by the device updates a
  distribution p_t over a dense pose library, and the precoder is re-solved at coherence-block cadence under a CVaR_α exposure
  constraint evaluated against p_t. Using AEGIS's closed-form mmWave exposure operator Q on anatomically realistic phantoms
  (instead of the spherical head + empirical fits in Castellanos 2020), we recover the full Ying 2015 water-filling structure
  with CVaR duals, extend the multi-user MAC version of Ying 2017, and show that on 3GPP UMi channels, at compliance probability
   ≥ 0.99, the body-DT recovers X dB of capacity relative to worst-case Hochwald and Y dB relative to Zhou 2026's
  thermal-Lyapunov baseline. The closed loop is UL-first (matching the deployed regime the iPhone-12/ANFR saga lives in) with an
   optional DL near-BS section. "Closed-loop" in Ying 2015 meant CSI feedback; here it means body state feedback through the
  exposure operator itself.

  Now your checks

  1. Does the CVaR-on-posterior idea land now, or is there a specific step that's still fuzzy?
  2. The "simulate classifier output, not sensor physics" escape — are you comfortable with that being defensible, or do you
  want the one-afternoon empirical confusion-matrix figure as extra armor?
  3. On L: you said "tons of poses." Roughly how many can SMPL-X + AEGIS give us at reasonable cost for precomputed R_l? The
  CVaR story gets more interesting as L grows (more gestures → more room for a peaked posterior to save you dB).
