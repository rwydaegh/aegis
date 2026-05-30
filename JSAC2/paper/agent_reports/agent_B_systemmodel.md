# Agent B report: Section II "System model and DTN architecture"

Scope: `JSAC2/paper/jsac2_v3.tex`, lines 285-403 in the original
(now 285-420 after edits). Subsections: Geometry and channel, Body
twin and pose telemetry, Closed loop, Positioning against the
digital-twin literature.

## Summary

Light-touch sentence-level pass over the system-model section,
plus three structural fixes: (i) the architecture flowchart is now
referenced as the very first sentence of the section with a
stupid-simple Wout-style intro, (ii) the channel-vector dimensions
($\hh,\hBS,\hbody \in \Complex^{M}$) are made explicit at
eq.~\eqref{eq:cascaded} so the equation no longer mixes scalars
and vectors implicitly, and (iii) a new short paragraph in "Body
twin and pose telemetry" defines the BS-side environmental twin
and the per-element path dictionary $\Jmat$ (with citation to the
existing Sionna RT key), giving the RT scene and $\Jmat$ the
prominence the critique asked for. The "The closed loop" heading
lost its leading "The" per C11. Semicolons removed throughout
(except the math notation `;` inside function argument lists,
which is standard).

## Item-by-item resolution of critique items in scope

1. **"Equation 1 is a bit abstract maybe (mixing scalars and
   vectors?) and things aren't well defined."**
   Resolved. Added explicit type annotations
   `$\hh,\hBS,\hbody \in \Complex^{M}$` immediately after
   eq.~\eqref{eq:cascaded}, plus `$\rr_p \in \Reals^{3}$` and a
   one-sentence preamble that the channel vector has "$M$ complex
   entries (one per BS element)". The received-signal equation is
   now its own numbered equation (`eq:rx`) with $n$'s distribution
   in the same display, instead of being inlined with semicolons.

2. **"the flowchart needs to be introduced earlier and be really a
   point to hang onto"**
   Resolved. The first sentence of \subsection{Geometry and channel}
   is now `The DTN architecture is shown in
   Fig.~\ref{fig:dtn-arch}.` followed by a short stupid-simple
   recap (BS, FR2, phone, on-device render) and a one-sentence
   roadmap for the rest of the section. This matches Wout's
   convention from `wout_specific_pet_peeves.md` item 1 and TAP
   §IV's "Cref{fig:configuration} shows the configuration" opener.

3. **"Saying it is a SMPLX is important tho. Maybe more focus on
   the RT scene and J too."**
   Resolved. SMPL-X is named in the first sentence of the body-twin
   subsection. A new dedicated paragraph introduces the BS-side
   environmental twin and defines
   $\Jmat \in \Complex^{M \times P}$ with $P$ MPCs at the served
   user, identifies $\Jmat$ as "the only per-user object the BS
   needs from the scene", and ties it forward to
   \cref{sec:kirchhoff} and \cref{sec:control}. This also gives
   the closed-loop list (which references $\Jmat$) a definition
   to point back to.

4. **"Subsection name 'The closed loop' — Wout-style headings are
   fine ('Closed loop') but check no 'The' prefix."**
   Resolved. `\subsection{The closed loop}` became
   `\subsection{Closed loop}` (style guide C11).

5. **"Saying things are deliberately compressed is not a good
   wording"**
   Not applicable in this scope (the phrase appears in §III/§IV).
   Flagged for the agent owning that scope.

6. **"you state two conditions i and ii for culling..."**
   Not applicable in this scope (the i/ii framing is in the
   Kirchhoff §IV, not §II). Flagged for the agent owning that
   scope.

7. **"is u, v from gram schmidt actually used in any derivation?"**
   Not applicable in this scope (Gram-Schmidt is in the
   Kirchhoff section). Flagged for that agent.

8. **"T approx 0.54 is a funny thing to make a whole equation"**
   Not applicable in this scope (in §III). Flagged for that
   agent.

9. **"Saying Kirchoff operator is the 'new' central object 'of this
   paper'... the word new isnt necessary... also 'this paper' for
   no reason"**
   Verified: no "new" or "this paper" framing inside §II.

10. **Spine preserved.** The four subsection structure
    (Geometry/channel, Body twin/telemetry, Closed loop,
    Positioning) is unchanged. No equations dropped. No claims
    added beyond the $\Jmat$ definition, which is already used
    by the figure caption and the loop list.

## Counts of style fixes applied

- Em dashes removed: 0 (none were present in scope).
- Semicolons in prose removed: 4 (one in "with SINR defined in
  \cref{...}; we report...", one in the loop list bullet 1
  "$\sim 1$ Hz; per-path...", one in "see~\cref{sec:bandwidth};",
  one in the figure caption "Solid arrows are forward
  (downlink); dashed arrows..." and one in the cohort-study
  sentence).
- "We" reductions: 4 (active passive recasts where active was
  awkward, and "we report" → "Rates are reported").
- Anthropomorphism / promotional words trimmed:
  - "is the operating decomposition used throughout" → "."
    (cut the puffery).
  - "first-class outputs" → "direct outputs" (drop the
    sales-copy adjective).
  - "structurally different" preserved but rephrased as "Here
    the twin is the human body in the cell".
- `~\cref` ties added/normalised: 7
  (`in~\cref{sec:control}`, `of~\cref{sec:closed-loop}` ×2,
  `of~\cref{sec:control}` ×2, `of~\cref{sec:kirchhoff}` ×2,
  `to~\cref{sec:closed-loop}`, `see~\cref{sec:bandwidth}`,
  footnote `in~\cref{sec:kirchhoff}`).
- Numbers digit-grouped in math: `22`, `10\,475`, `20\,908`
  already had the thousands-thin-space; wrapped the integers in
  math mode for consistency.
- Equation punctuation: both equations now end with `\,` then `,`
  or `.` per latex-rules item 9.
- Subscript labels: `$P_{\mathrm{tx}}$`, `$N_{0}$`,
  `$\sigma_{\mathrm{joint}}$` already correct, kept consistent.
- Heading "The" prefix removed: 1 ("The closed loop" → "Closed
  loop").
- Equation eq:rx introduced (was previously inlined in prose).
  No body text refers to it by label, but it lives in a numbered
  display now and can be cross-referenced later if needed.

## Cross-section flags for the audit

- **New label `\label{eq:rx}`** added on the received-signal
  equation. Nothing currently references it; Agent J / audit can
  decide to drop the label or wire references in to it.
- **New citation key used**: `\cite{Hoydis2023Sionna}` (already
  in use elsewhere in the paper at lines 227 and 967, so this
  is not a new bib entry — but the Sionna RT bibitem must
  remain in the bibliography).
- **No labels removed.** No `\cite{}` keys removed.
- **Figure label is `fig:dtn-arch`** (not `fig:flowchart` as
  the prompt assumed). All my refs use the existing label.
- **Cross-section reference `\cref{sec:bandwidth}`** is preserved
  from the original draft. If that label does not yet exist in
  the source, this is a pre-existing forward reference, not
  something I introduced.
- The opening sentence of §II promises a "cadence at which the
  loop runs" but the only cadence-bearing content here is the
  $\sim 1$ Hz refresh inside the closed-loop list. If a separate
  cadence/timing table or paragraph lives elsewhere
  (\cref{tab:cadence} exists at line 1286 of the original), the
  audit may want to add a forward pointer here. I did not add
  one because I was not sure the table is final yet.

## Open issues

- The architecture **figure** itself (`figures/fig_dtn_architecture.pdf`)
  has a known issue per the critique: white label rectangles cover
  the arrows, "K99 mode SVD gamma fit" is opaque on first read,
  and the elements need to be understandable on first glance.
  This is a figure-rendering issue, not text. **Flagged for the
  user to iterate visually** (the prompt asked me to flag rather
  than re-render). The caption text itself is clean now and
  matches the symbols introduced in the body.
- The Body twin paragraph mentions
  `\bm{\beta}` (body shape) "distinct from the BS-side calibration
  coefficient $\betab$". This is good notation hygiene but the
  collision is pre-existing — `\betab` is the macro for
  `\bm{\beta}`. Flagged for the audit pass: consider renaming the
  shape parameter to avoid the symbol overlap entirely.
- The "Positioning" subsection still does not cite a specific
  body-twin precedent that the contribution differs from. The
  three DTN cites (`Chen2024DTN, Saad2025DTN, Hashash2025DTN`)
  carry the network-twin literature but the gap claim ("the twin
  is the human body in the cell, not the network or the
  application") would be sharper with one body-DTN reference to
  contrast against. Out of scope for a style pass, flagged for
  the lit-positioning agent.
- Compile check: paper builds to 14 pages. Undefined-citation
  warnings are pre-existing (bibliography owned by Agent J) and
  unrelated to my edits. No new errors originating in my scope.
