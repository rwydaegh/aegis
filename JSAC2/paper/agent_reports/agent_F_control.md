# Agent F report: Section VI style pass

Scope: `JSAC2/paper/jsac2_v3.tex` Section VI (`\section{Pose-differentiable rate
and human-in-the-loop control}`), three subsections.

## Summary of changes

1. **Subsection headings: dropped leading "The"** (style guide C11).
   - "The cascaded SINR and the rate" -> "Cascaded SINR and rate" (also
     dropped the second "the").
   - "Pose-space restriction and the latent gradient" -> "Pose-space
     restriction and latent gradient".
   - "The human-in-the-loop control law" -> "Human-in-the-loop control law".

2. **Cascaded SINR and rate subsection.** Subject-verb-rest restructuring.
   Killed "the Shannon expression" filler; killed "with magnitude controlled
   by" (mild anthropomorphism); killed colon-then-clause. `\cref{eq:cascaded}`
   -> `~\eqref{eq:cascaded}` (eqref per latex_rules 31). Tightened the
   gradient sentence.

3. **Pose-space restriction subsection.** Killed "for our purposes" (filler).
   Replaced the parenthetical "(joints outside their range of motion,
   incompatible torso-limb couplings)" with prose to avoid the parenthetical
   rule-of-three. "VAE" expanded to "variational autoencoder" on first use
   in body prose. Replaced semicolons with periods. Killed "We therefore"
   and "Any latent" -> "Every latent". Split a long compound sentence into
   subject-verb-rest pieces.

4. **Cascaded autodiff chain paragraph.** Removed semicolons in the
   "Kirchhoff render ... SMPL-X is ... VPoser decoder is" parallel
   construction and replaced with periods and a coordinating "and"
   (no rule-of-three triplet). Reframed "We compute" as "The gradient is
   computed" to avoid the bare we-verb. Replaced
   "requiring one forward pass and one backward pass per iteration (no
   finite-difference oracle on the underlying physics)" with a single
   declarative without a parenthetical interjection.

5. **Mahalanobis comfort claim (per first-reading critique).** Softened
   the load-bearing claim. New opening of the comfort paragraph:
   > We identify the comfort region with the Mahalanobis ball
   > ||z|| <= rho_nat in VPoser latent space~\cite{Pavlakos2019VPoser}.
   > This is an empirical surrogate for the natural-pose manifold under
   > the VAE prior; calibration of rho_nat against subjective-comfort
   > studies is left for future work.
   The Pavlakos VPoser citation is retained (already in the bibliography,
   key `Pavlakos2019VPoser`). The constraint definition and prior-log-
   probability bound are kept downstream of the softened framing. Also
   killed the em-dash `---` ("broadly natural, but excluding ...") and
   the lyrical parenthetical "(yoga splits, gymnast bridges)" was folded
   into prose ("such as yoga splits and gymnast bridges").

6. **Human-in-the-loop control law subsection.** Killed the "Rather than
   X, which would Y, the BS does Z" Yoda-style construction by splitting
   into two simple sentences. Replaced semicolon-chained sentence "The user
   accepts or rejects; the next tick observes ..." with comma-coordinated
   prose. Replaced "slowly-drifting non-stationary" with "slowly drifting
   non-stationary" (no spurious hyphen).

7. **Haptic-cue paragraph (per first-reading critique). Dryer rewrite.**
   The original chatty UI text
   > "The user need not see the gradient itself. A simple haptic or cue
   > (a torso-yaw bar or a small arrow on the screen) suffices because the
   > actuation is body-scale and the rate signal refreshes at ~10 Hz. This
   > is one of the two semantic outputs the network's wireless control loop
   > issues to the user; the other is the live exposure reading of
   > \cref{sec:saridx}."
   was replaced with:
   > "The latent gradient need not be exposed to the user. A one-bit
   > acceptance channel suffices to close the loop, with Delta z^(k)
   > refreshed at ~10 Hz under body-scale actuation. The control loop
   > emits two semantic outputs at the user side, namely the latent step
   > Delta z^(k) of \cref{alg:closed-loop} and the live exposure reading
   > of \cref{sec:saridx}."
   No haptic/arrow/torso-yaw-bar UI talk; mathematical channel-level
   framing; bound to algorithm objects already in scope.

8. **In-algorithm reference.** `\cref{eq:autodiff-chain}` inside
   \State -> `~\eqref{eq:autodiff-chain}`.

## Resolution of the Mahalanobis comfort claim

Softened with explicit "empirical surrogate ... calibration ... left for
future work" framing, citation to Pavlakos2019VPoser retained. No new
citation required; Pavlakos is already in bib. **No Agent J action needed.**

## Resolution of the haptic-cue sentence

Killed entirely. Replaced with a dry one-bit-channel + refresh-rate
declaration that binds to the algorithm. No UI vocabulary survives.

## Subsection heading renames

- `\subsection{The cascaded SINR and the rate}` -> `\subsection{Cascaded SINR and rate}`
- `\subsection{Pose-space restriction and the latent gradient}` -> `\subsection{Pose-space restriction and latent gradient}`
- `\subsection{The human-in-the-loop control law}` -> `\subsection{Human-in-the-loop control law}`

Section heading `\section{Pose-differentiable rate and human-in-the-loop
control}` was already free of leading "The" and is left as is.

## Style fix counts (within scope only)

- Em-dash `---` removed: 1.
- Semicolons removed: 3 (autodiff chain paragraph, comfort paragraph,
  control law paragraph).
- `\cref` -> `\eqref` for equation refs: 2 (eq:cascaded, eq:autodiff-chain).
- Tildes (`~`) added before refs/units: 3 (`~\eqref{eq:cascaded}`,
  `$2$~nats`, `$\sim 10$~Hz`).
- "We" sentences trimmed (passive/declarative reframe): 2.
- Anthropomorphism / chatty-UI sentences killed or rewritten: 2
  (the rate-signal "haptic cue" paragraph, the "with magnitude controlled
  by" clause).
- Filler phrases deleted: "for our purposes", "the Shannon expression",
  "the system", "issues to the user", "broadly natural, but excluding".
- Subject-verb-rest restructures: 4 sentence-level.

## Cross-section flags for the audit

- The control-loop paragraph now references `\cref{alg:closed-loop}` and
  `\cref{sec:saridx}`. Both labels exist in the current draft (verified by
  successful compile, 14 pages, no undefined references reported in
  `jsac2_v3.log` beyond the usual rerun warning).
- The comfort-region softening exposes a minor terminology choice for the
  Discussion / SI: rho_nat is now described as a calibration-pending
  empirical surrogate. If a later section asserts a stronger comfort
  semantics, it should be reconciled with this section's softening.
- The Pavlakos2019VPoser citation now appears only **once** in this
  section (in the Mahalanobis-ball paragraph). The earlier in-paragraph
  reuse of the citation key (which the original had at the start of the
  comfort sentence under the VAE prior) was removed in the rewrite; the
  earlier "VPoser variational prior~\cite{Pavlakos2019VPoser}" call still
  carries the introduction.
- Bibliography is untouched (Agent J domain).

## Open issues

- "AMASS" is cited via `\cite{AMASS2019}` on first mention but not
  expanded as "Archive of Motion Capture as Surface Shapes". The
  introduction agent (Agent A) may want to define it on first use earlier
  in the paper; in this section the bare citation is left as-is per the
  spine. Agent A or Agent B can pick this up.
- "VAE" still appears once after expansion ("Under the VAE prior ..."). It
  is acceptable since variational autoencoder is now defined three lines
  above. No change made.
- "BS" first-use is outside this section; not my responsibility.
- Line "K-iteration latent projected gradient ascent" caption is fine as
  is; no leading "The".
- The Algorithm block is unchanged in structure; only the inline
  `\cref{eq:autodiff-chain}` -> `~\eqref{eq:autodiff-chain}` swap was
  made. No state-line wording changes (those are pseudocode).

## Compile status

`cd JSAC2/paper && pdflatex -interaction=nonstopmode jsac2_v3.tex` returns
14-page PDF, no undefined references attributable to this section. Only
the usual "Label(s) may have changed. Rerun" warning, and the standard
IEEEtran overfull-hbox for the running header on page 14 (not my scope).
