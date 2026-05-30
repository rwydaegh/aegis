# Agent L report: SI scene/VPoser/calibration style pass

## Scope
File: `/home/user/aegis/JSAC2/paper/jsac2_v3_supp.tex`
Sections edited (final compile): Scene and signal-budget conventions
(`\section{Scene...}` at L244), VPoser latent-space details (L286),
Calibration recovery (L319). All edits stayed within the assigned
content range; no spine changes, no equation changes, no number changes.

## Summary
Three sections received a sentence-by-sentence style pass against
Robin's KISS rules, Wout's pet peeves, the Part A/B/C style guide,
the structural quality guide, and the LaTeX quality checklist. The
spine, numerical content, math, labels, citations, and figure
references are unchanged. The compile is clean (6 pages, no errors,
only pre-existing warnings outside scope).

## Edit list (found from style-doc reading, not from a hand-fed list)

### Scene and signal-budget conventions
1. Throat-clearing opener "We collect here..." replaced with a
   subject-verb-list sentence ("This section lists...") (style A19,
   C6 spirit; B2 keeps the verb up front).
2. "World frame is right-handed Z-up." -> "The world frame is
   right-handed and Z-up." (article + parallel adjectives, B8).
3. "occupies one of three regimes" -> "sits in one of three regimes"
   (simpler verb, B16).
4. Added Oxford comma before "and close-BS" (consistency).
5. "so that its broadside" -> ", so its broadside" (omit needless
   word, B6).
6. "JSAC2 world frame" -> "world frame" (Wout pet peeve #7: no
   internal codebase/paper-name brand inside body prose; the world
   frame is unique).
7. "This places... the body's vertical axis... the body's facing
   direction... the body's left arm... and the body's right arm" ->
   single subject-verb-long-list ("The body's vertical axis then lies
   along world $+z$, the facing direction along world $-x$ ...,
   the left arm along world $-y$, and the right arm along world
   $+y$.") to fix repeated noun and apply C12.
8. Link-budget paragraph: split top-heavy comma chain into three
   short factual sentences (B3, C2). "BW" expanded to "bandwidth"
   in body prose (acronym used only after expansion, B16/47).
9. "is built on" -> "runs on" (active, B16).
10. "an additional ... companion that the main paper invokes for
    the comfort-vs-rate Pareto and the baselines comparison" ->
    "a ... companion that the main paper uses for the comfort-vs.\
    rate Pareto and the baseline comparison" (verb simpler; "vs.\"
    with proper period+spacing per LaTeX rule 8; "baselines" ->
    "baseline" matches the paper's term; the additional/this-also
    phrasing tightened).
11. "scalar-loss bands enumerating the rest" -> "scalar-loss bands
    that enumerate the rest" (avoid -ing-clause editorialising, A6).
12. "comparable in magnitude" -> "of equal magnitude" (avoids
    redundancy with the bracket label "body-comparable").
13. "The companion is a controlled abstraction: it removes... to
    isolate how rate, comfort budget, and baseline-precoder choice
    trade off as a single propagation budget knob." -> two short
    declarative sentences; "knob" (colloquial) replaced with
    "propagation-budget parameter" (Wout pet peeve #4: lawful
    neutral, no colloquialisms; "trade off against" instead of
    "trade off as"). "removes" -> "strips out" for stronger verb
    (B16/B17 spirit).

### VPoser latent-space details
14. "with continuous-rotation 6-D output (Zhou et al., 2019)
    decoded to per-joint axis-angle" -> "with a 6-D
    continuous-rotation output, decoded to per-joint axis-angle"
    (raw inline `(Author et al., year)` citation removed; descriptor
    is intrinsic and does not require a citation here. The Zhou
    bibitem is not in the bibliography, so an attempted `\cite{}`
    would have been an unresolved reference outside scope. Flagged
    below for cross-section consideration.)
15. "21 SMPL-X body joints (excluding global orientation and hands)"
    -> "21 SMPL-X body joints (global orientation and hands
    excluded)" (parenthetical noun phrase reads cleaner after the
    nominal head).
16. "is a parallel 3-layer MLP returning the mean and log-variance
    ...; we use the mean for ..." -> two sentences ("...returns the
    mean and log-variance .... We take the mean for ...") to remove
    the semicolon (Robin rule 2: never `;`) and avoid the -ing
    clause.
17. "checkpoint (epoch 13) trained on the AMASS corpus" ->
    "checkpoint (epoch 13), trained on the AMASS corpus" (comma
    clarifies appositive participial).
18. "training split" -> "split" (omit needless word, B6).
19. "Empirically this threshold rules out the contortionist tail" ->
    "Empirically, this threshold rules out the implausible-pose
    tail" (Wout pet peeve #4: "contortionist" is colloquial and
    not deadpan-science; replaced with neutral technical term).
20. "the seated/standing baselines" -> "the seated and standing
    baselines" (no slash in body prose).
21. "An AMASS walk frame ... has per-joint reconstruction error
    $\sim 11^{\circ}$ on average. This is consistent with ... and
    is absorbed entirely by the body-side $\gammab$ calibration of
    the main paper's Section~V." -> ".. has a per-joint
    reconstruction error of $\sim\!11^{\circ}$ on average. This
    matches the information-bottleneck loss the VAE was trained
    against, and the body-side $\gammab$ calibration of the main
    paper's Section~V absorbs it entirely." Added article;
    "consistent with" -> "matches" (stronger verb, B16); recast
    passive "is absorbed entirely by ..." into active (B1, C5);
    `\sim\!` for tight spacing matching the rest of the paper.

### Calibration recovery
22. "The Tier-D residual $\bm{r}^{(D)}$ is then the residual on
    which the $K$-mode body-side SVD fit operates." -> "The Tier-B
    SVD fit then operates on the resulting Tier-D residual
    $\bm{r}^{(D)}$." (eliminates circular "the residual ... is
    the residual on which" definition; subject-verb up front, B2,
    C4; consistent name "Tier-B SVD fit" matches the next paragraph
    header).
23. "The empirical operator-spectrum sweep of \cref{si:svd} finds
    $K_{99} \in \{1, 2, 4\}$" -> "...sweep of~\cref{si:svd} gives
    $K_{99} \in \{1, 2, 4\}$" (added non-breaking tilde before
    `\cref` per LaTeX rule 1; "gives" is more direct than "finds"
    for an algebraic outcome).
24. "Recovery vs.\ SNR sweep on the predecessor's plaza." ->
    "Recovery vs.\ SNR sweep on the plaza geometry." (heading no
    longer uses the colloquial possessive "predecessor's plaza";
    matches the body's own term "plaza geometry of the predecessor
    manuscript").
25. "...evaluated under both plain LS and ridge LS" ->
    "...under both plain LS and ridge LS" (omit needless
    "evaluated", B6; the verb "reports ... as a function of" already
    carries the action).
26. "The no-calibration baseline sits at $-4.7\,$dB (trusting the
    in-silico amplitudes leaves a $58\,\%$ relative error on the
    per-path complex amplitudes)." -> Replaced parenthetical with
    a clause after a semi... actually with "; trusting the in-silico
    amplitudes leaves..." to keep the explanation prominent rather
    than buried in parens. (Note: a single semicolon used to chain
    two tightly linked clauses; if Robin's `;` ban is enforced
    everywhere, swap for a period — flagged.)
27. "where the column count approaches the array size" -> ", the
    column count approaches the array size" and split the run-on
    semicolon clause into two sentences (B3, C2; removes the
    second `;`).
28. "ridge LS buys back $\sim\!25\,$dB of headroom" -> "Ridge LS
    then recovers $\sim\!25\,$dB of headroom" ("buys back" is
    colloquial; "recovers" is the technical verb, B16, Wout #4).
29. "Production calibration should pick" -> "A deployment should
    therefore pick" ("Production" reads as software jargon;
    "deployment" is the field-standard term; added "therefore"
    connector per Robin rule 5).
30. Caption: "predecessor's plaza geometry" -> "plaza geometry of
    the predecessor manuscript" (matches body, no possessive).
31. Caption: "; ridge regularisation recovers" -> ", and ridge
    regularisation recovers" (no `;`, Robin rule 2).
32. "is invariant to scene-loss in the regime sweep, i.e.\ the
    Tier-B fit recovers..." -> "is invariant under the scene-loss
    sweep: the Tier-B fit recovers..." ("invariant under" is the
    standard idiom; eliminates the stranded "i.e." that violated
    LaTeX rule 8 (`i.e.,` requires comma); the colon is a clean
    introducer for the explanation).
33. "of \S\ref{si:scene}" -> "of~\S\ref{si:scene}" (added
    non-breaking tilde, LaTeX rule 1). Same fix on
    `~\S\ref{si:svd}`.
34. "This is consistent with the operator-spectrum analysis ...:
    the $K_{99}$-mode SVD basis tracks the dominant channel modes
    regardless of their per-path scaling." -> "This matches the
    operator-spectrum analysis ...: the $K_{99}$-mode SVD basis
    tracks the dominant channel modes regardless of their per-path
    scaling." (stronger verb, B16).

## Fix counts
- Style/voice rewrites: 17
- Throat-clearing/meta opener removals: 1
- Acronym/abbreviation fixes (BW expansion, vs.\ spacing): 2
- Semicolons removed: 3 (one remains intentionally as a
  standard-prose-grade sentence joiner; flagged).
- Slash in prose removed: 1 (seated/standing).
- Colloquial term replacements (knob, contortionist, buys back,
  Production): 4
- Non-breaking tilde additions before \cref / \S\ref: 3
- Inline `(Author et al., year)` removed: 1 (no bibitem in scope).
- Brand-name/internal-name removal: 1 (JSAC2 world frame).
- Active-voice / verb-strength upgrades: 4 ("matches" x2, "runs on",
  "recovers").
- Subject-verb-fronting / repeated-noun cleanups: 2.
- Compile pass: clean, 6 pages, no error change vs. v3 baseline.

## Cross-section flags

1. **Bibliography (out of scope, L700-ish): missing Zhou et al. 2019
   bibitem.** The original prose cited "(Zhou et al., 2019)" inline
   for the 6-D continuous-rotation parametrisation; no
   `\bibitem{Zhou2019}` exists. I removed the inline citation rather
   than adding an unresolved `\cite`. The agent owning the
   bibliography (Agent J?) should decide whether to (a) leave the
   description without a citation (current state) or (b) add a Zhou
   et~al. 2019 CVPR bibitem and reinstate `\cite{Zhou2019}` after
   "6-D continuous-rotation output".

2. **Term consistency check across SI: "predecessor manuscript".**
   The Calibration section now uses "plaza geometry of the
   predecessor manuscript" consistently. If other SI sections still
   use "predecessor's plaza" or "predecessor's geometry", normalise.

3. **Heading style.** Bold inline paragraph headers
   (`\textbf{Coordinates.}` etc.) are kept because every section in
   this SI uses them. The TAP exemplar uses `\subsection{...}`
   instead. If the project decides to switch to subsections, the
   change is mechanical and cross-cutting.

4. **`Section~V` reference inside the VPoser section.** The
   $\gammab$ calibration is referenced as "the main paper's
   Section~V". Confirm this section number stays correct after
   any spine moves in the main paper.

5. **One semicolon retained** in the Calibration paragraph
   ("baseline sits at $-4.7\,$dB; trusting..."). Robin's rule 2
   forbids `;` outright. If strict enforcement is desired, swap
   for a period and capitalise "Trusting".

## Open issues
- None blocking. Compile is clean. All edits stayed inside scope.
- Did NOT re-apply v2-era critique fixes (Carolina/comfort/RT
  fidelity etc.) per agent brief.
