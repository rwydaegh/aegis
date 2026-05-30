# Agent M — SI sensitivity sections style pass

**File:** `/home/user/aegis/JSAC2/paper/jsac2_v3_supp.tex`
**Scope:** Lines 384–565 (after edits: lines 376–533)
**Sections covered:** §F (IMU sensitivity overlay), §G (Peak-APD location sensitivity), §H (Operator spectrum and $K_{99}$ adaptivity)

---

## Summary

Sentence-by-sentence style pass on three SI sections. Seven edits made,
all in scope. Spine, structure, claims, numbers, and honesty framing
preserved. Compile clean (6 pages, no errors, no new warnings inside
my scope).

## Honesty framing and table values — explicit confirmation

All load-bearing numbers preserved exactly:

**§F (IMU sensitivity overlay):**
- $\sigma_\mathrm{joint} \in \{0, 2, 4, 8, 16\}^{\circ}$, $5$ Monte-Carlo
  trials, $18$ Munich scenes — preserved.
- $4^{\circ}$ point: $0.4\,$dB LOS, $0.1\,$dB NLOS — preserved.
- $16^{\circ}$ point: $0.3\,$dB both classes — preserved.
- $90$th-percentile $\sim\!1.8\,$dB — preserved.
- "Model assumptions" caveat (steady-state-only, Madgwick reference,
  follow-up to use Madgwick/Mahony in loop) — preserved with light
  rephrase. The "lower bound" honesty framing intact.

**§G (Peak-APD location sensitivity, NEW section):**
- $\sigma = 2^{\circ}$: bias $-0.0\,\%$, $\pm 0.7\,\%$ — preserved.
- $\sigma = 4^{\circ}$: $-0.5\,\%$, $\pm 1.4\,\%$ — preserved.
- $\sigma = 8^{\circ}$: $-1.2\,\%$, $\pm 2.8\,\%$ — preserved.
- $\sigma = 16^{\circ}$: $-3.2\,\%$, $\pm 4.5\,\%$ — preserved.
- $\sim 5\,\%$ whole-body bound, $<4\,\%$ systematic low-bias — preserved.
- $52\,$cm at $\sigma = 2^{\circ}$, $58\,$cm at $\sigma = 16^{\circ}$,
  std $> 30\,$cm — preserved.
- Argmax-flip mechanism (forearm/shoulder, hip/knee), independence of
  noise magnitude — preserved.
- "Implication for cohort framing" honest caveat (whole-body $P_\mathrm{abs}$
  in scope, anatomical-region resolution out of scope, $4\,$cm$^2$
  spatial averaging deferred to follow-up) — preserved verbatim.

**§H (Operator spectrum):**
- Median rank $4$ specular, $3$ stochastic at $\epsilon = 10^{-2}$ — preserved.
- $B = 4$ bounce bound, $\sim\!14^{\circ}$ angular resolution, $3$–$5$
  resolvable directions, tail to $k = 30$ — preserved.
- $K_{99} = 1$ far-BS, $K_{99} = 4$ close-BS — preserved.

No drift. No loosening. No "improvement" that touched a number.

## Edit list (found by reading my scope against the style docs)

### §F — IMU sensitivity overlay

**Edit 1 — opening sentence: colloquial verb + fuzzy pronoun antecedent**
- Was: "We measure how much rate the closed loop loses when the
  on-device twin is fed a noisy IMU pose estimate. ... The user's
  actually achieved SINR at $\bm{z}^{\star}$ is what the rate loss
  measures."
- Now: "We measure the closed-loop rate loss when the on-device twin
  receives a noisy IMU pose estimate. ... The reported rate loss is
  the SINR gap between $\bm{z}^{\star}$ and the noiseless-IMU optimum,
  evaluated on the user's true channel."
- Fixes: KISS subject–verb-rest opener (Robin §1, §3); drop filler
  "actually" (A18); replace pronoun-fronted "is what...measures" with
  declarative S-V-rest (C4); drop colloquial "fed".
- Also: enforced "$21$" (numbers in math mode for consistency with the
  rest of the section).

**Edit 2 — second paragraph: "small" puffery, parallel "is bounded by" run**
- Was: "Across the range the mean rate loss is small: at the
  canonical ... operating point ..., the mean loss is bounded by
  $0.4\,$dB on LOS and $0.1\,$dB on NLOS; at the worst-case
  $\sigma_\mathrm{joint} = 16^{\circ}$ (poorly-calibrated IMU), the
  mean loss is bounded by $0.3\,$dB on both classes."
- Now: "The mean rate loss stays under $0.5\,$dB across the swept
  range. At the canonical ... operating point ..., the mean loss is
  bounded by $0.4\,$dB on LOS and $0.1\,$dB on NLOS. At the
  worst-case ... (poorly calibrated IMU), the mean loss is bounded by
  $0.3\,$dB on both classes."
- Fixes: replace vague "small" with the actual bound (C8 concrete over
  abstract); split the semi-colon-strung mega-sentence into staccato
  shorter ones (Robin §3, C2); drop hyphen in "poorly calibrated"
  (predicative compound, no hyphen needed); "without any explicit IMU
  compensation" → "with no explicit IMU compensation" (B7 positive
  form).

**Edit 3 — "Model assumptions" paragraph: A18 puffery + Robin §2 semi-colon**
- Was: "...would use a Madgwick/Mahony filter directly in the loop;
  the per-tick robustness reported here is a lower bound on what that
  more elaborate model would deliver, since..."
- Now: "...would run a Madgwick or Mahony filter directly in the
  loop. The per-tick robustness reported here is a lower bound on
  what such a fuller model would report, since..."
- Fixes: drop A18 "elaborate" → "fuller"; drop semi-colon (Robin §2);
  drop colloquial "deliver" → "report"; "Madgwick/Mahony" → "Madgwick
  or Mahony" (slash usage in math/units only).

### §G — Peak-APD location sensitivity (NEW section)

**Edit 4 — opening: colloquial "two flavours", A18 "very different"**
- Was: "The cohort-side $S_\mathrm{ab}$ reading has two flavours: ...
  The two have very different sensitivities to the IMU pose estimate."
- Now: "The cohort-side $S_\mathrm{ab}$ reading takes two forms: ...
  The two differ sharply in their sensitivity to the IMU pose
  estimate."
- Fixes: "flavours" colloquial (Wout §4 deadpan); "very different"
  A18 — replace with "differ sharply" (B17 strong word over
  intensifier+weak word).
- Note: kept "localised" — the document uses British spelling
  consistently (normalised, centred). Did NOT Americanise.

**Edit 5 — "Single-triangle peak": anthropomorphism + "cured by"**
- Was: "...several near-equal candidate triangles often compete for
  the per-tick maximum; small pose perturbations flip the argmax
  across body regions ... This is independent of noise magnitude, so
  it cannot be cured by a better IMU."
- Now: "...several triangles carry near-equal $S_\mathrm{ab}$ values
  around the per-tick maximum, so small pose perturbations flip the
  argmax across body regions ... The effect is independent of noise
  magnitude and therefore not removable by a better IMU."
- Fixes: anthropomorphism "compete" (A23); colloquial "cured by"
  (Wout §4); semi-colon → comma+so (Robin §2); pronoun "This" with
  fuzzy referent → explicit "The effect"; "moves by a mean $52$ cm"
  → "moves by a mean of $52$ cm" (idiomatic English).

### §H — Operator spectrum and $K_{99}$ adaptivity

**Edit 6 — first paragraph: redundant "(max 4, never above)"**
- Was: "...the median rank is $4$ for the specular dictionary
  (max $4$, never above) and $3$ for the stochastic dictionary
  (max $3$). The specular case shows a hard cliff after $k = 4$ ...
  even with $56$ subpaths only $3$ to $5$ distinguishable BS-side
  directions are excited above $\epsilon = 10^{-2}$, with a long
  sub-dominant tail that reaches the numerical floor near $k = 30$."
- Now: "...the median rank is $4$ for the specular dictionary and
  $3$ for the stochastic dictionary, with maxima of $4$ and $3$
  respectively. The specular case drops sharply after $k = 4$ ...
  of the $56$ subpaths, only $3$ to $5$ resolvable BS-side
  directions exceed $\epsilon = 10^{-2}$, and a long sub-dominant
  tail reaches the numerical floor near $k = 30$."
- Fixes: "(max 4, never above)" tautology removed and folded into
  "with maxima of $4$ and $3$ respectively" (using C13's
  respectively-is-free rule); "shows a hard cliff" → "drops
  sharply" (B18 "shows" filler verb); "shows a smooth decay" →
  "decays smoothly" (same); "even with...are excited above" →
  "of the...exceed" (more direct subject-verb).

**Edit 7 — second paragraph: em dashes + mic-drop stinger**
- Was: "...spreads energy across $K_{99} = 4$ modes. The two
  figures cover the same physical regime---rank-few BS-side
  excitation of the body---on different array conventions; the
  rank-few claim transfers."
- Now: "...spreads energy across $K_{99} = 4$ modes. Both figures
  cover the same physical regime (rank-few BS-side excitation of
  the body) on different array conventions, so the rank-few claim
  transfers between them."
- Fixes: em dashes `---` BANNED (C9, A1) — replaced with
  parentheses; A21 mic-drop stinger ("the rank-few claim
  transfers." after a long sentence) folded into the preceding
  clause with "so ... transfers between them"; "distributes
  energy" → "spreads energy" (B16 simple over Latinate); "The two
  figures" → "Both figures" (same).

## Fix counts

| Category | Count |
|---|---|
| Em dashes removed (`---`) | 1 (was the only one in scope) |
| Mic-drop stingers folded (A21) | 1 |
| A18 filler intensifiers/adverbs removed ("very", "actually", "elaborate") | 3 |
| Anthropomorphism (A23) softened | 1 ("compete for" → "carry near-equal values around") |
| Colloquialisms removed | 4 ("flavours", "fed", "cured", "deliver") |
| Semi-colons replaced with commas/period (Robin §2) | 3 |
| Bullet lists touched | 0 (preserved per-σ table verbatim) |
| `\textbf{...}` paragraph leads converted | 0 (kept document-wide convention; see flag below) |
| Numbers / claims changed | 0 |
| British→American spelling Americanisations | 0 (document uses British consistently) |

## Cross-section flags (out of scope — for other agents)

1. **Document-wide bold-paragraph convention.** The whole SI uses
   `\textbf{Lead.} prose...` for paragraph leads (lines 257, 266,
   273, 306, 310, 318, 329, 335, 342, 373, 445, 469, 480, 570, 591,
   600, 686, 692, 699). The TAP exemplar uses `\paragraph{Lead.}`.
   Not changing in scope alone — would create local inconsistency.
   If any agent does a document-wide convert to `\paragraph{}`, my
   three (lines 445, 469, 480) should go too.

2. **Percent-sign spacing.** The SI mixes `4\%` (line 122) and
   `0.44\,\%` (line 144) — IEEE house style is `4\%` (no space).
   The `\,\%` form dominates in my scope and elsewhere, so I left
   alone. If a document-wide cleanup happens, all my percents
   ($-0.0\,\%$, $\pm 0.7\,\%$, etc.) should follow.

3. **Spelling convention.** Document uses British (`localised`,
   `normalised`, `centred`, `optimised`). IEEE TAP/TWC/JSAC house
   style is American. Latex_rules item 71 calls this out. I kept
   British in scope to match the rest of the file. If anyone
   Americanises globally, my "optimises" and "localised" go too.

4. **Section §H caption "fig2_svd_spectrum.pdf".** Filename has
   "fig2" hard-coded — this is a stale main-paper figure number
   reference inside an SI. Not load-bearing, but flag for the asset
   pipeline.

5. **Section IV reference (line 561, just after my scope).** Reads
   "of Section~IV (UE-anchored Kirchhoff render) of the main
   paper" — the parenthetical title might no longer match the main
   paper's section title after other agents' edits. Not in my scope
   but worth a cross-check by Agent J or whoever owns main-SI
   alignment.

## Open issues

None inside my scope. The compile is clean (6 pages, no errors, no
new warnings traceable to my edits — the underfull/overfull boxes
in the log are at lines 561+, outside my scope).

## Compile verification

```
$ pdflatex -interaction=nonstopmode jsac2_v3_supp.tex 2>&1 | tail -50
Output written on jsac2_v3_supp.pdf (6 pages, 594453 bytes).
```

Grep for errors / undefined refs returned empty. The two warnings
about "Token not allowed in PDF string" and the over/underfull boxes
are at lines 561+, all outside my scope.
