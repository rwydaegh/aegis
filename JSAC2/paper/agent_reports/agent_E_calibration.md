# Agent E report: Section V (Closed-loop calibration)

## Scope
`/home/user/aegis/JSAC2/paper/jsac2_v3.tex`, section
`\section{Closed-loop calibration: UL pilots and \gammab}` and its
three subsections (Residual decomposition, Body-side parametrisation,
Calibration robustness to IMU drift).

## Summary of changes

1. **Section opening (preamble).** Rewrote the three-cause enumeration
   into Robin's "First/Second/Third" pattern. Replaced the coined term
   "twin gap" — defined and immediately abandoned in the original — with
   plain "the gap". Removed "the cooperative downlink in which the user
   is enrolled" (UL pilots feed the regression, so "uplink pilot stream"
   is the correct anchor). Tightened "regression of measured against
   predicted channel, fit per-slot or per-second" to "regressing the
   measured channel on the predicted one, refit per slot or per second".

2. **V.A Residual decomposition.** Replaced "decomposes into ...
   components:" with "splits into ... components," (no colon before the
   display equation, equation now ends with `\,,`). Removed the
   semicolon inside the `\delta\betab` parenthetical (Robin: no
   semicolons). Replaced "(BS-side, calibrated against uplink pilots;
   see SI~\S{}S5)" with "(fitted from uplink pilots, SI~\S{}S5)" —
   BS-side label is redundant with the underbrace, and "see" is empty
   filler. Replaced "is identifiable ... as long as ... are
   distinguishable" with the precise "are linearly independent".
   Dropped redundant "factor" in "per-triangle correction factor".

3. **V.B Body-side parametrisation.** Heading: dropped "a" — now
   `Body-side parametrisation: $K$-mode SVD basis`. Split the long
   three-`and` sentence ("We project ... write ... and fit ...") into
   two sentences. Removed "itself" (filler) after
   `\Lambda_{\mathrm{KH}}`. Replaced possessive "operator's spectral
   mass" with "spectral mass of the operator" (TAP avoids possessive
   forms on inanimate objects). **Softened the K_99 claim:**
   `K_{99} \in \{1, 2, 4\}` → "ranging from $1$ to $4$ across the BS
   geometries considered, with the exact value depending on UE--BS
   distance and visibility". This addresses the critique that the
   specific `\{1,2,4\}` set may be an artefact of the old toy scenery
   and the new RT-based experiments may report different values.

4. **V.C Calibration robustness to IMU drift.** Refactored to remove
   the colon-introduced explanation pattern ("The closed loop is
   therefore robust to ... : the calibration step ..."). Combined the
   "same mechanism" sentence with the conclusion so the cause-effect
   chain reads in one breath. Replaced "operator's leading modes" with
   "leading modes of the operator" (no inanimate possessive). Changed
   "absorbing the residual into the operator's leading modes" to
   "projecting the residual onto the leading modes of the operator"
   (more honest — ridge least-squares with an SVD basis is exactly a
   projection plus shrinkage, "absorbs" is too loose). Replaced "in the
   pose telemetry" filler with nothing — "robust to consumer-grade IMU
   drift" stands on its own.

## Item-by-item resolution of applicable critique items

- **"Sec V.B: just pick the one you go for"** — V.B as it stood
  already presented a single chosen parametrisation, no "we considered
  A and B before settling on C" framing existed. Re-checked carefully;
  nothing to cull. The §V.B critique is satisfied by construction in
  the current draft.

- **K_99=1/4 regime claim** — Robin asked whether this is obsolete
  given the move to RT. The text in my scope already used the milder
  `K_{99} \in \{1, 2, 4\}`, not the inflammatory "rank-1 regime
  K99=1 ... rank-many regime K99=4". I softened further to "ranging
  from $1$ to $4$" with an attribution to UE--BS distance/visibility.
  **Cross-section flag for Agent G (§VII):** if the new RT numerical
  study reports `K_{99}` values outside `[1,4]`, the V.B prose now
  references this honestly via a range and SI~\S{}S7, so a single number
  update in §VII won't strand the V.B claim. If Agent G observes
  `K_{99}` reaching 5 or higher, the V.B range should be re-extended;
  if `K_{99}` is always 1 in the new RT setup, the V.B "ranging from 1
  to 4" should be flattened to "typically 1 in our setup, up to 4 in
  the close-BS geometries". Flag for the audit pass.

- **Cap-violation passage (`2.47\%` etc.)** — not in my scope. The
  passage lives in §VII (Agent G). My scope only references
  `\sigma_{\mathrm{joint}} \in \{0, 2, 4, 8, 16\}^{\circ}` once and
  defers to SI~\S{}S6 for the rate cost. No change needed here.

- **"Comfort becomes a Mahalanobis ball"** — not in my scope (§VI,
  Agent F's territory). Left alone.

- **"The" prefix in subsection headings** — V.B heading "Body-side
  parametrisation: a $K$-mode SVD basis" had "a" not "The". Dropped
  "a" too for a cleaner heading. V.C heading "Calibration robustness
  to IMU drift" had no "The" prefix; left as-is per Robin's "fine
  as-is" note.

- **"this paper", "we now", "as we have shown earlier" artefacts** —
  none of these appeared in my scope. No fixes needed.

## Style fix counts

- Semicolons removed: 1 (in V.A parenthetical).
- Colons before display equations: 1 normalised (V.A `:` → `,`).
- Long sentences split: 2 (V.B opening, V.C robust-to-IMU sentence).
- Anthropomorphic / inanimate possessives removed: 2 ("operator's
  spectral mass", "operator's leading modes").
- Redundant filler removed: 5 ("factor", "itself", "the two sides",
  "in the pose telemetry", "see SI").
- "First, ... Second, ... Third, ..." patterns introduced: 1 (V.0
  preamble three-cause list).
- Heading articles dropped: 1 ("a $K$-mode" → "$K$-mode").

## Cross-section flags for the audit

- **§VII / Agent G:** V.B now says `K_{99}` ranges from 1 to 4 across
  geometries. If the new RT-based numerical study finds a different
  range, V.B should be updated to match. Currently soft enough not to
  contradict any plausible RT outcome.
- **SI \S S5, S6, S7:** V.A points to S5 (BS-side calibration), V.B
  points to S7 (operator-spectrum sweep), V.C points to S6 (IMU-noise
  sensitivity). If the SI section numbering changes, these need to be
  re-synced. Currently consistent with how my scope and the rest of
  the body cite the SI.
- **Macro consistency:** `\gammab` and `\Lambda_{\mathrm{KH}}` are
  used as defined in the preamble. No new macros introduced.

## Open issues

- The opening sentence still uses `\emph{prediction}` to mark the
  measured-vs-predicted distinction. This is light emphasis, not
  decorative bold, so I left it. An audit pass may want to remove it
  if §III/IV already establish the predicted/measured contrast.
- The proposition body (Identifiability) was not touched — it is a
  formal statement, and Robin's "short sentences" preference is
  outweighed by mathematical readability there.
- "Body-side parametrisation" still uses the British `-isation`
  spelling. Whole-paper harmonisation to American (`parametrization`)
  is an audit-pass concern per the assignment, not a per-agent task.
- The "twin gap" coinage is removed from my scope (used once in the
  original, now replaced with plain "the gap"). If any other section
  refers back to "the twin gap" by name, that reference is now
  orphaned. Grep confirms no other usage:
  `grep -n "twin gap\|twin-gap"` returns nothing after my edit. Safe.

## Verification

`pdflatex -interaction=nonstopmode jsac2_v3.tex` compiles cleanly (14
pages, no `!` errors, no undefined-control-sequence warnings, no
runaway-argument warnings). Only pre-existing Overfull \hbox warnings
in the bibliography (Agent J's scope) remain.
